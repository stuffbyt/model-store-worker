# Complete Guide: Building a Docker Image for RunPod Serverless with Model Store

This guide will walk you through creating a serverless worker that properly uses RunPod's model store feature.

## Understanding the Model Store Structure

RunPod caches models at: `/runpod-volume/huggingface-cache/hub/`

The directory structure follows this pattern:
```
/runpod-volume/huggingface-cache/hub/models--{org}--{model-name}/snapshots/{version-hash}/
```

For example: `microsoft/Phi-3-mini-4k-instruct` becomes:
```
/runpod-volume/huggingface-cache/hub/models--microsoft--Phi-3-mini-4k-instruct/snapshots/{hash}/
```

---

## Step 1: Create Project Directory Structure

```bash
mkdir runpod-model-store-worker
cd runpod-model-store-worker
```

Create these files in your project:
- `Dockerfile` - Container definition
- `rp_handler.py` - Your serverless handler
- `requirements.txt` - Python dependencies
- `builder/setup.sh` - Build-time setup script (optional)

---

## Step 2: Create requirements.txt

```txt
runpod>=1.6.2
transformers>=4.38.0
torch>=2.1.0
accelerate>=0.27.0
```

---

## Step 3: Create rp_handler.py

This is the CORRECTED handler that works with RunPod's model store:

```python
import runpod
import torch
import os
from transformers import pipeline

# CRITICAL: Set these BEFORE importing/loading any models
os.environ['HF_HOME'] = '/runpod-volume/huggingface-cache'
os.environ['TRANSFORMERS_CACHE'] = '/runpod-volume/huggingface-cache'
os.environ['HF_HUB_CACHE'] = '/runpod-volume/huggingface-cache/hub'

# Get model name from environment variable
MODEL_NAME = os.environ.get('MODEL_NAME', 'microsoft/Phi-3-mini-4k-instruct')
MODEL_REVISION = os.environ.get('MODEL_REVISION', 'main')

print(f"=" * 60)
print(f"Loading model: {MODEL_NAME}")
print(f"Revision: {MODEL_REVISION}")
print(f"Cache directory: {os.environ['HF_HOME']}")
print(f"=" * 60)

# Check if model exists in cache
model_cache_dir = f'models--{MODEL_NAME.replace("/", "--")}'
model_cache_path = os.path.join(os.environ['HF_HOME'], 'hub', model_cache_dir, 'snapshots')

if os.path.exists(model_cache_path) and os.listdir(model_cache_path):
    snapshots = os.listdir(model_cache_path)
    print(f"✓ Model found in cache!")
    print(f"  Path: {model_cache_path}")
    print(f"  Snapshots: {snapshots}")
else:
    print(f"⚠ Model NOT in cache - will download from HuggingFace")
    print(f"  Expected path: {model_cache_path}")

# Load the model pipeline
print("Loading model pipeline...")
pipe = pipeline(
    "text-generation",
    model=MODEL_NAME,
    revision=MODEL_REVISION,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    model_kwargs={
        "cache_dir": "/runpod-volume/huggingface-cache"
    }
)

print(f"✓ Model loaded successfully!")
print(f"=" * 60)

def handler(event):
    """
    RunPod serverless handler for text generation.
    
    Expected input:
    {
        "input": {
            "prompt": "Your text here",
            "max_tokens": 256,
            "temperature": 0.7
        }
    }
    """
    try:
        input_data = event['input']
        user_prompt = input_data.get('prompt', 'Hello!')
        max_tokens = input_data.get('max_tokens', 256)
        temperature = input_data.get('temperature', 0.7)
        
        print(f"Generating response for: {user_prompt[:50]}...")
        
        # Format as chat messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_prompt}
        ]
        
        # Apply chat template
        formatted_prompt = pipe.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Generate
        outputs = pipe(
            formatted_prompt,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            top_k=50,
            top_p=0.95
        )
        
        result = outputs[0]["generated_text"]
        print(f"✓ Generation complete ({len(result)} chars)")
        
        return {
            "output": result,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "error"
        }

if __name__ == '__main__':
    print("Starting RunPod serverless worker...")
    runpod.serverless.start({'handler': handler})
```

---

## Step 4: Create Dockerfile

```dockerfile
# Use RunPod's PyTorch base image
FROM runpod/pytorch:2.1.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler
COPY rp_handler.py .

# Set the handler as the entry point
CMD ["python", "-u", "rp_handler.py"]
```

---

## Step 5: Build the Docker Image

```bash
# Build the image
docker build -t your-dockerhub-username/model-store-worker:latest .

# Test locally (optional)
docker run --rm \
  -e MODEL_NAME="microsoft/Phi-3-mini-4k-instruct" \
  -e RUNPOD_WEBHOOK_GET_JOB="http://test" \
  your-dockerhub-username/model-store-worker:latest
```

---

