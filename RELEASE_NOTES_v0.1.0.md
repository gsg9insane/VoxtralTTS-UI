# VoxtralTTS-UI v0.1.0

First public release of VoxtralTTS-UI.

Included in this version:

- PySide6 desktop UI for Voxtral TTS
- local workflow through vLLM-Omni and WSL2
- remote workflow through the Mistral API
- premium UI variant with resizable panels
- multiple output formats
- speed and pitch post-processing
- sanitized public repository structure

Notes:

- local voice cloning is limited by the public Voxtral open-source checkpoint
- remote Mistral API mode is supported
- use `data/config.example.json` as the starting point for local setup
