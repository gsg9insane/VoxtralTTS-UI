from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class VoiceSample:
    sample_id: str
    speaker_name: str
    mood: str
    language_code: str
    file_name: str
    stored_path: str
    duration_seconds: float
    created_at: str
    consent_confirmed: bool
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return Path(self.stored_path)


@dataclass(slots=True)
class VoiceOption:
    label: str
    value: str
    languages: list[str] = field(default_factory=list)
    gender: str = ""
    age: int | None = None
    tags: list[str] = field(default_factory=list)
    source: str = "local"


@dataclass(slots=True)
class SynthesisRequest:
    text: str
    language_code: str
    response_format: str
    speed: float
    pitch_semitones: float
    preset_voice: str | None = None
    reference_audio_path: Path | None = None
    reference_audio_name: str | None = None
    reference_audio_data_url: str | None = None

    @property
    def needs_post_processing(self) -> bool:
        return abs(self.speed - 1.0) > 1e-6 or abs(self.pitch_semitones) > 1e-6


@dataclass(slots=True)
class SynthesisResult:
    audio_bytes: bytes
    output_path: Path
    server_format: str
    final_format: str
    sample_rate: int
    voice_label: str
    language_code: str
