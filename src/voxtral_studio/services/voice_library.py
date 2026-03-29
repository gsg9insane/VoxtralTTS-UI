from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf

from voxtral_studio.config import AppPaths
from voxtral_studio.models import VoiceSample


class VoiceLibrary:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.paths.ensure()
        self._samples: list[VoiceSample] = []
        self._load()

    def all_samples(self) -> list[VoiceSample]:
        return list(self._samples)

    def speakers(self) -> list[str]:
        return sorted({sample.speaker_name for sample in self._samples})

    def moods_for_speaker(self, speaker_name: str) -> list[str]:
        moods = {sample.mood for sample in self._samples if sample.speaker_name == speaker_name}
        return sorted(moods)

    def samples_for_speaker(self, speaker_name: str) -> list[VoiceSample]:
        return sorted(
            [sample for sample in self._samples if sample.speaker_name == speaker_name],
            key=lambda item: (item.mood, item.language_code, item.created_at),
        )

    def get(self, sample_id: str) -> VoiceSample | None:
        return next((sample for sample in self._samples if sample.sample_id == sample_id), None)

    def find(self, speaker_name: str, mood: str) -> VoiceSample | None:
        for sample in self._samples:
            if sample.speaker_name == speaker_name and sample.mood == mood:
                return sample
        return None

    def import_sample(
        self,
        source_path: Path,
        speaker_name: str,
        language_code: str,
        mood: str,
        consent_confirmed: bool,
        notes: str = "",
        tags: list[str] | None = None,
    ) -> VoiceSample:
        if not speaker_name.strip():
            raise ValueError("Speaker name is required.")
        if not consent_confirmed:
            raise ValueError("You must confirm consent before saving a cloned voice sample.")

        try:
            info = sf.info(str(source_path))
            duration_seconds = float(info.duration or 0.0)
        except Exception:
            duration_seconds = 0.0
        sample_id = uuid.uuid4().hex
        extension = source_path.suffix or ".wav"
        target_name = f"{sample_id}{extension}"
        target_path = self.paths.voice_dir / target_name
        shutil.copy2(source_path, target_path)

        sample = VoiceSample(
            sample_id=sample_id,
            speaker_name=speaker_name.strip(),
            mood=mood.strip().lower(),
            language_code=language_code,
            file_name=source_path.name,
            stored_path=str(target_path),
            duration_seconds=duration_seconds,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            consent_confirmed=consent_confirmed,
            notes=notes.strip(),
            tags=[tag.strip() for tag in (tags or []) if tag.strip()],
        )
        self._samples.append(sample)
        self._save()
        return sample

    def delete_sample(self, sample_id: str) -> None:
        sample = self.get(sample_id)
        if sample is None:
            return
        path = sample.path
        self._samples = [item for item in self._samples if item.sample_id != sample_id]
        if path.exists():
            path.unlink()
        self._save()

    def _load(self) -> None:
        if not self.paths.voice_manifest_path.exists():
            self._save()
            return
        raw = json.loads(self.paths.voice_manifest_path.read_text(encoding="utf-8"))
        self._samples = [VoiceSample(**item) for item in raw.get("samples", [])]

    def _save(self) -> None:
        payload = {
            "samples": [asdict(sample) for sample in sorted(self._samples, key=lambda item: item.created_at, reverse=True)],
        }
        self.paths.voice_manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
