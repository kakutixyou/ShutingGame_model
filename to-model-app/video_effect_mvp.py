#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Video effect MVP for face anonymization and QR masking.

This script creates a single-pass video processing pipeline that:
- detects faces in each frame
- blurs or mosaics them
- detects QR codes and masks them
- writes a processed output video

It is intentionally lightweight and easy to extend for richer expressions,
face swaps, and timeline-based trick edits.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except Exception:  # pragma: no cover - optional dependency
    mp = None


FaceBox = Tuple[int, int, int, int]


def detect_face_boxes(frame: np.ndarray, expand_ratio: float = 0.18) -> List[FaceBox]:
    """Return a list of (x, y, w, h) boxes for detected faces."""
    boxes: List[FaceBox] = []
    height, width = frame.shape[:2]

    if mp is not None:
        face_detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5,
        )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detector.process(rgb)
        if results.detections:
            for detection in results.detections:
                rel = detection.location_data.relative_bounding_box
                x = int(rel.xmin * width)
                y = int(rel.ymin * height)
                w = max(1, int(rel.width * width))
                h = max(1, int(rel.height * height))
                pad_x = int(w * expand_ratio)
                pad_y = int(h * expand_ratio)
                x = max(0, x - pad_x)
                y = max(0, y - pad_y)
                w = min(width - x, w + pad_x * 2)
                h = min(height - y, h + pad_y * 2)
                boxes.append((x, y, w, h))

    if boxes:
        return boxes

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        return boxes

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )
    for (x, y, w, h) in faces:
        pad_x = int(w * expand_ratio)
        pad_y = int(h * expand_ratio)
        x = max(0, x - pad_x)
        y = max(0, y - pad_y)
        w = min(width - x, w + pad_x * 2)
        h = min(height - y, h + pad_y * 2)
        boxes.append((x, y, w, h))

    return boxes


def detect_qr_boxes(frame: np.ndarray) -> List[np.ndarray]:
    """Return QR code polygon boxes as numpy arrays."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detector = cv2.QRCodeDetector()
    try:
        data, bbox, _ = detector.detectAndDecode(gray)
        if data and bbox is not None:
            # bbox is [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] or similar
            points = np.asarray(bbox, dtype=np.int32)
            if points.size > 0:
                return [points.reshape(-1, 2)]
    except cv2.error:
        pass

    try:
        _, bbox_list, _ = detector.detectAndDecodeMulti(gray)
        if bbox_list is not None:
            boxes = []
            for bbox in bbox_list:
                if bbox is not None:
                    points = np.asarray(bbox, dtype=np.int32)
                    if points.size > 0:
                        boxes.append(points.reshape(-1, 2))
            return boxes
    except cv2.error:
        pass

    return []


def apply_face_blur(frame: np.ndarray, boxes: Sequence[FaceBox], kernel_size: int = 31) -> np.ndarray:
    """Apply a strong blur to boxes to anonymize faces."""
    out = frame.copy()
    if kernel_size < 3:
        kernel_size = 3
    if kernel_size % 2 == 0:
        kernel_size += 1

    for x, y, w, h in boxes:
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            continue
        roi = out[y : y + h, x : x + w]
        if roi.size == 0:
            continue
        blurred = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
        out[y : y + h, x : x + w] = blurred
    return out


def apply_qr_mask(frame: np.ndarray, boxes: Sequence[np.ndarray]) -> np.ndarray:
    """Black out detected QR boxes to hide payment information."""
    out = frame.copy()
    for box in boxes:
        if box.size == 0:
            continue
        cv2.fillPoly(out, [box], (0, 0, 0))
    return out


def process_video(input_path: str, output_path: str, face_blur_kernel: int = 31, face_expand_ratio: float = 0.18, qr_mask: bool = True) -> None:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open input video: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open output video writer for {output_path}")

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_index += 1

        face_boxes = detect_face_boxes(frame, expand_ratio=face_expand_ratio)
        if face_boxes:
            frame = apply_face_blur(frame, face_boxes, kernel_size=face_blur_kernel)

        if qr_mask:
            qr_boxes = detect_qr_boxes(frame)
            if qr_boxes:
                frame = apply_qr_mask(frame, qr_boxes)

        writer.write(frame)

        if frame_index % 30 == 0:
            print(f"Processed {frame_index}/{total_frames} frames", flush=True)

    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"Video written to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Face blur + QR masking video editor MVP")
    parser.add_argument("--input", type=str, required=True, help="Path to input video")
    parser.add_argument("--output", type=str, required=True, help="Path to processed output video")
    parser.add_argument("--face-blur-kernel", type=int, default=31, help="Gaussian blur strength for faces")
    parser.add_argument("--face-expand-ratio", type=float, default=0.18, help="Expand face boxes before blur")
    parser.add_argument("--disable-qr-mask", action="store_true", help="Disable QR code masking")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        process_video(
            str(input_path),
            args.output,
            face_blur_kernel=args.face_blur_kernel,
            face_expand_ratio=args.face_expand_ratio,
            qr_mask=not args.disable_qr_mask,
        )
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
