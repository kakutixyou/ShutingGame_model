#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Video effect MVP with trigger-based expression exaggeration.

Design goal:
- Always protect privacy: face blur + QR masking remain active.
- Only when a trigger event occurs, run a lightweight expression analysis.
- If a face reaction is large enough, apply a prank-style exaggeration effect.
- This keeps the system practical and extensible without requiring a full custom
  facial generation model from the start.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except Exception:  # pragma: no cover - optional dependency
    mp = None


FaceBox = Tuple[int, int, int, int]


def euclidean(p1, p2):
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


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


def analyze_expression(frame: np.ndarray, face_box: FaceBox) -> Dict[str, float]:
    """Return rough expression scores: surprise, laugh, confused, angry."""
    x, y, w, h = face_box
    if w <= 0 or h <= 0:
        return {"surprise": 0.0, "laugh": 0.0, "confused": 0.0, "angry": 0.0}

    face_h = max(1.0, h)
    face_w = max(1.0, w)
    scores = {"surprise": 0.0, "laugh": 0.0, "confused": 0.0, "angry": 0.0}

    # MediaPipe face mesh for a more interpretable approximation.
    if mp is not None:
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            left_eye_top = lm[159]
            left_eye_bottom = lm[145]
            right_eye_top = lm[386]
            right_eye_bottom = lm[374]
            mouth_top = lm[13]
            mouth_bottom = lm[14]
            mouth_left = lm[78]
            mouth_right = lm[308]
            brow_left = lm[27]
            brow_right = lm[276]
            nose_tip = lm[4]

            eye_open = (euclidean((left_eye_top.x, left_eye_top.y), (left_eye_bottom.x, left_eye_bottom.y)) +
                        euclidean((right_eye_top.x, right_eye_top.y), (right_eye_bottom.x, right_eye_bottom.y)))
            mouth_open = euclidean((mouth_top.x, mouth_top.y), (mouth_bottom.x, mouth_bottom.y))
            mouth_width = euclidean((mouth_left.x, mouth_left.y), (mouth_right.x, mouth_right.y))
            brow_gap = euclidean((brow_left.x, brow_left.y), (brow_right.x, brow_right.y))
            nose_y = nose_tip.y

            surprise = min(1.0, (eye_open / max(0.05, face_h / 22.0) + mouth_open / max(0.05, face_h / 18.0)) / 2.5)
            laugh = min(1.0, (mouth_open / max(0.05, face_h / 24.0) + mouth_width / max(0.05, face_w / 10.0)) / 2.0)
            confused = min(1.0, (abs(brow_gap - (face_w / 10.0)) / max(0.05, face_w / 8.0)) / 3.0)
            angry = min(1.0, max(0.0, (brow_gap / max(0.05, face_w / 8.0)) - 1.0) * 0.8)

            scores = {
                "surprise": float(surprise),
                "laugh": float(laugh),
                "confused": float(confused),
                "angry": float(angry),
            }
            return scores

    # Fallback heuristics if MediaPipe is unavailable.
    # These are intentionally simple and explainable.
    scores["surprise"] = min(1.0, 0.22 + (w / max(1.0, frame.shape[1])) * 0.4)
    scores["laugh"] = min(1.0, 0.15 + (h / max(1.0, frame.shape[0])) * 0.45)
    scores["confused"] = min(1.0, 0.18 + abs(w - h) / max(1.0, frame.shape[1]) * 0.8)
    scores["angry"] = min(1.0, 0.12 + (abs(w - 0.4 * frame.shape[1]) / max(1.0, frame.shape[1])) * 0.7)
    return scores


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