## Step 6: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push the image
docker push your-dockerhub-username/model-store-worker:latest
```

---

## Step 7: Deploy to RunPod Serverless

### Via RunPod Dashboard:

1. Go to https://www.runpod.io/console/serverless
2. Click "New Endpoint"
3. Configure:
   - **Container Image**: `your-dockerhub-username/model-store-worker:latest`
   - **Container Disk**: 10 GB (or more depending on your model)
   - **GPU Type**: Select appropriate GPU (e.g., RTX 4090, A40)
   
4. **IMPORTANT - Add Models to Cache**:
   - Scroll to "Select Network Volume" section
   - Click "Cache Models"
   - Add your model: `microsoft/Phi-3-mini-4k-instruct` (or your chosen model)
   - This pre-downloads the model to RunPod's cache
   
5. Set Environment Variables (optional):
   ```
   MODEL_NAME=microsoft/Phi-3-mini-4k-instruct
   MODEL_REVISION=main
   ```

6. Click "Deploy"

---

## Step 8: Test Your Endpoint

Once deployed, you'll get an endpoint ID. Test it:

```bash
curl -X POST https://api.runpod.ai/v2/{YOUR_ENDPOINT_ID}/runsync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": {
      "prompt": "What is the capital of France?",
      "max_tokens": 100,
      "temperature": 0.7
    }
  }'
```

---

## Debugging Tips

### Check Logs

In the RunPod dashboard, click on your endpoint and view the logs. Look for:

✅ **Success indicators:**
```
✓ Model found in cache!
✓ Model loaded successfully!
```

❌ **Problem indicators:**
```
⚠ Model NOT in cache - will download from HuggingFace
```

### Add Debug Code

If you're having issues, add this debugging code right after setting environment variables:

```python
# Debug: Check what's actually in the cache
print("\n=== DEBUG: Cache Directory Contents ===")
cache_root = '/runpod-volume/huggingface-cache'

if os.path.exists(cache_root):
    print(f"✓ Cache root exists: {cache_root}")
    print(f"Contents:")
    for item in os.listdir(cache_root):
        item_path = os.path.join(cache_root, item)
        print(f"  - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
    
    hub_path = os.path.join(cache_root, 'hub')
    if os.path.exists(hub_path):
        print(f"\n✓ Hub directory exists: {hub_path}")
        print(f"Models in hub:")
        for item in os.listdir(hub_path):
            print(f"  - {item}")
else:
    print(f"❌ Cache root does NOT exist: {cache_root}")

print("=" * 60 + "\n")
```

---

## Common Issues & Solutions

### Issue 1: Model keeps downloading instead of using cache

**Solution**: Make sure you added the model via "Cache Models" in the RunPod dashboard when creating the endpoint.

### Issue 2: "No space left on device" error

**Solution**: Increase "Container Disk" size when creating the endpoint (10-20 GB recommended).

### Issue 3: Cold start is still slow

**Solution**: 
- Verify model is actually in cache (check logs for "✓ Model found in cache!")
- Use Active Workers > 0 to keep workers warm
- Consider smaller models for faster loading

### Issue 4: Path not found errors

**Solution**: Double-check you're using `/runpod-volume/huggingface-cache` (NOT `/runpod/model-store/`)

---

## Advanced Configuration

### Using Different Models

To use a different model, set the `MODEL_NAME` environment variable:

```python
# In RunPod dashboard or Docker:
MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
```

Don't forget to add it to the cache via the dashboard!

### Multi-Model Support

To support multiple models in one endpoint:

```python
# Load model based on input
def handler(event):
    input_data = event['input']
    model_name = input_data.get('model', 'microsoft/Phi-3-mini-4k-instruct')
    
    # Load model dynamically
    pipe = pipeline("text-generation", model=model_name, ...)
```

### Custom HuggingFace Token

For private models:

```python
from huggingface_hub import login
login(token=os.environ.get('HF_TOKEN'))
```

Then set `HF_TOKEN` as an environment variable in RunPod.

---

## Performance Tips

1. **Use bfloat16**: Faster inference with minimal quality loss
2. **Set Active Workers > 0**: Keeps workers warm (reduces cold starts)
3. **Right-size your GPU**: Don't use H100 if A40 suffices
4. **Pre-cache models**: Always use the "Cache Models" feature
5. **Monitor token usage**: Set reasonable `max_tokens` limits

---

## Next Steps

- Test with different prompts and parameters
- Add error handling and input validation
- Implement streaming responses (if needed)
- Set up monitoring and alerts
- Configure autoscaling based on load

---

## Summary Checklist

- [ ] Created correct directory structure
- [ ] Fixed handler paths to `/runpod-volume/huggingface-cache`
- [ ] Added `hub` subdirectory in path construction
- [ ] Built and pushed Docker image
- [ ] Deployed to RunPod serverless
- [ ] **Added model to cache via RunPod dashboard**
- [ ] Tested endpoint with sample request
- [ ] Verified "✓ Model found in cache!" in logs
- [ ] Confirmed fast cold start times

The key to success: **Always pre-cache your models via the RunPod dashboard and use the correct path!**
