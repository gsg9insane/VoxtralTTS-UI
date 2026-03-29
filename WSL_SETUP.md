# WSL2 Setup For Voxtral

This guide connects the Windows UI of VoxtralTTS-UI to a `vLLM` / `vLLM-Omni` server running inside Ubuntu on WSL2.

## Why WSL2

According to the official documentation:

- `vLLM` is designed for Linux and is not officially supported on native Windows in the same way
- Microsoft positions WSL2 as the practical path for Linux CUDA workloads on Windows
- services listening inside WSL2 are reachable from Windows through `localhost`

Sources:

- https://docs.vllm.ai/en/v0.11.1/getting_started/installation/gpu/
- https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl
- https://learn.microsoft.com/en-us/windows/wsl/networking
- https://docs.vllm.ai/projects/vllm-omni/en/latest/getting_started/quickstart/
- https://docs.vllm.ai/projects/vllm-omni/en/latest/getting_started/installation/gpu/

## Steps

### 1. Install WSL2 and Ubuntu

Open PowerShell as Administrator:

```powershell
scripts\setup_wsl2_ubuntu.ps1
```

If you prefer to do it manually:

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
```

After any required reboot:

```powershell
wsl -l -v
```

### 2. Verify CUDA inside WSL

Open Ubuntu and run:

```bash
nvidia-smi
```

If the GPU does not appear inside WSL, update:

- NVIDIA drivers for CUDA on WSL
- Windows Update
- the WSL kernel

### 3. Bootstrap the Voxtral runtime inside Ubuntu

From Windows PowerShell:

```powershell
scripts\bootstrap_voxtral_wsl.ps1
```

If the Hugging Face model requires authentication:

```powershell
scripts\bootstrap_voxtral_wsl.ps1 -HfToken "hf_xxx"
```

The script:

- installs Linux dependencies
- creates `~/voxtral-wsl`
- creates a Python 3.12 virtual environment with `uv`
- installs `vllm==0.18.0`
- clones `vllm-omni`
- installs `vllm-omni` from source

### 4. Start the Voxtral server in WSL

```powershell
scripts\start_wsl_voxtral_server.ps1
```

To check status:

```powershell
scripts\wsl_voxtral_status.ps1
```

To stop it:

```powershell
scripts\stop_wsl_voxtral_server.ps1
```

## Connecting the Windows UI

In the UI:

- `Host`: `127.0.0.1`
- `Port`: `8000`
- you do not need to use `Start Local Server` from the UI during the first WSL setup
- use `Check Health`

Once `scripts\start_wsl_voxtral_server.ps1` has started the backend correctly, the Windows UI will talk to the Linux server through `localhost`.

## Important Notes

- the more recent `vLLM-Omni` documentation shows Linux installation with Python `3.12`
- the published `vLLM-Omni` documentation does not always list Voxtral TTS prominently in every summary page, so this workflow is based on the Mistral documentation, the Voxtral materials, and the working integration tested here
- if `vllm-omni` bootstrap fails on your WSL setup, the next practical step is testing a repository revision or tag aligned with the Voxtral release, or using any updated self-hosted runtime guidance published by Mistral
- verified behavior on this setup: preset voices work through `/v1/audio/speech`; local cloning through `ref_audio` is not reliable with the public `mistralai/Voxtral-4B-TTS-2603` checkpoint because the current `vllm-omni` path reaches `encode_waveforms(...)` and requires encoder weights that are not included in the open-source checkpoint

## Quick Commands

Install WSL:

```powershell
scripts\setup_wsl2_ubuntu.ps1
```

Bootstrap runtime:

```powershell
scripts\bootstrap_voxtral_wsl.ps1
```

Start server:

```powershell
scripts\start_wsl_voxtral_server.ps1
```

Stop server:

```powershell
scripts\stop_wsl_voxtral_server.ps1
```
