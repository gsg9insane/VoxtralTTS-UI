from __future__ import annotations

import base64
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


DEFAULT_SAMPLE_RATE = 24_000


class AudioProcessor:
    def __init__(self, ffmpeg_command: str = "ffmpeg") -> None:
        self.ffmpeg_command = ffmpeg_command

    def ffmpeg_available(self) -> bool:
        return shutil.which(self.ffmpeg_command) is not None

    def decode_audio(self, audio_bytes: bytes, input_format: str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
        if input_format == "pcm":
            audio = np.frombuffer(audio_bytes, dtype="<f4")
            return audio.astype(np.float32, copy=False), sample_rate

        with io.BytesIO(audio_bytes) as buffer:
            audio, detected_sr = sf.read(buffer, dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio, int(detected_sr)

    def apply_speed_pitch(self, audio: np.ndarray, sample_rate: int, speed: float, pitch_semitones: float) -> tuple[np.ndarray, int]:
        processed = np.asfortranarray(audio)
        if abs(speed - 1.0) > 1e-6:
            processed = librosa.effects.time_stretch(processed, rate=speed)
        if abs(pitch_semitones) > 1e-6:
            processed = librosa.effects.pitch_shift(
                processed,
                sr=sample_rate,
                n_steps=pitch_semitones,
            )
        processed = np.clip(processed, -1.0, 1.0).astype(np.float32, copy=False)
        return processed, sample_rate

    def export(self, audio: np.ndarray, sample_rate: int, output_format: str) -> bytes:
        output_format = output_format.lower()
        if output_format == "pcm":
            return audio.astype("<f4", copy=False).tobytes()
        if output_format in {"wav", "flac"}:
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format=output_format.upper(), subtype="PCM_16")
            return buffer.getvalue()
        if output_format in {"mp3", "aac", "opus"}:
            return self._transcode_with_ffmpeg(audio, sample_rate, output_format)
        raise ValueError(f"Unsupported output format: {output_format}")

    def _transcode_with_ffmpeg(self, audio: np.ndarray, sample_rate: int, output_format: str) -> bytes:
        if not self.ffmpeg_available():
            raise RuntimeError(
                f"`{self.ffmpeg_command}` is required to export {output_format.upper()} after speed/pitch processing."
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_path = temp_root / "input.wav"
            target_path = temp_root / f"output.{output_format}"
            sf.write(source_path, audio, sample_rate, format="WAV", subtype="PCM_16")

            command = [
                self.ffmpeg_command,
                "-y",
                "-i",
                str(source_path),
            ]
            if output_format == "mp3":
                command += ["-codec:a", "libmp3lame", "-q:a", "2"]
            elif output_format == "aac":
                command += ["-codec:a", "aac", "-b:a", "192k"]
            elif output_format == "opus":
                command += ["-codec:a", "libopus", "-b:a", "128k"]
            command.append(str(target_path))

            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg export failed")
            return target_path.read_bytes()

    def prepare_reference_audio_data_url(self, source_path: Path) -> str:
        wav_bytes = self._normalize_reference_audio(source_path)
        encoded = base64.b64encode(wav_bytes).decode("ascii")
        return f"data:audio/wav;base64,{encoded}"

    def _normalize_reference_audio(self, source_path: Path) -> bytes:
        if self.ffmpeg_available():
            return self._transcode_reference_with_ffmpeg(source_path)

        audio, sample_rate = sf.read(str(source_path), dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        if int(sample_rate) != DEFAULT_SAMPLE_RATE:
            audio = librosa.resample(np.asfortranarray(audio), orig_sr=int(sample_rate), target_sr=DEFAULT_SAMPLE_RATE)
        audio = np.clip(audio, -1.0, 1.0).astype(np.float32, copy=False)
        buffer = io.BytesIO()
        sf.write(buffer, audio, DEFAULT_SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return buffer.getvalue()

    def _transcode_reference_with_ffmpeg(self, source_path: Path) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            target_path = temp_root / "reference.wav"
            command = [
                self.ffmpeg_command,
                "-y",
                "-i",
                str(source_path),
                "-ac",
                "1",
                "-ar",
                str(DEFAULT_SAMPLE_RATE),
                "-c:a",
                "pcm_s16le",
                str(target_path),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg reference conversion failed")
            return target_path.read_bytes()
