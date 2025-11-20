import runpod
import torch
import os
from transformers import pipeline, AutoTokenizer

# Get MODEL_NAME from environment (set by RunPod) or use default
MODEL_NAME = os.environ.get('MODEL_NAME', 'microsoft/Phi-3-mini-4k-instruct')

print(f"Loading model: {MODEL_NAME}")

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

# Load model
pipe = pipeline(
    "text-generation",
    model=MODEL_NAME,
    tokenizer=tokenizer,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)

print("Model loaded!")

def handler(job):
    """RunPod serverless handler"""
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