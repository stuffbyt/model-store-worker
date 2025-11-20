import os
import runpod
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ---------------------------
# Config
# ---------------------------

# HF repo id – can be overridden by env (e.g. what Model Store sets)
MODEL_ID = os.environ.get("MODEL_NAME", "microsoft/Phi-3-mini-4k-instruct")

# Root of the HF-style cache that Model Store mounts
HF_CACHE_ROOT = "/runpod-volume/huggingface-cache/hub"

# Force offline behavior for testing
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


# ---------------------------
# Helper: resolve snapshot path for MODEL_ID
# ---------------------------

def resolve_snapshot_path(model_id: str) -> str:
    """
    Convert a HF model id like 'microsoft/Phi-3-mini-4k-instruct'
    into its local snapshot path inside Model Store cache.

    Expected layout:
      /runpod-volume/huggingface-cache/hub/
        models--ORG--NAME/
          snapshots/{hash}/...
          refs/main  (optional)
    """
    if "/" not in model_id:
        raise ValueError(f"MODEL_ID '{model_id}' is not in 'org/name' format")

    org, name = model_id.split("/", 1)

    model_root = os.path.join(
        HF_CACHE_ROOT,
        f"models--{org}--{name}"
    )

    refs_main = os.path.join(model_root, "refs", "main")
    snapshots_dir = os.path.join(model_root, "snapshots")

    print(f"[ModelStore] MODEL_ID: {model_id}")
    print(f"[ModelStore] Model root: {model_root}")
    print(f"[ModelStore] refs/main: {refs_main}")
    print(f"[ModelStore] snapshots dir: {snapshots_dir}")

    # 1) Preferred: use refs/main to get active snapshot hash
    if os.path.isfile(refs_main):
        with open(refs_main, "r") as f:
            snapshot_hash = f.read().strip()
        candidate = os.path.join(snapshots_dir, snapshot_hash)
        if os.path.isdir(candidate):
            print(f"[ModelStore] Using snapshot from refs/main: {candidate}")
            return candidate
        else:
            print(f"[ModelStore] Snapshot from refs/main not found on disk: {candidate}")

    # 2) Fallback: list snapshots directory and pick one
    if not os.path.isdir(snapshots_dir):
        raise RuntimeError(
            f"[ModelStore] snapshots directory not found: {snapshots_dir}"
        )

    versions = [d for d in os.listdir(snapshots_dir)
                if os.path.isdir(os.path.join(snapshots_dir, d))]

    if not versions:
        raise RuntimeError(
            f"[ModelStore] No snapshot subdirectories found under {snapshots_dir}"
        )

    versions.sort()
    chosen = os.path.join(snapshots_dir, versions[0])
    print(f"[ModelStore] Using first available snapshot: {chosen}")
    return chosen


# ---------------------------
# Load model strictly from local snapshot (offline)
# ---------------------------

LOCAL_MODEL_PATH = resolve_snapshot_path(MODEL_ID)
print(f"[ModelStore] Resolved local model path: {LOCAL_MODEL_PATH}")

# Strict offline: ONLY load from local files; will fail if Model Store
# did not actually place the model on disk at the expected path.
tokenizer = AutoTokenizer.from_pretrained(
    LOCAL_MODEL_PATH,
    trust_remote_code=True,
    local_files_only=True,
)

model = AutoModelForCausalLM.from_pretrained(
    LOCAL_MODEL_PATH,
    trust_remote_code=True,
    torch_dtype="auto",
    device_map="auto",
    local_files_only=True,
)

text_gen = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    torch_dtype="auto",
    device_map="auto",
)

print("[ModelStore] ✅ Model loaded from local snapshot (offline test)")


# ---------------------------
# RunPod handler
# ---------------------------

def handler(job):
    """
    RunPod serverless handler.

    Expected input:
    {
      "input": {
        "prompt": "Your prompt here",
        "max_tokens": 256,
        "temperature": 0.7
      }
    }
    """
    job_input = job.get("input", {}) or {}

    prompt = job_input.get("prompt", "Hello from Model Store offline test!")
    max_tokens = int(job_input.get("max_tokens", 256))
    temperature = float(job_input.get("temperature", 0.7))

    print(f"[Handler] Prompt: {prompt[:80]!r}")
    print(f"[Handler] max_tokens={max_tokens}, temperature={temperature}")

    try:
        outputs = text_gen(
            prompt,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
        )
        generated = outputs[0]["generated_text"]
        print(f"[Handler] Generated length: {len(generated)} chars")

        return {
            "status": "success",
            "output": generated,
        }

    except Exception as e:
        print(f"[Handler] ❌ Error during generation: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


runpod.serverless.start({"handler": handler})
