"""Official-test evaluation for FFHQ-Wrinkle U-Net and SwinUNETR."""

from __future__ import annotations

import csv
import ctypes
import gc
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

from .alignment import YuNetFaceDetector
from .face_parsing import face_mask_from_labels, load_label_map
from .metrics import BinaryConfusion, binary_confusion, metrics_from_confusion, summarize_rows
from .modeling import ModelBundle, load_wrinkle_model
from .paths import MODEL_ROOT
from .prediction import THRESHOLD_VERSION, ThresholdConfig, infer_logits_and_probability
from .preprocess import build_four_channel_tensor
from .quality import pose_metrics

EVALUATION_VERSION = "ffhq-wrinkle-official-test-v1"
EVALUATION_PREPROCESSING_VERSION = "official-masked-rgb+published-weak-texture-v1"
LUMA_BINS = {"low": (None, 85.0), "typical": (85.0, 170.0), "high": (170.0, None)}
SHARPNESS_BINS = {"low": (None, 100.0), "medium": (100.0, 300.0), "high": (300.0, None)}


def image_path_for_id(root: Path, image_id: str) -> Path:
    group = int(image_id) - int(image_id) % 1_000
    return root / f"{group:05d}" / f"{image_id}.png"


def load_image_array(path: Path, mode: str) -> np.ndarray:
    with Image.open(path) as opened:
        return np.asarray(opened.convert(mode)).copy()


def read_test_ids(path: Path) -> list[str]:
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not values or any(len(value) != 5 or not value.isdigit() for value in values):
        raise ValueError("test ID file must contain five-digit IDs")
    if len(values) != len(set(values)):
        raise ValueError("test ID file contains duplicates")
    return values


def fixed_bin(value: float, bins: dict[str, tuple[float | None, float | None]]) -> str:
    for name, (lower, upper) in bins.items():
        if (lower is None or value >= lower) and (upper is None or value < upper):
            return name
    raise ValueError(f"value {value} does not match configured bins")


def current_process_rss_bytes() -> int:
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        process = kernel32.GetCurrentProcess()
        psapi.GetProcessMemoryInfo.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        )
        success = psapi.GetProcessMemoryInfo(
            process, ctypes.byref(counters), counters.cb
        )
        if not success:
            raise OSError("GetProcessMemoryInfo failed")
        return int(counters.WorkingSetSize)
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = int(Path("/proc/self/statm").read_text().split()[1])
        return pages * page_size
    except (AttributeError, FileNotFoundError, OSError):
        return 0


class MemorySampler:
    def __init__(self, interval_seconds: float = 0.02):
        self.interval_seconds = interval_seconds
        self.baseline_bytes = current_process_rss_bytes()
        self.peak_bytes = self.baseline_bytes
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.peak_bytes = max(self.peak_bytes, current_process_rss_bytes())

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict[str, int]:
        self._stop.set()
        self._thread.join()
        self.peak_bytes = max(self.peak_bytes, current_process_rss_bytes())
        return {
            "baseline_rss_bytes": self.baseline_bytes,
            "peak_rss_bytes": self.peak_bytes,
            "peak_rss_delta_bytes": max(0, self.peak_bytes - self.baseline_bytes),
        }


