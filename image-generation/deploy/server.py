"""Bounded, single-GPU image inference API. TLS and identity handled by KServe."""
import base64
import io
import logging
import threading
import time
from contextlib import asynccontextmanager

import torch
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

MODEL = 'stable-diffusion-v1-5/stable-diffusion-v1-5'
REVISION = '451f4fe16113bff5a5d2269ed5ad43b0592e9a14'
lock = threading.Lock()
pipe = None

@asynccontextmanager
async def lifespan(app):
    global pipe
    pipe = StableDiffusionPipeline.from_pretrained(
        '/mnt/models', torch_dtype=torch.float16, variant='fp16',
        use_safetensors=True, local_files_only=True,
    ).to('cuda')
    if pipe.safety_checker is None:
        raise RuntimeError('Expected model safety checker is missing')
    pipe.enable_vae_slicing()
    pipe.set_progress_bar_config(disable=True)
    yield

app = FastAPI(title='reference Image Generation', lifespan=lifespan)

@app.middleware('http')
async def bound_request_size(request, call_next):
    if request.method == 'POST':
        try:
            size = int(request.headers.get('content-length', '-1'))
        except ValueError:
            size = -1
        if size < 0 or size > 8192:
            return JSONResponse(status_code=413, content={'detail':'Supply a JSON body no larger than 8192 bytes.'})
    return await call_next(request)

class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    prompt: str = Field(min_length=1, max_length=500)
    negative_prompt: str = Field(default='', max_length=500)
    steps: int = Field(default=25, ge=10, le=40)
    seed: int = Field(default=42, ge=0, le=2147483647)

@app.get('/health')
def health():
    return {'ready': pipe is not None}

@app.get('/v1/models')
def models():
    return {'data': [{'id': MODEL, 'revision': REVISION, 'size': '512x512'}]}

@app.post('/v1/images/generations')
def generate(request: Request):
    if not request.prompt.strip():
        raise HTTPException(422, 'Enter an image description.')
    for value in (request.prompt, request.negative_prompt):
        if len(pipe.tokenizer(value).input_ids) > pipe.tokenizer.model_max_length:
            raise HTTPException(422, 'Description is too long for this model. Use roughly 50 words or fewer.')
    if not lock.acquire(blocking=False):
        raise HTTPException(429, 'The GPU is busy. Retry after the current image completes.', headers={'Retry-After':'15'})
    started = time.monotonic()
    try:
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            result = pipe(prompt=request.prompt, negative_prompt=request.negative_prompt,
                          height=512, width=512, num_inference_steps=request.steps,
                          guidance_scale=7.5,
                          generator=torch.Generator(device='cuda').manual_seed(request.seed))
        if result.nsfw_content_detected and any(result.nsfw_content_detected):
            raise HTTPException(422, 'The model safety checker blocked this image. Try a different description.')
        buffer = io.BytesIO()
        result.images[0].save(buffer, format='PNG')
        return {'created': int(time.time()), 'model': MODEL, 'seed': request.seed,
                'seconds': round(time.monotonic()-started, 2),
                'peak_gpu_allocated_mib': round(torch.cuda.max_memory_allocated()/1024**2),
                'data': [{'b64_json': base64.b64encode(buffer.getvalue()).decode()}]}
    except HTTPException:
        raise
    except Exception:
        logging.exception('Image generation failed')
        torch.cuda.empty_cache()
        raise HTTPException(500, 'Image generation failed. Check service logs.')
    finally:
        lock.release()
