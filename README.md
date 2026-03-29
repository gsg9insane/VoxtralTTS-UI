# VoxtralTTS-UI

[![Release](https://img.shields.io/github/v/release/gsg9insane/VoxtralTTS-UI?display_name=tag)](https://github.com/gsg9insane/VoxtralTTS-UI/releases)
[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%2B%20WSL2-0078D4)](./WSL_SETUP.md)

`VoxtralTTS-UI` is a `PySide6` desktop application for running Voxtral TTS either locally through `vLLM-Omni` or remotely through the `Mistral API`.

It provides:

- preset voice selection
- language-based voice filtering
- local voice sample management
- output export in multiple formats
- local post-processing for `speed` and `pitch`
- WSL2 helpers for Windows users
- a premium UI variant with resizable panels

## Why This Architecture

The official Mistral documentation and the Hugging Face model card point to:

- local deployment with `vllm serve mistralai/Voxtral-4B-TTS-2603 --omni`
- official remote usage through the Mistral API with `Bearer` authentication
- support for 20 preset voices and 9 languages: English, French, Spanish, German, Italian, Portuguese, Dutch, Arabic, Hindi
- an OpenAI-compatible `/v1/audio/speech` endpoint
- `/v1/audio/voices` for voice discovery
- `ref_audio` for cloning-related API flows
- 24 kHz output

The public documentation does not expose official `speed`, `pitch`, or explicit `emotion` fields.
Because of that, the app follows a practical model-aligned approach:

- `mood` is represented through tagged local reference samples
- `speed` and `pitch` are applied locally after generation
- `language` is used to filter voices and organize the UI

## Features

- local runtime start/stop for `vLLM-Omni`
- health checks and runtime logs
- `Local server` and `Mistral API` modes in the `Runtime` tab
- dynamic voice refresh from the backend
- local reference sample library with speaker, mood, language, notes, and tags
- output export to `wav`, `flac`, `pcm`, `mp3`, `aac`, and `opus`
- desktop playback of generated results
- premium UI with resizable panels and compact hero mode

## Installation

### 1. Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -e .
```

Initial local config:

- copy `data/config.example.json` to `data/config.json`
- place your Mistral API key only in the local file or provide it through `MISTRAL_API_KEY`

### 2. Local Voxtral runtime

The recommended local stack is:

```powershell
pip install -U vllm
pip install git+https://github.com/vllm-project/vllm-omni.git --upgrade
```

Notes:

- `Voxtral-4B-TTS-2603` requires a GPU with roughly 16 GB VRAM in BF16 according to the model card
- `ffmpeg` is optional, but recommended if you want `AAC` export or post-processing with `MP3` / `Opus`

### 3. Launch the app

```powershell
python app.py
```

or:

```powershell
voxtral-studio
```

### 4. Included PowerShell scripts

Standard setup and launch:

```powershell
scripts\setup_and_run.ps1
```

Premium setup and launch:

```powershell
scripts\setup_and_run.ps1 -Mode premium
```

Setup with local runtime:

```powershell
scripts\setup_and_run.ps1 -InstallRuntime
```

Build executables:

```powershell
scripts\build_exe.ps1 -Mode both -Clean
```

### 5. Recommended Windows path: WSL2

For real local Voxtral execution on Windows, the recommended path is WSL2 with Ubuntu:

```powershell
scripts\setup_wsl2_ubuntu.ps1
scripts\bootstrap_voxtral_wsl.ps1
scripts\start_wsl_voxtral_server.ps1
```

Full guide:

- [WSL_SETUP.md](./WSL_SETUP.md)

## Usage

### Local server mode

In the `Runtime` tab:

- `Backend`: `Local server`
- `Command`: `vllm`
- `Local model / path`: `mistralai/Voxtral-4B-TTS-2603`
- `Port`: `8000`

Then click `Start Local Server`.

### Preset voice generation

1. Open `Synthesis`
2. Keep `Use preset server voice` enabled
3. Choose language and voice
4. Enter text
5. Choose output format, speed, and pitch
6. Click `Generate`

### Remote Mistral API mode

In the `Runtime` tab:

1. set `Backend` to `Mistral API`
2. keep `API base URL` as `https://api.mistral.ai` unless you need something else
3. use `Remote model` = `voxtral-mini-tts-2603`
4. paste your key in `API key` or provide `MISTRAL_API_KEY`
5. optionally use `Refresh saved voices` to load account voices
6. if you already know a `voice_id`, you can paste it directly into the voice selector

### Local voice sample library

1. Open `Voice Library`
2. Import a clean audio sample
3. Set `Speaker`, `Language`, and `Mood`
4. Confirm consent
5. Use those samples to organize reference material and sessions

## Practical Notes

- short, clean reference samples usually work best for organization and future cloning workflows
- if you want stronger mood control, record multiple samples for the same speaker such as `neutral`, `cheerful`, `calm`, or `serious`
- `PCM` is saved correctly but is not previewed directly inside the UI
- the UI runs natively on Windows, but upstream `vLLM` is not officially supported there in the same way Linux is; WSL2 is the practical route
- with the public `mistralai/Voxtral-4B-TTS-2603` checkpoint, preset voices work locally, but local voice cloning is disabled in the UI because the open-source checkpoint does not include the encoder weights required by the current `vllm-omni` flow
- in `Mistral API` mode, the key can stay in memory only, or be saved locally if you explicitly enable that option

## Project Structure

```text
PREMIUM/
  premium_app.py
  premium_styles.py
  premium_window.py
  README.md
packaging/
  voxtral_studio.spec
  voxtral_studio_premium.spec
scripts/
  bootstrap_voxtral_wsl.ps1
  build_exe.ps1
  setup_wsl2_ubuntu.ps1
  setup_and_run.ps1
  start_wsl_voxtral_server.ps1
  stop_wsl_voxtral_server.ps1
  wsl_voxtral_status.ps1
src/voxtral_studio/
  config.py
  models.py
  main.py
  services/
    audio_tools.py
    server_manager.py
    tts_client.py
    voice_library.py
  ui/
    main_window.py
    styles.py
    workers.py
data/
  config.example.json
  README.md
wsl/
  bootstrap_voxtral.sh
  start_voxtral_server.sh
  stop_voxtral_server.sh
```

## Sources

- [Mistral Voxtral announcement](https://mistral.ai/news/voxtral-tts)
- [Voices docs](https://docs.mistral.ai/capabilities/audio/text_to_speech/voices)
- [Speech docs](https://docs.mistral.ai/capabilities/audio/text_to_speech/speech)
- [Model docs](https://docs.mistral.ai/models/voxtral-tts-26-03)
- [Paper](https://arxiv.org/pdf/2603.25551)
- [Hugging Face model card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603)
- [Official vLLM-Omni demo](https://raw.githubusercontent.com/vllm-project/vllm-omni/main/examples/online_serving/voxtral_tts/gradio_demo.py)

## License

This repository is distributed under `PolyForm Noncommercial 1.0.0`.
See [LICENSE](./LICENSE).
