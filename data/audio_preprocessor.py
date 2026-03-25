"""
SafeZone AI — Audio Preprocessor
===================================
Pure preprocessing functions for converting raw audio (or audio extracted
from a video file) into a log-mel spectrogram tensor.

LogMelConverter is kept identical to audio_dataset.py so spectrogram
computation is exactly consistent with how PANNs was originally designed.

For video file uploads: extracts audio using librosa (which requires ffmpeg).
For CCTV streams: audio extraction from RTSP is not straightforward with
OpenCV — the CCTV inference pipeline therefore runs video-only and returns
neutral audio predictions. See backend/main.py CCTVStreamer for details.
"""

from __future__ import annotations
from typing import Optional

import numpy as np
import torch

from config import ACFG, AudioConfig
from utils.logger import get_logger

logger = get_logger("safezone.audio_prep")


# ══════════════════════════════════════════════════════════════════
#  LOG-MEL CONVERTER  (identical to audio_dataset.py version)
# ══════════════════════════════════════════════════════════════════

class LogMelConverter:
    """
    Converts a 1-D waveform (float32) to a log-mel spectrogram.

    Output: (n_mels, T) float32

    Uses numpy/scipy only — no torchaudio dependency.
    """

    def __init__(self, cfg: AudioConfig = ACFG):
        self.cfg      = cfg
        self._mel_fb  = self._build_mel_filterbank()

    def convert(self, waveform: np.ndarray) -> np.ndarray:
        """
        waveform : (N,) float32
        Returns  : (n_mels, T) float32 log-mel spectrogram
        """
        frames  = self._frame(waveform)
        window  = np.hanning(self.cfg.n_fft).astype(np.float32)
        spec    = np.abs(np.fft.rfft(frames * window, n=self.cfg.n_fft))   # (T, n_fft//2+1)
        mel     = spec @ self._mel_fb.T                                     # (T, n_mels)
        log_mel = np.log(mel + 1e-8).T                                      # (n_mels, T)
        return log_mel.astype(np.float32)

    def _frame(self, waveform: np.ndarray) -> np.ndarray:
        n       = len(waveform)
        indices = (
            np.arange(self.cfg.n_fft)[None, :] +
            np.arange(0, n - self.cfg.n_fft + 1, self.cfg.hop_length)[:, None]
        )
        return waveform[indices]

    def _build_mel_filterbank(self) -> np.ndarray:
        sr      = self.cfg.sample_rate
        n_freqs = self.cfg.n_fft // 2 + 1
        fft_bins = np.linspace(0, sr / 2, n_freqs)

        def hz_to_mel(f): return 2595 * np.log10(1 + f / 700)
        def mel_to_hz(m): return 700  * (10 ** (m / 2595) - 1)

        mel_min = hz_to_mel(self.cfg.fmin)
        mel_max = hz_to_mel(self.cfg.fmax)
        mel_pts = np.linspace(mel_min, mel_max, self.cfg.n_mels + 2)
        hz_pts  = mel_to_hz(mel_pts)

        fb = np.zeros((self.cfg.n_mels, n_freqs), dtype=np.float32)
        for m in range(self.cfg.n_mels):
            lo, ctr, hi = hz_pts[m], hz_pts[m + 1], hz_pts[m + 2]
            for k, f in enumerate(fft_bins):
                if lo <= f <= ctr:
                    fb[m, k] = (f - lo) / (ctr - lo + 1e-8)
                elif ctr < f <= hi:
                    fb[m, k] = (hi - f) / (hi - ctr + 1e-8)
        return fb


# ══════════════════════════════════════════════════════════════════
#  AUDIO LOADING FROM VIDEO FILE
# ══════════════════════════════════════════════════════════════════

def load_audio_from_video(
    video_path      : str,
    sample_rate     : int   = 32000,
    duration_secs   : Optional[float] = 2.0,
    offset_secs     : float = 0.0,
) -> Optional[np.ndarray]:
    """
    Extract audio from a video file and return a fixed-length waveform.

    Requires ffmpeg to be installed (librosa uses it internally).
    Returns None if audio cannot be extracted (e.g. video has no audio track).

    Args:
        video_path    : path to video file (.mp4, .avi, etc.)
        sample_rate   : target sample rate in Hz (default 32000 to match PANNs)
        duration_secs : how many seconds to extract (default 2.0)
        offset_secs   : start offset in seconds (default 0 = beginning)

    Returns:
        (N,) float32 waveform with N = sample_rate × duration_secs,
        or None if extraction failed.
    """
    try:
        import librosa
        waveform, sr = librosa.load(
            video_path,
            sr       = sample_rate,
            mono     = True,
            offset   = offset_secs,
            duration = duration_secs,
        )

        if duration_secs is None:
            return waveform.astype(np.float32)

        n_samples = int(sample_rate * duration_secs)

        # Pad or trim to exact length
        if len(waveform) >= n_samples:
            return waveform[:n_samples].astype(np.float32)

        padded = np.zeros(n_samples, dtype=np.float32)
        padded[:len(waveform)] = waveform
        return padded

    except Exception as e:
        logger.warning(
            "Could not extract audio from '%s': %s  "
            "(video may have no audio track, or ffmpeg is not installed)",
            video_path, e,
        )
        return None


# ══════════════════════════════════════════════════════════════════
#  WAVEFORM → SPECTROGRAM TENSOR
# ══════════════════════════════════════════════════════════════════

def waveform_to_tensor(
    waveform  : np.ndarray,
    cfg       : AudioConfig = ACFG,
) -> torch.Tensor:
    """
    Convert a raw waveform to a spectrogram tensor ready for PANNs.

    Args:
        waveform : (N,) float32 audio samples

    Returns:
        (1, 1, n_mels, T) float32 tensor — batched + channel dim added
    """
    converter = LogMelConverter(cfg)
    log_mel   = converter.convert(waveform)                          # (n_mels, T)
    tensor    = torch.from_numpy(log_mel).unsqueeze(0).unsqueeze(0) # (1, 1, n_mels, T)
    return tensor.float()


def silence_tensor(cfg: AudioConfig = ACFG) -> torch.Tensor:
    """
    Return a spectrogram tensor representing silence.
    Used when audio cannot be extracted (e.g. no audio track in video).
    """
    n_samples = cfg.chunk_samples
    silence   = np.zeros(n_samples, dtype=np.float32)
    return waveform_to_tensor(silence, cfg)