def sample_characteristics(
    image: np.ndarray,
    face_mask: np.ndarray,
) -> dict[str, float | str]:
    grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    selected = face_mask.astype(bool)
    mean_luma = float(grayscale[selected].mean()) if selected.any() else float(grayscale.mean())
    eroded = cv2.erode(selected.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    laplacian = cv2.Laplacian(grayscale, cv2.CV_64F)
    sharpness = float(laplacian[eroded].var()) if eroded.any() else float(laplacian.var())
    return {
        "mean_luma": mean_luma,
        "sharpness": sharpness,
        "luma_group": fixed_bin(mean_luma, LUMA_BINS),
        "sharpness_group": fixed_bin(sharpness, SHARPNESS_BINS),
    }


def analyze_dataset(
    image_ids: list[str],
    data_root: Path,
    yunet_path: Path | None,
) -> dict[str, dict[str, float | str]]:
    detector = YuNetFaceDetector(yunet_path, score_threshold=0.5) if yunet_path and yunet_path.is_file() else None
    result: dict[str, dict[str, float | str]] = {}
    for image_id in image_ids:
        image = load_image_array(
            image_path_for_id(data_root / "images1024x1024", image_id), "RGB"
        )
        labels = load_label_map(data_root / "face-parsed-labels" / f"{image_id}.npy")
        face_mask = face_mask_from_labels(labels, image.shape[:2])
        values = sample_characteristics(image, face_mask)
        values["pose_group"] = "unavailable"
        if detector is not None:
            detections = detector.detect(image)
            if detections:
                pose = pose_metrics(detections[0])
                values.update(pose)
                frontal = (
                    abs(float(pose["roll_degrees"])) <= 10.0
                    and abs(float(pose["yaw_proxy"])) <= 0.20
                    and 0.30 <= float(pose["pitch_proxy"]) <= 0.75
                )
                values["pose_group"] = "frontal" if frontal else "nonfrontal"
        result[image_id] = values
    return result


def load_evaluation_sample(
    data_root: Path,
    image_id: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    image = load_image_array(
        image_path_for_id(data_root / "images1024x1024", image_id), "RGB"
    )
    masked = load_image_array(data_root / "masked_face_images" / f"{image_id}.png", "RGB")
    texture = load_image_array(
        image_path_for_id(data_root / "weak_wrinkle_masks", image_id), "L"
    )
    target = load_image_array(
        data_root / "manual_wrinkle_masks" / f"{image_id}.png", "L"
    ) > 0
    labels = load_label_map(data_root / "face-parsed-labels" / f"{image_id}.npy")
    face_mask = face_mask_from_labels(labels, target.shape)
    tensor = build_four_channel_tensor(masked, texture)
    return image, tensor, target, face_mask


def error_visualization(
    image: np.ndarray,
    prediction: np.ndarray,
    target: np.ndarray,
) -> np.ndarray:
    visual = np.rint(image.astype(np.float32) * 0.55).astype(np.uint8)
    true_positive = prediction & target
    false_positive = prediction & ~target
    false_negative = ~prediction & target
    visual[true_positive] = (32, 255, 32)
    visual[false_positive] = (255, 32, 32)
    visual[false_negative] = (32, 96, 255)
    return visual


def stratified_summary(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row[field]), []).append(row)
    return {name: summarize_rows(group_rows) for name, group_rows in sorted(groups.items())}


def evaluate_architecture(
    architecture: str,
    image_ids: list[str],
    data_root: Path,
    output_dir: Path,
    characteristics: dict[str, dict[str, float | str]],
    requested_device: str,
    threshold: ThresholdConfig,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    sampler = MemorySampler()
    sampler.start()
    bundle = load_wrinkle_model(architecture, requested_device=requested_device)
    if bundle.device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(bundle.device)
    rows: list[dict[str, object]] = []
    candidates: dict[str, tuple[int, str, np.ndarray]] = {}
    latencies: list[float] = []
    for index, image_id in enumerate(image_ids, 1):
        image, tensor, target, face_mask = load_evaluation_sample(data_root, image_id)
        _, probability, latency = infer_logits_and_probability(
            bundle.model, tensor, bundle.device, threshold.positive_class
        )
        prediction = (probability >= threshold.probability) & face_mask
        confusion = binary_confusion(prediction, target)
        row: dict[str, object] = {
            "architecture": bundle.architecture,
            "image_id": image_id,
            **metrics_from_confusion(confusion),
            "inference_seconds": latency,
            **characteristics[image_id],
        }
        rows.append(row)
        latencies.append(latency)
        counts = {
            "largest_true_positive": confusion.true_positive,
            "largest_false_positive": confusion.false_positive,
            "largest_false_negative": confusion.false_negative,
        }
        visualization = None
        for name, count in counts.items():
            if name not in candidates or count > candidates[name][0]:
                if visualization is None:
                    visualization = error_visualization(image, prediction, target)
                candidates[name] = (count, image_id, visualization.copy())
        print(
            f"[{bundle.architecture}] {index}/{len(image_ids)} {image_id} "
            f"dice={row['dice']:.4f} latency={latency:.3f}s",
            flush=True,
        )
    memory = sampler.stop()
    examples_dir = output_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    example_metadata: dict[str, object] = {}
    slug = bundle.architecture.lower()
    for name, (count, image_id, visualization) in candidates.items():
        filename = f"{slug}_{name}_{image_id}.png"
        Image.fromarray(visualization, mode="RGB").save(examples_dir / filename)
        example_metadata[name] = {"image_id": image_id, "pixel_count": count, "file": f"examples/{filename}"}
    latency_array = np.asarray(latencies, dtype=np.float64)
    summary: dict[str, object] = {
        "architecture": bundle.architecture,
        "checkpoint": str(bundle.checkpoint),
        "checkpoint_sha256": bundle.checkpoint_sha256,
        "device": bundle.device_metadata,
        "model_loading_seconds": bundle.load_seconds,
        "inference_latency_seconds": {
            "mean": float(latency_array.mean()),
            "median": float(np.median(latency_array)),
            "p95": float(np.percentile(latency_array, 95)),
            "min": float(latency_array.min()),
            "max": float(latency_array.max()),
        },
        "memory": {
            **memory,
            "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated(bundle.device)) if bundle.device.type == "cuda" else None,
            "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved(bundle.device)) if bundle.device.type == "cuda" else None,
        },
        "overall": summarize_rows(rows),
        "stratified": {
            "luma": stratified_summary(rows, "luma_group"),
            "sharpness": stratified_summary(rows, "sharpness_group"),
            "pose": stratified_summary(rows, "pose_group"),
            "skin_tone": {"status": "unavailable", "reason": "official test metadata does not provide validated skin-tone labels"},
            "facial_region": {"status": "unavailable", "reason": "manual masks are binary and do not contain region labels"},
        },
        "examples": example_metadata,
    }
    del bundle
    gc.collect()
    return summary, rows


def validate_dataset(image_ids: list[str], data_root: Path) -> None:
    missing: list[str] = []
    for image_id in image_ids:
        paths = (
            image_path_for_id(data_root / "images1024x1024", image_id),
            data_root / "masked_face_images" / f"{image_id}.png",
            image_path_for_id(data_root / "weak_wrinkle_masks", image_id),
            data_root / "manual_wrinkle_masks" / f"{image_id}.png",
            data_root / "face-parsed-labels" / f"{image_id}.npy",
        )
        missing.extend(str(path) for path in paths if not path.is_file())
    if missing:
        raise FileNotFoundError("missing evaluation artifacts:\n" + "\n".join(missing[:20]))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_evaluation(
    data_root: Path,
    output_dir: Path,
    architectures: list[str],
    requested_device: str = "auto",
    threshold: ThresholdConfig = ThresholdConfig(),
    limit: int | None = None,
) -> dict[str, object]:
    threshold.validate()
    test_list = data_root / "test_file_lists.txt"
    image_ids = read_test_ids(test_list)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        image_ids = image_ids[:limit]
    validate_dataset(image_ids, data_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    yunet = MODEL_ROOT / "face_detection_yunet_2023mar.onnx"
    characteristics = analyze_dataset(image_ids, data_root, yunet)
    summaries: list[dict[str, object]] = []
    all_rows: list[dict[str, object]] = []
    for architecture in architectures:
        summary, rows = evaluate_architecture(
            architecture,
            image_ids,
            data_root,
            output_dir,
            characteristics,
            requested_device,
            threshold,
        )
        summaries.append(summary)
        all_rows.extend(rows)
    payload: dict[str, object] = {
        "evaluation_version": EVALUATION_VERSION,
        "preprocessing_version": EVALUATION_PREPROCESSING_VERSION,
        "threshold": {
            "version": THRESHOLD_VERSION,
            "probability": threshold.probability,
            "positive_class": threshold.positive_class,
            "selection_policy": "predeclared in Phase 4; not selected on the test set",
        },
        "dataset": {
            "test_list": str(test_list.resolve()),
            "test_list_sha256": hashlib.sha256(test_list.read_bytes()).hexdigest(),
            "official_id_count": len(read_test_ids(test_list)),
            "evaluated_id_count": len(image_ids),
            "limited_run": limit is not None,
            "image_ids": image_ids,
        },
        "models": summaries,
        "artifacts": {"per_image_csv": "per_image_metrics.csv", "examples": "examples/"},
    }
    _json_path = output_dir / "metrics.json"
    _json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(output_dir / "per_image_metrics.csv", all_rows)
    return payload
