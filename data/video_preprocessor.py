"""
SafeZone AI — Video Preprocessor
==================================
Pure preprocessing functions for converting raw video frames into
the (slow, fast) tensor pair required by SlowFast R50.

This module contains NO dataset or training logic — inference only.

Slow/Fast pathway construction (matches training exactly):
  fast : ALL T frames  →  (1, 3, T=32,      H=224, W=224)
  slow : T//4 frames sampled uniformly  →  (1, 3, T=8, H=224, W=224)

ImageNet normalization matches Kinetics-400 pretraining:
  MEAN = [0.45, 0.45, 0.45]
  STD  = [0.225, 0.225, 0.225]
"""

from __future__ import annotations
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch

from config import VCFG, VideoConfig
from utils.logger import get_logger

logger = get_logger("safezone.video_prep")

# Kinetics-400 normalisation constants (same as used during training)
_MEAN = np.array([0.45, 0.45, 0.45], dtype=np.float32)
_STD  = np.array([0.225, 0.225, 0.225], dtype=np.float32)


# ══════════════════════════════════════════════════════════════════
#  SINGLE FRAME PREPROCESSING
# ══════════════════════════════════════════════════════════════════

def preprocess_frame(
    frame_bgr : np.ndarray,
    frame_size : int = 224,
) -> np.ndarray:
    """
    Convert a raw BGR frame (from OpenCV) to a normalised RGB float32 array.

    Args:
        frame_bgr : HxWx3 uint8 BGR (OpenCV format)
        frame_size: target spatial resolution (square)

    Returns:
        (frame_size, frame_size, 3) float32, normalised with ImageNet stats
    """
    frame = cv2.resize(frame_bgr, (frame_size, frame_size))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = frame.astype(np.float32) / 255.0
    frame = (frame - _MEAN) / _STD
    return frame


# ══════════════════════════════════════════════════════════════════
#  SLOW / FAST PATHWAY CONSTRUCTION
# ══════════════════════════════════════════════════════════════════

def frames_to_slowfast(
    frames    : np.ndarray,
    cfg       : VideoConfig = VCFG,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Convert a stack of preprocessed frames into slow and fast pathway tensors.

    Args:
        frames: (T, H, W, 3) float32, already normalised

    Returns:
        slow : (1, 3, T_slow, H, W)  e.g. (1, 3, 8,  224, 224)
        fast : (1, 3, T,      H, W)  e.g. (1, 3, 32, 224, 224)
    """
    T = frames.shape[0]

    # (T, H, W, 3) → (3, T, H, W)
    video = np.transpose(frames, (3, 0, 1, 2))
    video_t = torch.from_numpy(video.copy()).float()   # (3, T, H, W)

    # Fast pathway: all T frames
    fast = video_t.unsqueeze(0)   # (1, 3, T, H, W)

    # Slow pathway: uniformly sample T_slow frames from T
    T_slow   = cfg.slow_frames    # = cfg.frames // 4 = 8
    step     = max(T // T_slow, 1)
    slow_idx = list(range(0, T, step))[:T_slow]

    # Pad if not enough frames (shouldn't happen in normal use)
    while len(slow_idx) < T_slow:
        slow_idx.append(slow_idx[-1])

    slow = video_t[:, slow_idx, :, :].unsqueeze(0)   # (1, 3, T_slow, H, W)

    return slow, fast


# ══════════════════════════════════════════════════════════════════
#  VIDEO FILE LOADING
# ══════════════════════════════════════════════════════════════════

def load_frames_from_file(
    video_path : str,
    num_frames : int = 32,
    frame_size : int = 224,
) -> Optional[np.ndarray]:
    """
    Load `num_frames` uniformly-sampled frames from a video file.

    Samples frames uniformly across the entire video duration so
    the clip is representative of the whole video (for file upload mode).
    In CCTV mode use `preprocess_frame` directly on the live stream.

    Args:
        video_path : path to .mp4 / .avi or any OpenCV-readable format
        num_frames : number of frames to sample (must match training, default 32)
        frame_size : resize target (must match training, default 224)

    Returns:
        (num_frames, frame_size, frame_size, 3) float32  or  None on error
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return None

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 1:
        logger.warning("Video has 0 frames: %s", video_path)
        cap.release()
        return None

    # Uniformly sample num_frames positions across the video
    if total >= num_frames:
        indices = np.linspace(0, total - 1, num_frames, dtype=int)
    else:
        # Video shorter than required — repeat last frame
        indices = list(range(total)) + [total - 1] * (num_frames - total)

    frames: List[np.ndarray] = []
    last_good: Optional[np.ndarray] = None

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret:
            last_good = preprocess_frame(frame, frame_size)
            frames.append(last_good)
        elif last_good is not None:
            frames.append(last_good)   # pad with last good frame
        else:
            frames.append(np.zeros((frame_size, frame_size, 3), dtype=np.float32))

    cap.release()

    result = np.stack(frames, axis=0)   # (T, H, W, 3)
    logger.debug(
        "Loaded %d frames from '%s'  (video has %d total frames)",
        len(frames), video_path, total,
    )
    return result


# ══════════════════════════════════════════════════════════════════
#  CCTV FRAME BUFFER HELPER
# ══════════════════════════════════════════════════════════════════

class FrameBuffer:
    """
    Rolling buffer for CCTV mode.

    Accumulates preprocessed frames. When `is_ready()` returns True,
    call `get_clip()` to obtain a (T, H, W, 3) numpy array that can
    be passed to `frames_to_slowfast()`.

    Args:
        clip_length : frames per clip (32, matching training)
        stride      : run inference every N new frames (8 = 25% overlap)
        frame_size  : resize target
    """

    def __init__(
        self,
        clip_length : int = 32,
        stride      : int = 8,
        frame_size  : int = 224,
    ):
        from collections import deque
        self._buf        = deque(maxlen=clip_length)
        self.clip_length = clip_length
        self.stride      = stride
        self.frame_size  = frame_size
        self._count      = 0   # total frames added

    def add(self, frame_bgr: np.ndarray) -> None:
        """Add a raw BGR frame (from cap.read()) to the buffer."""
        processed = preprocess_frame(frame_bgr, self.frame_size)
        self._buf.append(processed)
        self._count += 1

    def is_ready(self) -> bool:
        """True when buffer is full AND it's time to run inference."""
        return (
            len(self._buf) == self.clip_length
            and self._count % self.stride == 0
        )

    def get_clip(self) -> np.ndarray:
        """Return (T, H, W, 3) float32 array from the current buffer."""
        return np.stack(list(self._buf), axis=0)

    def reset(self) -> None:
        self._buf.clear()
        self._count = 0
