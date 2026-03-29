from pathlib import Path

import numpy as np
import soundfile as sf

from voxtral_studio.config import AppPaths
from voxtral_studio.services.voice_library import VoiceLibrary


def test_import_and_lookup_voice_sample(tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.wav"
    sf.write(audio_path, np.zeros(24_000, dtype=np.float32), 24_000)

    library = VoiceLibrary(AppPaths(root=tmp_path))
    sample = library.import_sample(
        source_path=audio_path,
        speaker_name="Marco",
        language_code="it",
        mood="calm",
        consent_confirmed=True,
        notes="Test sample",
        tags=["home", "neutral"],
    )

    resolved = library.find("Marco", "calm")
    assert resolved is not None
    assert resolved.sample_id == sample.sample_id
    assert resolved.path.exists()
