#!/usr/bin/env bash
# Crucible — AMD Developer Cloud (MI300X) deploy. Run ON the GPU instance.
#
#   export FIREWORKS_API_KEY=fw-...
#   export HF_TOKEN=hf-...            # only if using a gated model (Llama)
#   bash deploy/amd_deploy.sh
#
# Default model is Qwen2.5-7B-Instruct — ungated, no HF license wall on Day 1.
set -euo pipefail

MODEL="${LOCAL_LLM_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
: "${FIREWORKS_API_KEY:?set FIREWORKS_API_KEY first}"

echo "== 1/4 GPU sanity =="
rocm-smi --showproductname || echo "(rocm-smi unavailable — check the ROCm image)"

echo "== 2/4 .env =="
cat > .env <<EOF
CRUCIBLE_MODE=live
CRUCIBLE_LLM_PROVIDER=fireworks
LOCAL_LLM_MODEL=$MODEL
LOCAL_LLM_BASE_URL=http://vllm:8000/v1
FIREWORKS_API_KEY=$FIREWORKS_API_KEY
HF_TOKEN=${HF_TOKEN:-}
EOF
echo "wrote .env (model: $MODEL)"

echo "== 3/4 containers (vLLM on ROCm + Crucible) =="
docker compose up -d --build

echo "== 4/4 wait for the model, then smoke-test =="
printf "waiting for vLLM"
for i in $(seq 1 120); do
  if curl -sf localhost:8000/v1/models >/dev/null 2>&1; then echo " ready"; break; fi
  printf "."; sleep 5
  [ "$i" = 120 ] && { echo " TIMEOUT — docker logs vllm"; exit 1; }
done

curl -sf localhost:8080/health && echo
curl -sf -X POST localhost:8080/underwrite \
  -H "Content-Type: application/json" \
  -d @data/sample_loans/needs_steps.json.wrapped 2>/dev/null \
  || curl -sf -X POST localhost:8080/underwrite \
       -H "Content-Type: application/json" \
       -d "{\"loan\": $(cat data/sample_loans/needs_steps.json)}" \
  | head -c 400 && echo

echo
echo "DONE. Console: http://<this-box-ip>:8080  (health should say mode=live)"
echo "PROOF STEP: open the console, run James, screenshot the routing trace"
echo "showing local=MI300X + cloud=Fireworks. Save it."
