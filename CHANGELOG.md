# Changelog

All notable changes to this project will be documented in this file.

## v0.1.0 - 2026-03-29

First public release of `VoxtralTTS-UI`.

- PySide6 desktop UI for Voxtral TTS
- local workflow through `vLLM-Omni` and `WSL2`
- remote workflow through the `Mistral API`
- premium UI variant with resizable panels
- multiple output formats
- local post-processing for speed and pitch
- repository sanitized for public distribution

Notes:

- local voice cloning is limited by the public Voxtral open-source checkpoint
- remote Mistral API mode is supported
- start from `data/config.example.json` for local setup
