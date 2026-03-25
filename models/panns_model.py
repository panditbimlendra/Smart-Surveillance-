import os
import torch
import numpy as np
import librosa
import json
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================
class Config:
    # Audio settings
    SAMPLE_RATE = 32000
    CONFIDENCE_THRESHOLD = 0.2  # Debug threshold, adjust as needed
    
    # Analysis settings
    SEGMENT_DURATION = 2
    SEGMENT_OVERLAP = 1
    
    # Output settings
    OUTPUT_DIR = "analysis_results"
    DEBUG_MODE = True  # Set to False to reduce output
    
    # Abnormal sound classes with severity levels
    ABNORMAL_CLASSES = {
        "Gunshot": {"severity": "CRITICAL", "action": "IMMEDIATE_RESPONSE"},
        "Explosion": {"severity": "CRITICAL", "action": "IMMEDIATE_RESPONSE"},
        "Scream": {"severity": "HIGH", "action": "ALERT_GUARDS"},
        "Glass breaking": {"severity": "HIGH", "action": "ALERT_GUARDS"},
        "Shout": {"severity": "MEDIUM", "action": "INVESTIGATE"},
        "Crying": {"severity": "MEDIUM", "action": "INVESTIGATE"},
        "Car horn": {"severity": "MEDIUM", "action": "NOTIFY"},
        "Siren": {"severity": "HIGH", "action": "ALERT_AUTHORITIES"},
        "Alarm": {"severity": "HIGH", "action": "ALERT_GUARDS"},
        "Tire squeal": {"severity": "MEDIUM", "action": "INVESTIGATE"},
        "Engine knocking": {"severity": "MEDIUM", "action": "NOTIFY"},
        "Crash": {"severity": "HIGH", "action": "IMMEDIATE_RESPONSE"},
        "Fight": {"severity": "HIGH", "action": "IMMEDIATE_RESPONSE"},
        "Door slamming": {"severity": "LOW", "action": "NOTE"},
        "Footsteps": {"severity": "LOW", "action": "NOTE"},
        "Machine humming": {"severity": "LOW", "action": "NOTE"},

         # Animal sounds
        "Dog bark": {"severity": "MEDIUM", "action": "INVESTIGATE"},
        "Cat meow": {"severity": "LOW", "action": "NOTE"},
        "Bird chirp": {"severity": "LOW", "action": "NOTE"},
        "Rooster crow": {"severity": "LOW", "action": "NOTE"},
        "Pig oink": {"severity": "LOW", "action": "NOTE"},
        "Cow moo": {"severity": "LOW", "action": "NOTE"},
        "Horse neigh": {"severity": "LOW", "action": "NOTE"},
        "Sheep bleat": {"severity": "LOW", "action": "NOTE"},
        "Insect buzz": {"severity": "LOW", "action": "NOTE"},
        "Frog croak": {"severity": "LOW", "action": "NOTE"},
        "Wolf howl": {"severity": "HIGH", "action": "ALERT_GUARDS"},
        "Monkey screech": {"severity": "MEDIUM", "action": "INVESTIGATE"}
    }
    
    # Expanded mapping for better coverage
    LABEL_MAPPING = {
        # Gunshot
        "Gunshot": "Gunshot",
        "Gunshot, gunfire": "Gunshot",
        "Firearm": "Gunshot",
        # Explosion
        "Explosion": "Explosion",
        "Bomb": "Explosion",
        # Scream / Shout
        "Screaming": "Scream",
        "Scream": "Scream",
        "Shout": "Shout",
        "Yell": "Shout",
        # Glass
        "Glass": "Glass breaking",
        "Glass shattering": "Glass breaking",
        # Crying
        "Crying": "Crying",
        "Cry": "Crying",
        # Car horn
        "Car horn": "Car horn",
        "Horn": "Car horn",
        # Siren
        "Siren": "Siren",
        "Emergency vehicle": "Siren",
        # Alarm
        "Alarm": "Alarm",
        "Burglar alarm": "Alarm",
        # Tire squeal
        "Tire squeal": "Tire squeal",
        "Screeching tires": "Tire squeal",
        # Engine
        "Engine knocking": "Engine knocking",
        "Engine noise": "Engine knocking",
        # Crash
        "Crash": "Crash",
        "Collision": "Crash",
        "Vehicle crash": "Crash",
        # Fight
        "Fight": "Fight",
        "Struggle": "Fight",
        # Door
        "Door slamming": "Door slamming",
        "Door slam": "Door slamming",
        # Footsteps
        "Footsteps": "Footsteps",
        "Running": "Footsteps",
        # Machine
        "Machine humming": "Machine humming",
        "Hum": "Machine humming",

        # Animal sounds - mapping AudioSet labels to our categories
        "Dog": "Dog bark",
        "Dog bark": "Dog bark",
        "Bark": "Dog bark",
        "Cat": "Cat meow",
        "Meow": "Cat meow",
        "Bird": "Bird chirp",
        "Bird chirp": "Bird chirp",
        "Rooster": "Rooster crow",
        "Rooster crowing": "Rooster crow",
        "Pig": "Pig oink",
        "Oink": "Pig oink",
        "Cow": "Cow moo",
        "Moo": "Cow moo",
        "Horse": "Horse neigh",
        "Neigh": "Horse neigh",
        "Sheep": "Sheep bleat",
        "Bleat": "Sheep bleat",
        "Insect": "Insect buzz",
        "Buzz": "Insect buzz",
        "Frog": "Frog croak",
        "Croak": "Frog croak",
        "Wolf": "Wolf howl",
        "Howl": "Wolf howl",
        "Monkey": "Monkey screech",
        "Screech": "Monkey screech"
    }

