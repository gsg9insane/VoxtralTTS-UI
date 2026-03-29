#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${HOME}/voxtral-wsl"
VLLM_OMNI_DIR="${WORKDIR}/vllm-omni"
MODEL_ID="${MODEL_ID:-mistralai/Voxtral-4B-TTS-2603}"
HOST="${VOXTRAL_HOST:-0.0.0.0}"
PORT="${VOXTRAL_PORT:-8000}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
EXTRA_ARGS="${VOXTRAL_EXTRA_ARGS:-}"
STAGE_CONFIG="${STAGE_CONFIG:-${VLLM_OMNI_DIR}/vllm_omni/model_executor/stage_configs/voxtral_tts.yaml}"

if [[ ! -d "${VLLM_OMNI_DIR}" ]]; then
  echo "[voxtral-wsl] Missing ${VLLM_OMNI_DIR}. Run /mnt/h/MistralTTS/wsl/bootstrap_voxtral.sh first."
  exit 1
fi

cd "${VLLM_OMNI_DIR}"
source "${WORKDIR}/.venv/bin/activate"

mkdir -p "${WORKDIR}/logs"

SITE_PACKAGES="${WORKDIR}/.venv/lib/python3.12/site-packages"
CUDA_LIB_PATHS=()
while IFS= read -r libdir; do
  CUDA_LIB_PATHS+=("${libdir}")
done < <(find "${SITE_PACKAGES}/nvidia" -maxdepth 2 -type d -name lib 2>/dev/null || true)

if [[ ${#CUDA_LIB_PATHS[@]} -gt 0 ]]; then
  export LD_LIBRARY_PATH="$(IFS=:; echo "${CUDA_LIB_PATHS[*]}"):${LD_LIBRARY_PATH:-}"
fi

COMMAND=(
  python -m vllm_omni.entrypoints.cli.main
  serve "${MODEL_ID}"
  --stage-configs-path "${STAGE_CONFIG}"
  --omni
  --host "${HOST}"
  --port "${PORT}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --trust-remote-code
  --enforce-eager
)

if [[ -n "${EXTRA_ARGS}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_TOKENS=(${EXTRA_ARGS})
  COMMAND+=("${EXTRA_TOKENS[@]}")
fi

echo "[voxtral-wsl] Starting: ${COMMAND[*]}"
"${COMMAND[@]}" 2>&1 | tee -a "${WORKDIR}/logs/voxtral-server.log"
