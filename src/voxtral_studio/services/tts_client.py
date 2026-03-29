from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from voxtral_studio.config import (
    DEFAULT_SERVER_VOICES,
    LOCAL_PROVIDER,
    REMOTE_PROVIDER,
    SUPPORTED_LANGUAGES,
    organize_voices_by_language,
)
from voxtral_studio.models import SynthesisRequest, VoiceOption


class TTSClient:
    def __init__(
        self,
        provider: str,
        model: str,
        host: str = "127.0.0.1",
        port: int = 8000,
        api_base_url: str = "https://api.mistral.ai",
        api_key: str = "",
        timeout: float = 180.0,
        pass_language_hint: bool = False,
    ) -> None:
        self.provider = provider
        self.host = host
        self.port = port
        self.model = model
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.pass_language_hint = pass_language_hint

    @property
    def base_url(self) -> str:
        if self.provider == REMOTE_PROVIDER:
            return f"{self.api_base_url}/v1"
        return f"http://{self.host}:{self.port}/v1"

    @property
    def health_url(self) -> str:
        if self.provider == REMOTE_PROVIDER:
            return f"{self.base_url}/models"
        return f"http://{self.host}:{self.port}/health"

    def check_health(self) -> tuple[bool, str]:
        try:
            response = httpx.get(self.health_url, headers=self._headers(), timeout=10.0)
            response.raise_for_status()
            if self.provider == REMOTE_PROVIDER:
                return True, "Mistral API reachable"
            return True, "Server ready"
        except Exception as exc:
            return False, str(exc)

    def list_server_voices(self) -> dict[str, list[VoiceOption]]:
        fallback = self._fallback_voice_groups()
        try:
            response = httpx.get(
                f"{self.base_url}/audio/voices",
                headers=self._headers(),
                timeout=10.0,
            )
            response.raise_for_status()
        except Exception:
            return fallback

        payload = response.json()
        raw_voices = payload.get("voices", payload)
        if self.provider == REMOTE_PROVIDER:
            return self._parse_remote_voice_groups(raw_voices)

        voice_names: list[str] = []
        if isinstance(raw_voices, list):
            for item in raw_voices:
                if isinstance(item, str):
                    voice_names.append(item)
                elif isinstance(item, dict):
                    candidate = item.get("slug") or item.get("id") or item.get("name")
                    if isinstance(candidate, str):
                        voice_names.append(candidate)
        if not voice_names:
            return fallback
        grouped = organize_voices_by_language(sorted(set(voice_names)))
        return {
            language: [
                VoiceOption(
                    label=voice,
                    value=voice,
                    languages=[self._language_code_for_voice(voice)],
                    source="local",
                )
                for voice in names
            ]
            for language, names in grouped.items()
        }

    def generate(self, request: SynthesisRequest, force_server_format: str | None = None) -> tuple[bytes, str]:
        payload = self._build_payload(request, force_server_format=force_server_format)
        response = httpx.post(
            f"{self.base_url}/audio/speech",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error_detail(response)
            if detail:
                raise RuntimeError(f"TTS request failed: {detail}") from exc
            raise
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            audio_data = data.get("audio_data")
            if not isinstance(audio_data, str):
                raise RuntimeError("The TTS endpoint returned JSON without `audio_data`.")
            return base64.b64decode(audio_data), payload["response_format"]
        return response.content, payload["response_format"]

    def _build_payload(self, request: SynthesisRequest, force_server_format: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "input": request.text.strip(),
            "model": self.model,
            "response_format": force_server_format or request.response_format,
        }
        if self.pass_language_hint and self.provider == LOCAL_PROVIDER:
            payload["language"] = request.language_code
        if request.preset_voice:
            payload[self._voice_field_name()] = request.preset_voice
        if request.reference_audio_data_url:
            if self.provider == REMOTE_PROVIDER:
                payload["ref_audio"] = self._data_url_to_base64(request.reference_audio_data_url)
            else:
                payload["task_type"] = "Base"
                payload["x_vector_only_mode"] = True
                payload["ref_audio"] = request.reference_audio_data_url
        elif request.reference_audio_path:
            audio_path = Path(request.reference_audio_path)
            if self.provider == REMOTE_PROVIDER:
                payload["ref_audio"] = base64.b64encode(audio_path.read_bytes()).decode("ascii")
            else:
                mime_type = self._guess_audio_mime_type(audio_path)
                payload["task_type"] = "Base"
                payload["x_vector_only_mode"] = True
                payload["ref_audio"] = (
                    f"data:{mime_type};base64,"
                    f"{base64.b64encode(audio_path.read_bytes()).decode('ascii')}"
                )
        return payload

    def _guess_audio_mime_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".wav":
            return "audio/wav"
        if suffix == ".mp3":
            return "audio/mpeg"
        if suffix == ".flac":
            return "audio/flac"
        if suffix in {".m4a", ".mp4"}:
            return "audio/mp4"
        if suffix == ".aac":
            return "audio/aac"
        if suffix == ".opus":
            return "audio/opus"
        if suffix == ".ogg":
            return "audio/ogg"
        return "application/octet-stream"

    def _extract_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return response.text.strip()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str):
                    return message
            message = payload.get("message")
            if isinstance(message, str):
                return message
        return response.text.strip()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.provider == REMOTE_PROVIDER and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _voice_field_name(self) -> str:
        return "voice_id" if self.provider == REMOTE_PROVIDER else "voice"

    def _fallback_voice_groups(self) -> dict[str, list[VoiceOption]]:
        if self.provider == REMOTE_PROVIDER:
            return {"Saved Voices": []}
        grouped = organize_voices_by_language(list(DEFAULT_SERVER_VOICES))
        return {
            language: [
                VoiceOption(
                    label=voice,
                    value=voice,
                    languages=[self._language_code_for_voice(voice)],
                    source="local",
                )
                for voice in names
            ]
            for language, names in grouped.items()
        }

    def _parse_remote_voice_groups(self, raw_voices: Any) -> dict[str, list[VoiceOption]]:
        grouped: dict[str, list[VoiceOption]] = {}
        if not isinstance(raw_voices, list):
            return {"Saved Voices": []}

        language_map = {code: label for code, label in SUPPORTED_LANGUAGES}
        for item in raw_voices:
            if not isinstance(item, dict):
                continue
            voice_id = item.get("id") or item.get("voice_id") or item.get("slug") or item.get("name")
            if not isinstance(voice_id, str) or not voice_id.strip():
                continue
            label = item.get("name") or item.get("slug") or voice_id
            if not isinstance(label, str):
                label = voice_id
            tags = item.get("tags")
            parsed_tags = [tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else []
            gender = item.get("gender") if isinstance(item.get("gender"), str) else ""
            age = item.get("age") if isinstance(item.get("age"), int) else None
            languages = item.get("languages")
            parsed_languages: list[str] = []
            groups: list[str] = []
            if isinstance(languages, list):
                for language in languages:
                    if isinstance(language, str):
                        parsed_languages.append(language.lower())
                        groups.append(language_map.get(language.lower(), language))
            if not groups:
                groups = ["Saved Voices"]
            option = VoiceOption(
                label=label,
                value=voice_id,
                languages=parsed_languages,
                gender=gender,
                age=age,
                tags=parsed_tags,
                source="remote",
            )
            for group in groups:
                grouped.setdefault(group, []).append(option)

        if not grouped:
            return {"Saved Voices": []}
        for group, options in grouped.items():
            options.sort(key=lambda item: item.label.lower())
        return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))

    def _data_url_to_base64(self, value: str) -> str:
        if value.startswith("data:") and "," in value:
            return value.split(",", 1)[1]
        return value

    def _language_code_for_voice(self, voice: str) -> str:
        prefix = voice.lower().split("_", 1)[0]
        supported_codes = {code for code, _ in SUPPORTED_LANGUAGES}
        return prefix if prefix in supported_codes else "en"
