# Video Effect MVP

This project contains a lightweight Python pipeline for anonymizing faces and masking QR codes in video frames.

## What it does

- Detects faces in each frame
- Blurs or mosaics the face area
- Detects QR codes and blackens them
- Saves a processed MP4 output

## Setup

```bash
cd to-model-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-video-mvp.txt
```

## Run

```bash
python video_effect_mvp.py \
  --input /path/to/input.mp4 \
  --output /path/to/output.mp4 \
  --face-blur-kernel 31 \
  --face-expand-ratio 0.18
```

## Notes

- This is a minimal MVP, not a full AI face-generation system.
- It is intended as the base pipeline for later stages such as:
  - expression exaggeration
  - face deformation for prank edits
  - QR masking in payment scenes
  - timeline-based effect control

## Optional future directions

- add per-scene effect triggers
- add expression-based face exaggeration
- add face replacement or stylization
- add realtime camera mode