# ==================== VIDEO PROCESSOR ====================
class VideoProcessor:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        # Removed erroneous self.detector = detector

    def extract_audio_direct(self, video_path):
        audio_path = os.path.join(self.temp_dir, "extracted_audio.wav")
        
        methods = [
            ['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
             '-ar', str(Config.SAMPLE_RATE), '-ac', '1', '-y', audio_path],
            ['ffmpeg', '-i', video_path, '-vn', '-c:a', 'pcm_s16le',
             '-ar', str(Config.SAMPLE_RATE), '-ac', '1', '-y', audio_path],
            ['ffmpeg', '-i', video_path, '-vn', '-c:a', 'aac',
             '-ar', str(Config.SAMPLE_RATE), '-ac', '1', '-y', audio_path],
            ['ffmpeg', '-i', video_path, '-vn', '-c:a', 'copy',
             '-y', os.path.join(self.temp_dir, "temp_audio.aac")]
        ]
        
        for i, cmd in enumerate(methods, 1):
            try:
                if Config.DEBUG_MODE:
                    print(f"  Trying method {i}...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if i == 4 and result.returncode == 0:
                    temp_aac = os.path.join(self.temp_dir, "temp_audio.aac")
                    if os.path.exists(temp_aac) and os.path.getsize(temp_aac) > 0:
                        cmd_convert = ['ffmpeg', '-i', temp_aac, '-acodec', 'pcm_s16le',
                                       '-ar', str(Config.SAMPLE_RATE), '-ac', '1', '-y', audio_path]
                        result = subprocess.run(cmd_convert, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    if Config.DEBUG_MODE:
                        print(f"  ✓ Audio extracted successfully with method {i}")
                    return audio_path
            except Exception:
                continue
        return None
    
    def convert_video_with_ffmpeg(self, video_path):
        converted_path = os.path.join(self.temp_dir, "converted_video.mp4")
        cmd = ['ffmpeg', '-i', video_path, '-c:v', 'libx264', '-c:a', 'aac', '-y', converted_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(converted_path):
                return converted_path
        except:
            pass
        return None
    
    def extract_audio_robust(self, video_path):
        if video_path.lower().endswith(('.wav', '.mp3', '.flac', '.m4a', '.aac')):
            return video_path
        
        audio_path = self.extract_audio_direct(video_path)
        if audio_path:
            return audio_path
        
        converted = self.convert_video_with_ffmpeg(video_path)
        if converted:
            audio_path = self.extract_audio_direct(converted)
            if audio_path:
                return audio_path
        
        try:
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            if video.audio is not None:
                audio_path = os.path.join(self.temp_dir, "moviepy_audio.wav")
                video.audio.write_audiofile(audio_path, fps=Config.SAMPLE_RATE, nbytes=2)
                video.close()
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    return audio_path
        except:
            pass
        return None
    
    # ==================== REMOVED UNUSED METHOD ====================
    # No extract_and_detect_audio anymore
    
    def cleanup(self):
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

# ==================== PANNS DETECTOR ====================
class PANNSDetector:
    def __init__(self):
        from panns_inference import AudioTagging, labels
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        
        model_path = Path('C:/Users/Bimlendra/panns_data/Cnn14_mAP=0.431.pth')
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        self.model = AudioTagging(checkpoint_path=str(model_path), device=self.device)
        self.labels = labels
        print("PANNs model loaded successfully")
    
    def analyze_audio_file(self, audio_path):
        try:
            audio, sr = librosa.load(audio_path, sr=Config.SAMPLE_RATE)
            duration = len(audio) / sr
            print(f"Audio duration: {duration:.2f} seconds")
            
            # Check for silence
            max_amp = np.max(np.abs(audio))
            if max_amp < 0.01:
                print(f"Audio is silent (max amplitude: {max_amp:.4f}) - no sound detected")
                return []
            else:
                print(f"Audio amplitude range: {np.min(audio):.4f} to {np.max(audio):.4f}")
            
            segments = self._create_segments(audio, sr)
            print(f"Analyzing {len(segments)} segments...")
            
            all_detections = []
            for idx, (segment, start_time, end_time) in enumerate(segments):
                detections = self._analyze_segment(segment, start_time, end_time)
                if detections:
                    all_detections.extend(detections)
                    for d in detections:
                        print(f"  Segment {idx+1}: {d['sound']} at {start_time:.1f}s (confidence: {d['confidence']:.1%})")
                elif Config.DEBUG_MODE:
                    # Show top predictions for debugging
                    self._print_top_predictions(segment, start_time)
            
            return all_detections
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _create_segments(self, audio, sr):
        step = Config.SEGMENT_DURATION - Config.SEGMENT_OVERLAP
        segment_samples = int(Config.SEGMENT_DURATION * sr)
        step_samples = int(step * sr)
        segments = []
        start = 0
        while start < len(audio):
            end = min(start + segment_samples, len(audio))
            segment = audio[start:end]
            if len(segment) >= sr:
                segments.append((segment, start / sr, end / sr))
            start += step_samples
        return segments
    
    def _analyze_segment(self, audio_segment, start_time, end_time):
        try:
            if len(audio_segment.shape) == 1:
                audio_segment = audio_segment.reshape(1, -1)
            audio_tensor = torch.from_numpy(audio_segment).float()
            with torch.no_grad():
                clipwise_output, _ = self.model.inference(audio_tensor)
            
            if isinstance(clipwise_output, torch.Tensor):
                probs = clipwise_output[0].cpu().numpy()
            else:
                probs = clipwise_output[0] if len(clipwise_output.shape) > 1 else clipwise_output
            
            detections = []
            for idx, prob in enumerate(probs):
                if prob >= Config.CONFIDENCE_THRESHOLD and idx < len(self.labels):
                    audio_label = self.labels[idx]
                    # Check mapping
                    for abnormal_class, mapped_label in Config.LABEL_MAPPING.items():
                        if audio_label == abnormal_class or audio_label == mapped_label:
                            info = Config.ABNORMAL_CLASSES.get(mapped_label)
                            if info:
                                detections.append({
                                    "sound": mapped_label,
                                    "confidence": float(prob),
                                    "severity": info["severity"],
                                    "action": info["action"],
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "timestamp": start_time
                                })
                                break
            # Deduplicate
            unique = {}
            for d in detections:
                key = f"{d['sound']}_{d['start_time']:.1f}"
                if key not in unique or d['confidence'] > unique[key]['confidence']:
                    unique[key] = d
            return list(unique.values())
        except Exception as e:
            return []
    
    def _print_top_predictions(self, audio_segment, start_time):
        """Print top 5 predictions for debugging."""
        try:
            if len(audio_segment.shape) == 1:
                audio_segment = audio_segment.reshape(1, -1)
            audio_tensor = torch.from_numpy(audio_segment).float()
            with torch.no_grad():
                clipwise_output, _ = self.model.inference(audio_tensor)
            if isinstance(clipwise_output, torch.Tensor):
                probs = clipwise_output[0].cpu().numpy()
            else:
                probs = clipwise_output[0] if len(clipwise_output.shape) > 1 else clipwise_output
            
            # Get top 5 indices
            top_indices = np.argsort(probs)[-5:][::-1]
            print(f"  Segment at {start_time:.1f}s - Top predictions:")
            for idx in top_indices:
                if probs[idx] > 0.1:
                    print(f"    {self.labels[idx]}: {probs[idx]:.2%}")
        except:
            pass

# ==================== RESULT HANDLER ====================
class ResultHandler:
    def __init__(self):
        Path(Config.OUTPUT_DIR).mkdir(exist_ok=True)
    
    def save_results(self, input_path, detections):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = Path(input_path).stem
        report = {
            "input_file": input_path,
            "file_name": file_name,
            "analysis_time": datetime.now().isoformat(),
            "total_detections": len(detections),
            "detections": detections,
            "severity_summary": self._summarize_severities(detections)
        }
        json_path = Path(Config.OUTPUT_DIR) / f"{file_name}_{timestamp}_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        txt_path = Path(Config.OUTPUT_DIR) / f"{file_name}_{timestamp}_report.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ABNORMAL SOUND DETECTION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Input File: {input_path}\n")
            f.write(f"Analysis Time: {report['analysis_time']}\n")
            f.write(f"Total Abnormal Detections: {report['total_detections']}\n\n")
            if detections:
                f.write("DETECTION DETAILS:\n")
                f.write("-" * 80 + "\n")
                for d in detections:
                    f.write(f"\nTime: {d['start_time']:.1f}s - {d['end_time']:.1f}s\n")
                    f.write(f"  Sound: {d['sound']}\n")
                    f.write(f"  Severity: {d['severity']}\n")
                    f.write(f"  Confidence: {d['confidence']:.1%}\n")
                    f.write(f"  Action: {d['action']}\n")
        return json_path, txt_path
    
    def _summarize_severities(self, detections):
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for d in detections:
            summary[d["severity"]] += 1
        return summary
    
    def print_results(self, input_path, detections):
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        print(f"File: {Path(input_path).name}")
        print(f"Abnormal Detections: {len(detections)}")
        if not detections:
            print("\n✅ No abnormal sounds detected")
        else:
            print("\n⚠️  ABNORMAL SOUNDS DETECTED:")
            print("-" * 80)
            for d in detections:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(d["severity"], "⚪")
                print(f"\n{icon} {d['severity']} ALERT")
                print(f"   Time: {d['start_time']:.1f}s - {d['end_time']:.1f}s")
                print(f"   Sound: {d['sound']}")
                print(f"   Confidence: {d['confidence']:.1%}")
                print(f"   Action Required: {d['action']}")
            print("\n" + "-" * 80)
            print("SEVERITY SUMMARY:")
            for s, c in self._summarize_severities(detections).items():
                if c > 0:
                    print(f"   {s}: {c}")

# ==================== MAIN ANALYZER ====================
class AbnormalSoundDetector:
    def __init__(self):
        self.video_processor = VideoProcessor()
        self.result_handler = ResultHandler()
        self._check_ffmpeg()
        print("\nLoading PANNs model...")
        self.detector = PANNSDetector()
    
    def _check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✓ FFmpeg found")
        except:
            print("⚠️  FFmpeg not found (optional, for video files)")
    
    def analyze_file(self, file_path):
        print("\n" + "=" * 80)
        print(f"Analyzing: {Path(file_path).name}")
        print("=" * 80)
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return None
        
        ext = Path(file_path).suffix.lower()
        if ext in ['.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg']:
            print("\n[1/2] Audio file detected, loading directly...")
            detections = self.detector.analyze_audio_file(file_path)
            print("\n[2/2] Saving results...")
            self.result_handler.save_results(file_path, detections)
            self.result_handler.print_results(file_path, detections)
            return detections
        
        elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']:
            print("\n[1/3] Video file detected, extracting audio...")
            audio_path = self.video_processor.extract_audio_robust(file_path)
            if audio_path is None:
                print("\n⚠️  UNABLE TO EXTRACT AUDIO")
                self.video_processor.cleanup()
                return None
            print("\n[2/3] Analyzing extracted audio...")
            detections = self.detector.analyze_audio_file(audio_path)
            print("\n[3/3] Saving results...")
            self.result_handler.save_results(file_path, detections)
            self.result_handler.print_results(file_path, detections)
            self.video_processor.cleanup()
            return detections
        else:
            print(f"✗ Unsupported format: {ext}")
            return None

# ==================== BACKEND COMPATIBILITY ====================
SAFEZONE_AUDIO_CLASSES = ("normal", "scream", "explosion", "glass_break", "gunshot")


class PANNsInference:
    """
    Backend compatibility wrapper for the FastAPI inference pipeline.
    """

    KEYWORD_TO_SAFEZONE = {
        "gunshot": "gunshot",
        "gunfire": "gunshot",
        "machine gun": "gunshot",
        "cap gun": "gunshot",
        "firearm": "gunshot",
        "bang": "gunshot",
        "explosion": "explosion",
        "bomb": "explosion",
        "blast": "explosion",
        "burst": "explosion",
        "pop": "explosion",
        "firecracker": "explosion",
        "fireworks": "explosion",
        "crack": "explosion",
        "scream": "scream",
        "screaming": "scream",
        "shout": "scream",
        "shouting": "scream",
        "yell": "scream",
        "cry": "scream",
        "crying": "scream",
        "glass": "glass_break",
        "shatter": "glass_break",
        "clink": "glass_break",
        "chink": "glass_break",
    }

    def __init__(self, weights_path: str, device):
        from panns_inference import AudioTagging, labels

        device_name = getattr(device, "type", str(device))
        self.device = "cuda" if device_name == "cuda" and torch.cuda.is_available() else "cpu"

        checkpoint_path = weights_path if weights_path and os.path.exists(weights_path) else None
        if checkpoint_path is None:
            fallback_path = Path("C:/Users/Bimlendra/panns_data/Cnn14_mAP=0.431.pth")
            if fallback_path.exists():
                checkpoint_path = str(fallback_path)

        if checkpoint_path is None:
            raise FileNotFoundError(
                "No PANNs checkpoint found. Put the checkpoint in weights/ or C:/Users/Bimlendra/panns_data/."
            )

        self.model = AudioTagging(checkpoint_path=checkpoint_path, device=self.device)
        self.labels = labels

    def predict(self, waveform_input) -> Dict[str, float]:
        waveform = self._prepare_waveform(waveform_input)
        if waveform is None:
            return self.predict_silence()

        segment_samples = int(Config.SAMPLE_RATE * Config.SEGMENT_DURATION)
        step_samples = int(Config.SAMPLE_RATE * (Config.SEGMENT_DURATION - Config.SEGMENT_OVERLAP))
        step_samples = max(step_samples, 1)

        segment_scores = []
        for start in range(0, max(len(waveform) - segment_samples, 0) + 1, step_samples):
            segment = waveform[start:start + segment_samples]
            if len(segment) < segment_samples:
                padded = np.zeros(segment_samples, dtype=np.float32)
                padded[:len(segment)] = segment
                segment = padded
            segment_scores.append(self._predict_segment(segment))

        if not segment_scores:
            segment_scores.append(self._predict_segment(self._pad_waveform(waveform, segment_samples)))

        return self._aggregate_segment_scores(segment_scores)

    def predict_silence(self) -> Dict[str, float]:
        return {
            "normal": 1.0,
            "scream": 0.0,
            "explosion": 0.0,
            "glass_break": 0.0,
            "gunshot": 0.0,
        }

    def _prepare_waveform(self, waveform_input):
        if waveform_input is None:
            return None

        if isinstance(waveform_input, torch.Tensor):
            waveform = waveform_input.detach().cpu().numpy()
        else:
            waveform = np.asarray(waveform_input, dtype=np.float32)

        waveform = np.squeeze(waveform).astype(np.float32)
        if waveform.ndim != 1 or waveform.size == 0:
            return None

        return waveform

    def _pad_waveform(self, waveform: np.ndarray, target_samples: int) -> np.ndarray:
        if waveform.size >= target_samples:
            return waveform[:target_samples]

        padded = np.zeros(target_samples, dtype=np.float32)
        padded[:waveform.size] = waveform
        return padded

    def _predict_segment(self, waveform: np.ndarray) -> Dict[str, float]:
        audio_tensor = torch.from_numpy(waveform.reshape(1, -1)).float()
        with torch.no_grad():
            clipwise_output, _ = self.model.inference(audio_tensor)

        if isinstance(clipwise_output, torch.Tensor):
            probs = clipwise_output[0].detach().cpu().numpy()
        else:
            probs = np.asarray(clipwise_output[0] if np.ndim(clipwise_output) > 1 else clipwise_output)

        return self._map_to_safezone_classes(probs)

    def _aggregate_segment_scores(self, segment_scores) -> Dict[str, float]:
        scores = {key: 0.0 for key in SAFEZONE_AUDIO_CLASSES}

        for segment_score in segment_scores:
            for key, value in segment_score.items():
                scores[key] = max(scores[key], float(value))

        anomaly_max = max(scores["scream"], scores["explosion"], scores["glass_break"], scores["gunshot"])
        scores["normal"] = float(np.clip(1.0 - anomaly_max, 0.0, 1.0))

        total = sum(scores.values())
        if total > 0:
            scores = {key: value / total for key, value in scores.items()}

        return scores

    def _map_to_safezone_classes(self, probs: np.ndarray) -> Dict[str, float]:
        scores = {key: 0.0 for key in SAFEZONE_AUDIO_CLASSES}

        for idx, prob in enumerate(probs):
            if idx >= len(self.labels):
                continue
            mapped = self._map_label_to_safezone(self.labels[idx])
            if mapped:
                scores[mapped] = max(scores[mapped], float(prob))

        anomaly_max = max(scores["scream"], scores["explosion"], scores["glass_break"], scores["gunshot"])
        scores["normal"] = float(np.clip(1.0 - anomaly_max, 0.0, 1.0))

        total = sum(scores.values())
        if total > 0:
            scores = {key: value / total for key, value in scores.items()}

        return scores

    def _map_label_to_safezone(self, label: str):
        label_lower = label.lower()
        for keyword, target in self.KEYWORD_TO_SAFEZONE.items():
            if keyword in label_lower:
                return target
        return None


class PANNsLitModel(torch.nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        raise NotImplementedError("PANNsLitModel is not used in the FastAPI inference server.")

# ==================== MAIN ====================
def main():
    print("\n" + "=" * 80)
    print("🎬 ABNORMAL SOUND DETECTION SYSTEM (Debug Mode)")
    print("=" * 80)
    print(f"Using PANNs - threshold = {Config.CONFIDENCE_THRESHOLD}, see top predictions")
    print("=" * 80)
    
    detector = AbnormalSoundDetector()
    while True:
        print("\n" + "-" * 40)
        file_path = input("Enter file path (audio/video) or 'q' to quit: ").strip().strip('"')
        if file_path.lower() == 'q':
            break
        if not file_path:
            continue
        detector.analyze_file(file_path)
        print("\n" + "-" * 40)
        if input("Analyze another file? (y/n): ").lower() != 'y':
            break
    print("\nExiting...")

if __name__ == "__main__":
    main()
