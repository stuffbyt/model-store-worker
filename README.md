# RunPod Model Store Serverless Worker

This repository contains a **corrected** serverless worker template that properly integrates with RunPod's Model Store feature.

## 🔴 Critical Issue Fixed

The original code used **incorrect paths**:
- ❌ Wrong: `/runpod/model-store/huggingface`
- ✅ Correct: `/runpod-volume/huggingface-cache`

This caused models to download every time instead of using the cache, resulting in slow cold starts.

## 🚀 Quick Start

### 1. Clone/Download Files

You need these files:
- `rp_handler.py` - Corrected handler with proper paths
- `Dockerfile` - Container definition
- `requirements.txt` - Dependencies
- `build-and-push.sh` - Build script (optional)

### 2. Build & Push

```bash
# Make build script executable
chmod +x build-and-push.sh

# Build and push (replace with your Docker Hub username)
./build-and-push.sh your-dockerhub-username
```

Or manually:
```bash
docker build -t your-dockerhub-username/model-store-worker:latest .
docker push your-dockerhub-username/model-store-worker:latest
```

### 3. Deploy to RunPod

1. Go to https://www.runpod.io/console/serverless
2. Click **"New Endpoint"**
3. Configure:
   - **Container Image**: `your-dockerhub-username/model-store-worker:latest`
   - **Container Disk**: 10 GB minimum
   - **GPU**: Select appropriate GPU (e.g., RTX 4090, A40)
4. **IMPORTANT**: Click **"Cache Models"** and add:
   - `microsoft/Phi-3-mini-4k-instruct` (or your model)
5. Click **"Deploy"**

### 4. Test

```bash
curl -X POST https://api.runpod.ai/v2/{YOUR_ENDPOINT_ID}/runsync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": {
      "prompt": "What is the capital of France?",
      "max_tokens": 100
    }
  }'
```

## 📖 Full Documentation

See `model-store-serverless-guide.md` for:
- Complete step-by-step instructions
- Debugging tips
- Common issues & solutions
- Advanced configuration
- Performance optimization

## ✅ What's Fixed

### Environment Variables
```python
# CORRECT paths
os.environ['HF_HOME'] = '/runpod-volume/huggingface-cache'
os.environ['TRANSFORMERS_CACHE'] = '/runpod-volume/huggingface-cache'
os.environ['HF_HUB_CACHE'] = '/runpod-volume/huggingface-cache/hub'
```

### Path Construction
```python
# CORRECT - includes 'hub' subdirectory
model_cache_path = os.path.join(
    os.environ['HF_HOME'], 
    'hub',  # This was missing!
    model_cache_dir, 
    'snapshots'
)
```

## 🎯 Key Features

- ✅ Properly uses RunPod's model cache
- ✅ Fast cold starts (seconds vs minutes)
- ✅ Supports any HuggingFace model
- ✅ Configurable via environment variables
- ✅ Detailed logging for debugging
- ✅ Error handling and status reporting

## 🔧 Configuration

Set these environment variables in RunPod:

```bash
MODEL_NAME=microsoft/Phi-3-mini-4k-instruct  # Your model
MODEL_REVISION=main                           # Model version
```

## 📊 Expected Results

When working correctly, you should see in logs:
```
✓ Model found in cache!
✓ Model loaded successfully!
```

Cold start should be **under 30 seconds** (vs 5+ minutes without cache).

## 🐛 Troubleshooting

### Model keeps downloading?
→ Make sure you added the model via "Cache Models" in RunPod dashboard

### "No space left on device"?
→ Increase Container Disk size to 10-20 GB

### Slow cold starts?
→ Check logs for "✓ Model found in cache!" - if missing, cache isn't working

See full guide for more debugging tips.

## 📝 Example Input/Output

**Input:**
```json
{
  "input": {
    "prompt": "Explain quantum computing in simple terms",
    "max_tokens": 256,
    "temperature": 0.7
  }
}
```

**Output:**
```json
{
  "output": "Quantum computing is...",
  "status": "success"
}
```

## 🤝 Support

Issues? Check:
1. Full guide: `model-store-serverless-guide.md`
2. Logs in RunPod dashboard
3. Model is added to cache in RunPod

## 📄 License

MIT License - feel free to use and modify for your needs.

---

**TL;DR**: Use `/runpod-volume/huggingface-cache` paths, add models to cache via RunPod dashboard, profit! 🚀
