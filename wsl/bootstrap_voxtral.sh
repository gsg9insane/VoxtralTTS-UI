#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${HOME}/voxtral-wsl"
VLLM_OMNI_DIR="${WORKDIR}/vllm-omni"
MODEL_ID="${MODEL_ID:-mistralai/Voxtral-4B-TTS-2603}"

SYSTEM_PACKAGES=()
command -v ffmpeg >/dev/null 2>&1 || SYSTEM_PACKAGES+=("ffmpeg")
command -v git >/dev/null 2>&1 || SYSTEM_PACKAGES+=("git")
python3 -m pip --version >/dev/null 2>&1 || SYSTEM_PACKAGES+=("python3-pip")
python3 -m venv --help >/dev/null 2>&1 || SYSTEM_PACKAGES+=("python3-venv")
dpkg -s build-essential >/dev/null 2>&1 || SYSTEM_PACKAGES+=("build-essential")
dpkg -s python3-dev >/dev/null 2>&1 || SYSTEM_PACKAGES+=("python3-dev")

if [[ ${#SYSTEM_PACKAGES[@]} -gt 0 ]]; then
  echo "[voxtral-wsl] Installing missing system packages: ${SYSTEM_PACKAGES[*]}"
  sudo apt-get update
  sudo apt-get install -y "${SYSTEM_PACKAGES[@]}"
else
  echo "[voxtral-wsl] System dependencies already available, skipping sudo apt install"
fi

echo "[voxtral-wsl] Preparing workspace at ${WORKDIR}"
mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade "pip<26" uv
export PATH="${WORKDIR}/.venv/bin:${PATH}"

echo "[voxtral-wsl] Installing vLLM (official Linux path)"
uv pip install "vllm==0.18.0" --torch-backend=auto

if [[ ! -d "${VLLM_OMNI_DIR}" ]]; then
  echo "[voxtral-wsl] Cloning vLLM-Omni"
  git clone https://github.com/vllm-project/vllm-omni.git "${VLLM_OMNI_DIR}"
else
  echo "[voxtral-wsl] Updating existing vLLM-Omni checkout"
  git -C "${VLLM_OMNI_DIR}" pull --ff-only
fi

echo "[voxtral-wsl] Installing vLLM-Omni from source"
cd "${VLLM_OMNI_DIR}"
uv pip install -e .

if [[ -n "${HF_TOKEN:-}" ]]; then
  echo "[voxtral-wsl] Logging into Hugging Face"
  "${WORKDIR}/.venv/bin/python" -m huggingface_hub.commands.huggingface_cli login --token "${HF_TOKEN}" || true
else
  cat <<'EOF'
[voxtral-wsl] HF_TOKEN not set.
Before serving Voxtral, ensure you accepted the Hugging Face access conditions for:
  https://huggingface.co/mistralai/Voxtral-4B-TTS-2603
If the model requires authentication, export HF_TOKEN and rerun this script:
  export HF_TOKEN=hf_xxx
EOF
fi

cat <<EOF
[voxtral-wsl] Bootstrap complete.
Workspace: ${WORKDIR}
Model target: ${MODEL_ID}
Next step:
  ${WORKDIR}/vllm-omni/.venv/bin/python -m vllm.entrypoints.cli.main serve ${MODEL_ID} --omni --host 0.0.0.0 --port 8000
Or use the helper:
  /mnt/h/MistralTTS/wsl/start_voxtral_server.sh
EOF
