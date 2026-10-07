"""Export explicitly reviewed, consented Label Studio masks to pinned training snapshots."""

import asyncio
import hashlib
import json
import shutil
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from sqlalchemy import select

from backend.core.config import settings
from backend.core.consents import WRINKLE_TRAINING_CONSENT_VERSION
from backend.core.db.models import AnnotationTask, Consent
from backend.libs.minio_client import get_bytes, remove_objects
from backend.services.curated_training import (
    APPROVED_DATA_ROOT,
    PREPROCESSING_VERSION,
    sha256_file,
    validate_manifest,
)


def input_key(row) -> str:
    return row.object_key.rsplit("/", 1)[0] + "/model_input.npy"


async def training_consent(session, user_id):
    return await session.scalar(
        select(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == WRINKLE_TRAINING_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .with_for_update()
    )


async def check_user_dataset(session, data):
    if datetime.fromisoformat(data["expires_at"]) <= datetime.now(UTC):
        raise ValueError("Training dataset expired")
    for record in data["consent_records"]:
        from backend.services.annotation_service import has_annotation_consent

        annotation_allowed = await has_annotation_consent(session, UUID(record["user_id"]))
        consent = await training_consent(session, UUID(record["user_id"]))
        # Re-granting consent must not resurrect a previously revoked snapshot.
        if consent is None or str(consent.id) != record["consent_id"] or not annotation_allowed:
            raise ValueError("Training consent was withdrawn or changed")


def subject_split(user_id):
    bucket = int(hashlib.sha256(str(user_id).encode()).hexdigest(), 16) % 10
    return "test" if bucket == 0 else "validation" if bucket == 1 else "train"


def reviewed_mask(task, annotation_id: int):
    import numpy as np
    from label_studio_sdk.converter.brush import decode_rle

    data = task.model_dump() if hasattr(task, "model_dump") else task
    annotations = [
        a
        for a in data.get("annotations", [])
        if a.get("id") == annotation_id and not a.get("was_cancelled")
    ]
    if len(annotations) != 1:
        raise ValueError("Selected human annotation is missing or cancelled")
    result = annotations[0].get("result", [])
    mask = None
    no_wrinkles = False
    for item in result:
        value = item.get("value", {})
        if item.get("type") == "choices" and item.get("from_name") == "wrinkle_presence":
            if value.get("choices") == ["No visible wrinkles"]:
                no_wrinkles = True
            elif value.get("choices") != ["Visible wrinkles"]:
                raise ValueError("Invalid wrinkle-presence review")
            continue
        if item.get("type") != "brushlabels" or value.get("brushlabels") != ["Wrinkle"]:
            raise ValueError("Only reviewed Wrinkle brush masks are supported")
        width, height = item.get("original_width"), item.get("original_height")
        if width != 1024 or height != 1024:
            raise ValueError("Reviewed mask must match the 1024x1024 aligned face")
        if item.get("image_rotation", 0) != 0:
            raise ValueError("Reviewed mask must use the unrotated aligned-face coordinates")
        rle = value.get("rle")
        if (
            not isinstance(rle, list)
            or not 8 <= len(rle) <= 8 * 1024 * 1024
            or any(type(b) is not int or not 0 <= b <= 255 for b in rle)
            or int.from_bytes(bytes(rle[:4]), "big") != width * height * 4
        ):
            raise ValueError("Invalid or oversized brush encoding")
        layer = decode_rle(rle).reshape(height, width, 4)[:, :, 3] > 0
        mask = layer if mask is None else mask | layer
    # Empty annotations can be an accidental unfinished task; reject instead of guessing.
    if no_wrinkles:
        if mask is not None and mask.any():
            raise ValueError("No-wrinkle review conflicts with a positive mask")
        return np.zeros((1024, 1024), dtype=np.uint8)
    if mask is None:
        raise ValueError("A reviewed brush mask is required")
    return mask.astype(np.uint8) * 255


def export_sample(row, annotation_id: int, directory):
    import numpy as np
    from PIL import Image

    from backend.libs.labelstudio_client import get_label_studio_client

    client = get_label_studio_client()
    if client is None or not row.label_studio_task_id:
        raise ValueError("Label Studio review is unavailable")
    task = client.tasks.get(id=row.label_studio_task_id)
    data = task.model_dump() if hasattr(task, "model_dump") else task
    if data.get("data", {}).get("analysis_id") != str(row.analysis_id):
        raise ValueError("Review task does not belong to this analysis")
    mask = reviewed_mask(data, annotation_id)
    payload = get_bytes(input_key(row), settings.annotation_bucket)
    if len(payload) > 20 * 1024 * 1024:
        raise ValueError("Training input exceeds 20 MiB")
    array = np.load(BytesIO(payload), allow_pickle=False)
    if (
        array.dtype != np.float32
        or array.shape != (4, 1024, 1024)
        or not np.isfinite(array).all()
        or array.min() < -1
        or array.max() > 1
    ):
        raise ValueError("Invalid stored training input")
    name = str(row.id)
    image_path, mask_path = directory / f"{name}.npy", directory / f"{name}.png"
    image_path.write_bytes(payload)
    Image.fromarray(mask).save(mask_path)
    return {
        "id": name,
        "subject_id": hashlib.sha256(str(row.user_id).encode()).hexdigest(),
        "input": image_path.name,
        "mask": mask_path.name,
        "input_sha256": sha256_file(image_path),
        "mask_sha256": sha256_file(mask_path),
        "annotation_id": annotation_id,
    }


async def build_dataset(session, run):
    selections = run.config["selections"]
    directory = APPROVED_DATA_ROOT / f"review-{run.id}"
    if directory.exists():
        raise ValueError("Dataset snapshot already exists")
    directory.mkdir(parents=True)
    records, samples, expiries = [], [], []
    try:
        for selected in selections:
            row = await session.get(AnnotationTask, UUID(selected["task_id"]))
            consent = await training_consent(session, row.user_id) if row else None
            if row is None or consent is None or row.expires_at <= datetime.now(UTC):
                raise ValueError("Review image expired or training consent is missing")
            if selected["split"] != subject_split(row.user_id):
                raise ValueError("Subject split is fixed across dataset snapshots")
            records.append({"user_id": str(row.user_id), "consent_id": str(consent.id)})
            expiries.append(row.expires_at)
            sample = await asyncio.to_thread(
                export_sample, row, selected["annotation_id"], directory
            )
            samples.append({**sample, "split": selected["split"]})
        data = {
            "schema_version": 1,
            "source": "consented_user_review",
            "approved_for_training": True,
            "approval_reference": f"admin:{run.config['actor']}:{run.id}",
            "rights_reference": WRINKLE_TRAINING_CONSENT_VERSION,
            "preprocessing_version": PREPROCESSING_VERSION,
            "expires_at": min(expiries).isoformat(),
            "consent_records": records,
            "samples": samples,
        }
        await check_user_dataset(session, data)
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        await asyncio.to_thread(validate_manifest, manifest)
        return f"approved://{directory.name}@{sha256_file(manifest)}"
    except BaseException:
        # The directory was just created here, under the fixed private dataset root.
        await asyncio.to_thread(shutil.rmtree, directory)
        raise


async def cleanup_datasets(session):
    # ponytail: scan private manifests hourly; index datasets if the pilot outgrows this.
    for manifest in APPROVED_DATA_ROOT.glob("review-*/manifest.json"):
        if not manifest.resolve().is_relative_to(APPROVED_DATA_ROOT.resolve()):
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        try:
            await check_user_dataset(session, data)
        except ValueError:
            await asyncio.to_thread(shutil.rmtree, manifest.parent)


async def remove_user_training_inputs(session, user_id):
    rows = (
        await session.scalars(
            select(AnnotationTask).where(
                AnnotationTask.user_id == user_id,
            )
        )
    ).all()
    await asyncio.to_thread(
        remove_objects, [input_key(row) for row in rows], settings.annotation_bucket
    )
    await cleanup_datasets(session)
