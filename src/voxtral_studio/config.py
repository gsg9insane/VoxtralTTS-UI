from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
)

LANGUAGE_PREFIXES: dict[str, str] = {
    "ar": "Arabic",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
}

DEFAULT_SERVER_VOICES: tuple[str, ...] = (
    "casual_female",
    "casual_male",
    "cheerful_female",
    "neutral_female",
    "neutral_male",
    "ar_male",
    "de_female",
    "de_male",
    "es_female",
    "es_male",
    "fr_female",
    "fr_male",
    "hi_female",
    "hi_male",
    "it_female",
    "it_male",
    "nl_female",
    "nl_male",
    "pt_female",
    "pt_male",
)

POST_PROCESSABLE_FORMATS: tuple[str, ...] = ("wav", "flac", "pcm", "mp3", "aac", "opus")
SERVER_RESPONSE_FORMATS: tuple[str, ...] = ("mp3", "wav", "pcm", "flac", "opus")
DEFAULT_MOODS: tuple[str, ...] = (
    "neutral",
    "cheerful",
    "calm",
    "formal",
    "casual",
    "serious",
    "excited",
    "sad",
    "angry",
    "compassionate",
)

LOCAL_PROVIDER = "local"
REMOTE_PROVIDER = "mistral_api"
DEFAULT_REMOTE_BASE_URL = "https://api.mistral.ai"


@dataclass(slots=True)
class RuntimeSettings:
    provider: str = LOCAL_PROVIDER
    model: str = "mistralai/Voxtral-4B-TTS-2603"
    remote_model: str = "voxtral-mini-tts-2603"
    host: str = "127.0.0.1"
    port: int = 8000
    server_command: str = "auto"
    extra_args: str = ""
    ffmpeg_command: str = "ffmpeg"
    request_timeout: float = 180.0
    pass_language_hint: bool = False
    api_base_url: str = DEFAULT_REMOTE_BASE_URL
    api_key: str = ""
    save_api_key: bool = False

    def active_model(self) -> str:
        return self.remote_model if self.provider == REMOTE_PROVIDER else self.model

    def resolved_api_key(self) -> str:
        return self.api_key.strip() or os.environ.get("MISTRAL_API_KEY", "").strip()


@dataclass(slots=True)
class UISettings:
    synthesis_splitter: list[int] = field(default_factory=lambda: [320, 360, 180])
    source_splitter: list[int] = field(default_factory=lambda: [1, 1])
    voice_library_splitter: list[int] = field(default_factory=lambda: [840, 400])
    premium_hero_splitter: list[int] = field(default_factory=lambda: [170, 790])
    premium_hero_collapsed: bool = False


@dataclass(slots=True)
class AppConfig:
    runtime: RuntimeSettings
    ui: UISettings


class AppPaths:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        self.data_dir = self.root / "data"
        self.output_dir = self.data_dir / "outputs"
        self.voice_dir = self.data_dir / "voices"
        self.config_path = self.data_dir / "config.json"
        self.voice_manifest_path = self.voice_dir / "manifest.json"
        self.venv_python_path = self.root / ".venv" / "Scripts" / "python.exe"
        self.venv_site_packages = self.root / ".venv" / "Lib" / "site-packages"

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_dir.mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def detect_python_candidates(root: Path | None = None) -> list[Path]:
    base_root = root or project_root()
    candidates = [
        base_root / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def default_config() -> AppConfig:
    return AppConfig(runtime=RuntimeSettings(), ui=UISettings())


def _merge_dataclass(instance: object, payload: dict[str, object]) -> object:
    for field in fields(instance):
        if field.name not in payload:
            continue
        current = getattr(instance, field.name)
        incoming = payload[field.name]
        if hasattr(current, "__dataclass_fields__") and isinstance(incoming, dict):
            _merge_dataclass(current, incoming)
            continue
        setattr(instance, field.name, incoming)
    return instance


def load_config(paths: AppPaths) -> AppConfig:
    paths.ensure()
    config = default_config()
    if not paths.config_path.exists():
        save_config(paths, config)
        return config
    data = json.loads(paths.config_path.read_text(encoding="utf-8"))
    return _merge_dataclass(config, data)  # type: ignore[return-value]


def save_config(paths: AppPaths, config: AppConfig) -> None:
    paths.ensure()
    paths.config_path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def organize_voices_by_language(voices: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for voice in voices:
        voice_lower = voice.lower()
        language_name = "English"
        for prefix, candidate in LANGUAGE_PREFIXES.items():
            if voice_lower.startswith(f"{prefix}_"):
                language_name = candidate
                break
        grouped.setdefault(language_name, []).append(voice)

    for language_name, names in grouped.items():
        if language_name == "English":
            names.sort(key=lambda value: (0 if value == "neutral_male" else 1, value))
        else:
            names.sort()
    return dict(sorted(grouped.items(), key=lambda item: (0 if item[0] == "English" else 1, item[0].lower())))
