import runpod
import torch
import os
from transformers import pipeline, AutoTokenizer

# Point to where RunPod mounts models
os.environ['HF_HOME'] = '/runpod-volume/huggingface-cache'
os.environ['TRANSFORMERS_CACHE'] = '/runpod-volume/huggingface-cache'
os.environ['HF_HUB_CACHE'] = '/runpod-volume/huggingface-cache/hub'

MODEL_NAME = os.environ.get('MODEL_NAME', 'microsoft/Phi-3-mini-4k-instruct')

print(f"Loading model: {MODEL_NAME}")
print(f"Cache location: {os.environ['HF_HOME']}")

# TEST MODE: Force local files only - will fail if model not cached
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    local_files_only=True  # ← TESTING: Fails if not cached
)

pipe = pipeline(
    "text-generation",
    model=MODEL_NAME,
    tokenizer=tokenizer,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)

print("✓ Model loaded from cache successfully!")

def handler(job):
    job_input = job["input"]
    prompt = job_input.get("prompt", "Hello!")
    max_tokens = job_input.get("max_tokens", 256)
    temperature = job_input.get("temperature", 0.7)
    
    output = pipe(
        prompt,
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=temperature
    )
    
    return {"output": output[0]["generated_text"]}

runpod.serverless.start({"handler": handler})
    return {"output": output[0]["generated_text"]}

runpod.serverless.start({"handler": handler})
