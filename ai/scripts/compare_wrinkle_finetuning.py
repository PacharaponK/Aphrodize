"""Reproducible research pilot: locally fine-tuned U-Net versus official U-Net.

Run with ai/.venv/Scripts/python.exe ai/scripts/compare_wrinkle_finetuning.py.
Requires official manual masks, face labels and test_file_lists.txt in DATA_ROOT.
Downloads only selected FFHQ images using the existing integrity-checked helper.
This experiment does not activate a model in the application.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.ffhq_wrinkle.evaluation import image_path_for_id, read_test_ids, write_csv
from ai.ffhq_wrinkle.face_parsing import face_mask_from_labels, load_label_map, mask_rgb_image
from ai.ffhq_wrinkle.metrics import binary_confusion, metrics_from_confusion, summarize_rows
from ai.ffhq_wrinkle.modeling import load_wrinkle_model, sha256_file
from ai.ffhq_wrinkle.paths import DATA_ROOT, MODEL_ROOT, REPOSITORY_ROOT
from ai.ffhq_wrinkle.preprocess import build_four_channel_tensor
from ai.ffhq_wrinkle.texture_map import PREPROCESSING_VERSION, generate_texture_map
from ai.scripts.prepare_phase1_data import download_image, MIRROR_REVISION


def make_splits(ids, test_ids, train_count, validation_count, seed):
    if len(test_ids) != 100 or not set(test_ids).issubset(ids):
        raise ValueError("Expected all 100 official test IDs with manual masks")
    available = sorted(set(ids) - set(test_ids))
    if min(train_count, validation_count) < 1 or train_count + validation_count > len(available):
        raise ValueError("Insufficient images for the requested training/validation split")
    np.random.default_rng(seed).shuffle(available)
    splits = {"train": available[:train_count],
              "validation": available[train_count:train_count + validation_count],
              "test": list(test_ids)}
    assert not (set(splits["train"]) & set(splits["validation"]))
    assert not ((set(splits["train"]) | set(splits["validation"])) & set(test_ids))
    return splits


def prepare_sample(image_id, size):
    image = np.asarray(Image.open(image_path_for_id(DATA_ROOT / "images1024x1024", image_id)).convert("RGB"))
    labels = load_label_map(DATA_ROOT / "face-parsed-labels" / f"{image_id}.npy")
    face = face_mask_from_labels(labels, image.shape[:2])
    texture = generate_texture_map(image, face)
    masked = mask_rgb_image(image, face)
    rgb = cv2.resize(masked, (size, size), interpolation=cv2.INTER_AREA)
    texture = cv2.resize(texture, (size, size), interpolation=cv2.INTER_AREA)
    face = face_mask_from_labels(labels, (size, size))
    with Image.open(DATA_ROOT / "manual_wrinkle_masks" / f"{image_id}.png") as opened:
        target = np.asarray(opened.convert("L").resize((size, size), Image.Resampling.NEAREST)) > 0
    x = build_four_channel_tensor(rgb, texture)
    assert x.shape == (4, size, size) and np.isfinite(x).all()
    assert x.min() >= -1 and x.max() <= 1 and face.any() and target.any(), image_id
    return x, target, face


def evaluate(model, ids, prepared, device, name, split):
    model.eval()
    rows = []
    with torch.inference_mode():
        for image_id in ids:
            with np.load(prepared / f"{image_id}.npz", allow_pickle=False) as sample:
                x = torch.from_numpy(sample["x"]).unsqueeze(0).to(device)
                start = time.perf_counter()
                probability = torch.softmax(model(x), dim=1)[0, 1].cpu().numpy()
                elapsed = time.perf_counter() - start
                prediction = (probability >= 0.5) & sample["face"]
                counts = binary_confusion(prediction, sample["target"])
                rows.append({"model": name, "split": split, "image_id": image_id,
                             **metrics_from_confusion(counts), "inference_seconds": elapsed})
                if split == "test":
                    directory = prepared.parent / "predictions" / name.lower().replace(" ", "_")
                    directory.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(prediction.astype(np.uint8) * 255).save(directory / f"{image_id}.png")
    return summarize_rows(rows), rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "storage/artifacts/ffhq_wrinkle_comparison_20261008")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--train-images", type=int, default=50)
    parser.add_argument("--validation-images", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        ids = [f"{i:05d}" for i in range(200)]
        a = make_splits(ids, ids[:100], 50, 20, 2024)
        assert a == make_splits(list(reversed(ids)), ids[:100], 50, 20, 2024)
        assert [len(a[k]) for k in ("train", "validation", "test")] == [50, 20, 100]
        try:
            make_splits(ids, ids[:100], 90, 20, 2024)
        except ValueError:
            pass
        else:
            raise AssertionError("Oversized splits must fail")
        print("PASS: deterministic, disjoint splits; oversized request rejected")
        return
    if not 1 <= args.epochs <= 20 or args.size not in (256, 512, 1024):
        raise ValueError("epochs must be 1..20 and size must be 256, 512 or 1024")
    if (args.output / "metrics.json").exists():
        raise FileExistsError("Completed experiment exists; choose a new --output")
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    test_ids = read_test_ids(DATA_ROOT / "test_file_lists.txt")
    ids = sorted(p.stem for p in (DATA_ROOT / "manual_wrinkle_masks").glob("*.png"))
    splits = make_splits(ids, test_ids, args.train_images, args.validation_images, args.seed)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    protocol = {"experiment_version": "aphrodize-unet-pilot-v1", "seed": args.seed,
                "resolution": [args.size, args.size], "epochs": args.epochs,
                "learning_rate": 1e-4, "loss": "unweighted_cross_entropy", "batch_size": 1,
                "threshold": 0.5, "face_constraint": "labels 1 and 10",
                "preprocessing": f"aligned-FFHQ+{PREPROCESSING_VERSION}+area-resize-{args.size}",
                "test_list_sha256": sha256_file(DATA_ROOT / "test_file_lists.txt"),
                "splits": splits, "selection": "maximum validation micro Dice; test evaluated only after selection",
                "ffhq_mirror_revision": MIRROR_REVISION,
                "limitations": ["Small pilot subset; not full-data training",
                                "Image-ID disjoint splits; identity overlap is unknown",
                                "Generated texture and resized inputs differ from the published 1024px evaluation",
                                "FFHQ research data; not evaluation on Aphrodize users"]}
    protocol_path = output / "protocol.json"
    if protocol_path.exists() and json.loads(protocol_path.read_text()) != protocol:
        raise ValueError("Existing protocol differs; choose a new --output")
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n")
    all_ids = [i for group in splits.values() for i in group]
    downloaded = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {pool.submit(download_image, image_id, DATA_ROOT, 90): image_id for image_id in all_ids}
        for future in as_completed(tasks):
            downloaded.append(future.result())
            print(f"Download {len(downloaded)}/{len(all_ids)}: {tasks[future]}", flush=True)
    (output / "download_manifest.json").write_text(json.dumps(sorted(downloaded, key=lambda x: x["id"]), indent=2) + "\n")
    prepared = output / "prepared"
    prepared.mkdir(exist_ok=True)
    for index, image_id in enumerate(all_ids, 1):
        path = prepared / f"{image_id}.npz"
        if not path.exists():
            x, target, face = prepare_sample(image_id, args.size)
            np.savez_compressed(path, x=x, target=target, face=face)
        print(f"Prepared {index}/{len(all_ids)}: {image_id}", flush=True)
    sources = {"upstream_commit": "aa3c66c819c91034c72b5272caece92de545257f",
               "archives": [{"file": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                            for path in (DATA_ROOT / "manual_wrinkle_masks.zip", DATA_ROOT / "face_parsed_labels.zip")
                            if path.is_file()],
               "samples": [{"image_id": image_id, "split": split,
                            "manual_mask_sha256": sha256_file(DATA_ROOT / "manual_wrinkle_masks" / f"{image_id}.png"),
                            "face_labels_sha256": sha256_file(DATA_ROOT / "face-parsed-labels" / f"{image_id}.npy"),
                            "prepared_sha256": sha256_file(prepared / f"{image_id}.npz")}
                           for split, group in splits.items() for image_id in group]}
    (output / "source_manifest.json").write_text(json.dumps(sources, indent=2) + "\n")
    if args.prepare_only:
        return
    bundle = load_wrinkle_model("UNet", requested_device="cpu")
    model, device = bundle.model, bundle.device
    baseline_validation, _ = evaluate(model, splits["validation"], prepared, device, "Official U-Net", "validation")
    print("Baseline validation Dice:", baseline_validation["micro"]["dice"], flush=True)
    checkpoint = MODEL_ROOT / "experiments" / output.name / "candidate_unet.pth"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if checkpoint.exists():
        raise FileExistsError("Candidate checkpoint exists; choose a new --output")
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    history, best = [], -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for index, image_id in enumerate(splits["train"], 1):
            with np.load(prepared / f"{image_id}.npz", allow_pickle=False) as sample:
                x = torch.from_numpy(sample["x"]).unsqueeze(0).to(device)
                target = torch.from_numpy(sample["target"].astype(np.int64)).unsqueeze(0).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(x), target)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss")
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
            print(f"Epoch {epoch}/{args.epochs} {index}/{len(splits['train'])}: loss={losses[-1]:.6f}", flush=True)
        validation, _ = evaluate(model, splits["validation"], prepared, device, "Aphrodize U-Net", "validation")
        entry = {"epoch": epoch, "train_loss": float(np.mean(losses)), "validation": validation}
        history.append(entry)
        if validation["micro"]["dice"] > best:
            best, selected_epoch = validation["micro"]["dice"], epoch
            torch.save(model.state_dict(), checkpoint)
        (output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
        print(f"Epoch {epoch} validation Dice={validation['micro']['dice']:.6f}; selected epoch={selected_epoch}", flush=True)
    del optimizer, model, bundle
    gc.collect()
    models, all_rows = [], []
    for name, path in (("Official U-Net", None), ("Aphrodize U-Net", checkpoint)):
        bundle = load_wrinkle_model("UNet", checkpoint_path=path, requested_device="cpu", verify_official=path is None)
        overall, rows = evaluate(bundle.model, splits["test"], prepared, device, name, "test")
        assert overall["image_count"] == 100
        assert overall["micro"]["pixel_count"] == 100 * args.size ** 2
        models.append({"name": name, "architecture": "UNet", "checkpoint": str(bundle.checkpoint),
                       "checkpoint_sha256": bundle.checkpoint_sha256, "device": bundle.device_metadata,
                       "overall": overall})
        all_rows.extend(rows)
        print(name, json.dumps(overall["micro"]), flush=True)
        del bundle
        gc.collect()
    assert models[0]["checkpoint_sha256"] != models[1]["checkpoint_sha256"]
    result = {"protocol": protocol, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "selected_epoch": selected_epoch, "models": models, "history": history,
              "baseline_validation": baseline_validation, "artifacts": {"per_image_csv": "per_image_metrics.csv"}}
    write_csv(output / "per_image_metrics.csv", all_rows)
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Completed:", output / "metrics.json", flush=True)


if __name__ == "__main__":
    main()