def apply_expression_effect(frame: np.ndarray, face_box: FaceBox, trigger: str, strength: float = 1.0) -> np.ndarray:
    """Apply a prank-style expression exaggeration for a given trigger."""
    out = frame.copy()
    x, y, w, h = face_box
    if w <= 0 or h <= 0:
        return out

    if trigger == "surprise":
        eye_h = max(8, int(h * 0.18))
        eye_w = max(12, int(w * 0.18))
        eye_y = y + max(6, int(h * 0.2))
        eye_x1 = x + max(5, int(w * 0.16))
        eye_x2 = x + w - max(5, int(w * 0.16)) - eye_w
        for ex, ey in [(eye_x1, eye_y), (eye_x2, eye_y)]:
            eye_roi = out[ey : ey + eye_h, ex : ex + eye_w]
            if eye_roi.size == 0:
                continue
            enlarged = cv2.resize(eye_roi, (max(2, int(eye_w * (1.6 + strength * 0.5))), max(2, int(eye_h * (1.6 + strength * 0.5)))), interpolation=cv2.INTER_LINEAR)
            out[ey : ey + enlarged.shape[0], ex : ex + enlarged.shape[1]] = enlarged

        mouth_y = y + int(h * 0.7)
        mouth_h = max(10, int(h * 0.18 * (0.8 + strength * 0.7)))
        mouth_w = max(20, int(w * 0.45 * (0.9 + strength * 0.6)))
        mouth_x = x + int(w * 0.3)
        mouth_roi = out[mouth_y : mouth_y + mouth_h, mouth_x : mouth_x + mouth_w]
        if mouth_roi.size > 0:
            mouth_enlarged = cv2.resize(mouth_roi, (mouth_w * 2, mouth_h * 2), interpolation=cv2.INTER_LINEAR)
            out[mouth_y : mouth_y + mouth_enlarged.shape[0], mouth_x : mouth_x + mouth_enlarged.shape[1]] = mouth_enlarged

    elif trigger == "laugh":
        mouth_y = y + int(h * 0.62)
        mouth_h = max(12, int(h * 0.2 * (0.8 + strength * 1.2)))
        mouth_w = max(26, int(w * 0.6 * (0.9 + strength * 0.8)))
        mouth_x = x + int(w * 0.2)
        mouth_roi = out[mouth_y : mouth_y + mouth_h, mouth_x : mouth_x + mouth_w]
        if mouth_roi.size > 0:
            mouth_enlarged = cv2.resize(mouth_roi, (mouth_w * 2, mouth_h * 2), interpolation=cv2.INTER_LINEAR)
            out[mouth_y : mouth_y + mouth_enlarged.shape[0], mouth_x : mouth_x + mouth_enlarged.shape[1]] = mouth_enlarged

    elif trigger == "confused":
        brow_y = y + max(6, int(h * 0.2))
        brow_h = max(8, int(h * 0.1))
        brow_w = max(20, int(w * 0.55))
        brow_x = x + int(w * 0.2)
        brow_roi = out[brow_y : brow_y + brow_h, brow_x : brow_x + brow_w]
        if brow_roi.size > 0:
            brow_enlarged = cv2.resize(brow_roi, (brow_w * 2, brow_h * 2), interpolation=cv2.INTER_LINEAR)
            out[brow_y : brow_y + brow_enlarged.shape[0], brow_x : brow_x + brow_enlarged.shape[1]] = brow_enlarged

    elif trigger == "angry":
        out = cv2.convertScaleAbs(out, alpha=1.2, beta=18)

    # Final effect: higher contrast for emphasis.
    out = cv2.convertScaleAbs(out, alpha=1.08 + strength * 0.12, beta=8)
    return out


def apply_qr_mask(frame: np.ndarray, boxes: Sequence[np.ndarray]) -> np.ndarray:
    """Black out detected QR boxes to hide payment information."""
    out = frame.copy()
    for box in boxes:
        if box.size == 0:
            continue
        cv2.fillPoly(out, [box], (0, 0, 0))
    return out


def select_trigger(expression_scores: Dict[str, float], trigger_mode: str) -> str:
    """Return the strongest matching trigger, or 'none'."""
    if trigger_mode == "none":
        return "none"
    if trigger_mode == "auto":
        strongest = max(expression_scores, key=lambda k: expression_scores[k])
        return strongest if expression_scores[strongest] >= 0.55 else "none"
    if trigger_mode == "surprise":
        return "surprise" if expression_scores.get("surprise", 0.0) >= 0.62 else "none"
    if trigger_mode == "laugh":
        return "laugh" if expression_scores.get("laugh", 0.0) >= 0.6 else "none"
    if trigger_mode == "confused":
        return "confused" if expression_scores.get("confused", 0.0) >= 0.5 else "none"
    if trigger_mode == "angry":
        return "angry" if expression_scores.get("angry", 0.0) >= 0.55 else "none"

    # default: strongest non-zero signal
    strongest = max(expression_scores, key=lambda k: expression_scores[k])
    return strongest if expression_scores[strongest] >= 0.55 else "none"


def process_video(
    input_path: str,
    output_path: str,
    face_blur_kernel: int = 31,
    face_expand_ratio: float = 0.18,
    qr_mask: bool = True,
    trigger_mode: str = "surprise",
    trigger_threshold: float = 0.62,
) -> None:
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

        # Only evaluate reactions when trigger mode is enabled.
        if trigger_mode and trigger_mode.lower() != "none":
            for face_box in face_boxes:
                expression_scores = analyze_expression(frame, face_box)
                trigger = select_trigger(expression_scores, trigger_mode)
                if trigger != "none":
                    if expression_scores.get(trigger, 0.0) >= trigger_threshold:
                        frame = apply_expression_effect(frame, face_box, trigger=trigger, strength=1.0)
                        break

        writer.write(frame)

        if frame_index % 30 == 0:
            print(f"Processed {frame_index}/{total_frames} frames", flush=True)

    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"Video written to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger-based face anonymization and prank expression effect MVP")
    parser.add_argument("--input", type=str, required=True, help="Path to input video")
    parser.add_argument("--output", type=str, required=True, help="Path to processed output video")
    parser.add_argument("--face-blur-kernel", type=int, default=31, help="Gaussian blur strength for faces")
    parser.add_argument("--face-expand-ratio", type=float, default=0.18, help="Expand face boxes before blur")
    parser.add_argument("--disable-qr-mask", action="store_true", help="Disable QR code masking")
    parser.add_argument(
        "--trigger-mode",
        type=str,
        default="surprise",
        choices=["none", "surprise", "laugh", "confused", "angry", "auto"],
        help="Expression trigger to enable. 'auto' uses the strongest detected non-zero expression.",
    )
    parser.add_argument(
        "--trigger-threshold",
        type=float,
        default=0.62,
        help="Strength threshold required before applying a prank expression effect.",
    )
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
            trigger_mode=args.trigger_mode,
            trigger_threshold=args.trigger_threshold,
        )
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
