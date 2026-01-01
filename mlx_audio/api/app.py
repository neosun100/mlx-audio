"""MLX-Audio FastAPI 三合一应用 - UI/API/MCP集成"""
import asyncio
import io
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import mlx.core as mx
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mlx_audio.config import config
from mlx_audio.models.memory_manager import memory_manager
from mlx_audio.utils import load_model


# === Pydantic Models ===
class SpeechRequest(BaseModel):
    model: str = config.model.default_tts_model
    input: str
    voice: Optional[str] = None
    speed: float = 1.0
    lang_code: str = "a"
    temperature: float = 0.7
    response_format: str = "wav"
    blended_voice: Optional[str] = None  # base64编码的混合声音


class ModelRequest(BaseModel):
    model_name: str


# === Lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 预加载模型...")
    for model_name in config.model.preload_models:
        try:
            get_tts_model(model_name) if "whisper" not in model_name.lower() else get_stt_model(model_name)
            print(f"  ✅ {model_name}")
        except Exception as e:
            print(f"  ⚠️  {model_name}: {e}")
    
    asyncio.create_task(memory_manager.start_cleanup_loop())
    yield
    memory_manager.stop_cleanup_loop()
    memory_manager.release_all()


# === App ===
app = FastAPI(
    title="MLX-Audio",
    description="TTS/STT API on Apple Silicon",
    version="0.2.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# === Helper ===
def get_tts_model(model_name: str):
    return memory_manager.get_model(model_name, lambda: load_model(model_name))


def get_stt_model(model_name: str):
    return memory_manager.get_model(model_name, lambda: load_model(model_name))


# 语言对应的默认声音
LANG_DEFAULT_VOICE = {
    "a": "af_heart",
    "b": "bf_emma", 
    "z": "zf_xiaobei",
    "j": "jf_alpha",
}


# === API Routes ===
@app.get("/api/health")
async def health():
    stats = memory_manager.get_stats()
    # 分类TTS和STT模型
    tts_models = [m for m in stats['loaded_models'] if 'whisper' not in m.lower()]
    stt_models = [m for m in stats['loaded_models'] if 'whisper' in m.lower()]
    
    return {
        "status": "ok",
        "models": {
            "tts": tts_models,
            "stt": stt_models,
            "total_memory_mb": stats['memory_mb']
        }
    }


@app.get("/v1/models")
async def list_models():
    models = memory_manager.list_models()
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "created": int(time.time())} for m in models]
    }


@app.post("/v1/models")
async def add_model(req: ModelRequest):
    get_tts_model(req.model_name)
    return {"status": "success", "message": f"Model {req.model_name} loaded"}


@app.delete("/v1/models/{model_name}")
async def remove_model(model_name: str):
    if memory_manager.release(model_name):
        return {"status": "success"}
    raise HTTPException(404, f"Model '{model_name}' not found")


@app.post("/v1/audio/speech")
async def tts_speech(payload: SpeechRequest):
    """生成语音 - 支持中英日多语言"""
    model = get_tts_model(payload.model)
    voice = payload.voice or LANG_DEFAULT_VOICE.get(payload.lang_code, "af_heart")
    
    async def generate():
        for result in model.generate(
            payload.input,
            voice=voice,
            speed=payload.speed,
            lang_code=payload.lang_code,
            temperature=payload.temperature,
        ):
            buf = io.BytesIO()
            sf.write(buf, result.audio, result.sample_rate, format=payload.response_format)
            buf.seek(0)
            yield buf.getvalue()
    
    return StreamingResponse(
        generate(),
        media_type=f"audio/{payload.response_format}",
        headers={"Content-Disposition": f"attachment; filename=speech.{payload.response_format}"}
    )


@app.post("/v1/audio/speech/stream")
async def tts_speech_stream(payload: SpeechRequest):
    """流式生成语音 - PCM格式实时输出"""
    model = get_tts_model(payload.model)
    voice = payload.voice or LANG_DEFAULT_VOICE.get(payload.lang_code, "af_heart")
    
    async def generate_pcm():
        import numpy as np
        # 关键：按更细粒度分割（包括逗号、分号）
        for result in model.generate(
            payload.input,
            voice=voice,
            speed=payload.speed,
            lang_code=payload.lang_code,
            temperature=payload.temperature,
            split_pattern=r'[.!?。！？,，;；:：]+',  # 更细粒度分割
        ):
            audio_int16 = (np.array(result.audio) * 32767).astype(np.int16)
            yield audio_int16.tobytes()
    
    return StreamingResponse(
        generate_pcm(),
        media_type="audio/pcm",
        headers={
            "X-Sample-Rate": "24000",
            "X-Channels": "1",
            "X-Bit-Depth": "16",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/v1/audio/transcriptions")
async def stt_transcriptions(
    file: UploadFile = File(...),
    model: str = Form(config.model.default_stt_model),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    format: str = Form("text"),
):
    """语音转文字 - 支持多种输出格式
    
    参数:
    - file: 音频文件（支持WAV/MP3/M4A/FLAC等）
    - model: STT模型
    - language: 语言（可选）
    - prompt: 提示词（最多224 tokens约900字符，包含标点可改善输出标点）
    - format: 输出格式 (text/json/srt/vtt)
    """
    data = await file.read()
    tmp_input = f"/tmp/{time.time()}.{file.filename.split('.')[-1]}"
    tmp_wav = f"/tmp/{time.time()}.wav"
    
    # 保存上传的文件
    with open(tmp_input, "wb") as f:
        f.write(data)
    
    try:
        # 尝试直接读取
        try:
            audio, sr = sf.read(tmp_input, always_2d=False)
        except:
            # 如果失败，使用ffmpeg转换
            import subprocess
            subprocess.run([
                'ffmpeg', '-i', tmp_input, 
                '-ar', '16000', '-ac', '1', 
                tmp_wav, '-y'
            ], check=True, capture_output=True)
            audio, sr = sf.read(tmp_wav, always_2d=False)
            os.remove(tmp_wav)
        
        # 保存为WAV供Whisper使用
        tmp_path = f"/tmp/{time.time()}_final.wav"
        sf.write(tmp_path, audio, sr)
        
        stt_model = get_stt_model(model)
        result = stt_model.generate(
            tmp_path, 
            language=language if language != "Detect" else None,
            initial_prompt=prompt
        )
        
        os.remove(tmp_path)
        os.remove(tmp_input)
        
        if format == "json":
            return {
                "text": result.text,
                "language": result.language if hasattr(result, 'language') else language,
                "duration": len(audio) / sr,
            }
        elif format == "srt":
            return {"text": f"1\n00:00:00,000 --> 99:99:99,999\n{result.text}\n"}
        elif format == "vtt":
            return {"text": f"WEBVTT\n\n1\n00:00:00.000 --> 99:99:99.999\n{result.text}\n"}
        else:
            return {"text": result.text}
    except Exception as e:
        # 清理临时文件
        for f in [tmp_input, tmp_wav, tmp_path]:
            if os.path.exists(f):
                os.remove(f)
        raise HTTPException(500, f"处理失败: {str(e)}")


# === Voice Clone API ===
@app.post("/v1/audio/clone")
async def voice_clone(
    file: UploadFile = File(...),
    text: str = Form(...),
    model: str = Form("mlx-community/csm-1b"),
    ref_text: str = Form("This is a reference audio sample."),
):
    """声音克隆 - 使用参考音频生成语音
    
    参数:
    - file: 参考音频文件（用于克隆声音）
    - text: 要合成的文本
    - ref_text: 参考音频的文本内容（描述参考音频说了什么）
    """
    # 保存上传的参考音频
    data = await file.read()
    tmp_ref = f"/tmp/ref_{time.time()}.wav"
    
    with open(tmp_ref, "wb") as f:
        f.write(data)
    
    try:
        # 加载模型
        clone_model = get_tts_model(model)
        
        # 加载参考音频
        from mlx_audio.tts.generate import load_audio
        ref_audio = load_audio(tmp_ref, sample_rate=clone_model.sample_rate)
        
        # 生成克隆语音
        results = list(clone_model.generate(
            text,
            ref_audio=ref_audio,
            ref_text=ref_text,
        ))
        
        if not results:
            raise HTTPException(500, "No audio generated")
        
        # 返回音频
        buf = io.BytesIO()
        sf.write(buf, results[0].audio, results[0].sample_rate, format="wav")
        buf.seek(0)
        
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=cloned.wav"}
        )
    finally:
        if os.path.exists(tmp_ref):
            os.remove(tmp_ref)


# === 异步STT任务 ===
import uuid
stt_tasks: dict = {}

@app.post("/v1/audio/transcriptions/async")
async def stt_async(
    file: UploadFile = File(...),
    model: str = Form(config.model.default_stt_model),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    """异步STT - 适合长音频"""
    task_id = str(uuid.uuid4())
    data = await file.read()
    tmp_input = f"/tmp/stt_{task_id}.{file.filename.split('.')[-1]}"
    
    with open(tmp_input, "wb") as f:
        f.write(data)
    
    stt_tasks[task_id] = {"status": "processing", "result": None, "error": None}
    
    async def process():
        try:
            tmp_wav = f"/tmp/stt_{task_id}.wav"
            try:
                audio, sr = sf.read(tmp_input, always_2d=False)
            except:
                import subprocess
                subprocess.run(['ffmpeg', '-i', tmp_input, '-ar', '16000', '-ac', '1', tmp_wav, '-y'], check=True, capture_output=True)
                audio, sr = sf.read(tmp_wav, always_2d=False)
                if os.path.exists(tmp_wav): os.remove(tmp_wav)
            
            tmp_path = f"/tmp/stt_{task_id}_final.wav"
            sf.write(tmp_path, audio, sr)
            
            stt_model = get_stt_model(model)
            result = stt_model.generate(tmp_path, language=language if language != "Detect" else None, initial_prompt=prompt)
            
            os.remove(tmp_path)
            os.remove(tmp_input)
            
            stt_tasks[task_id]["status"] = "completed"
            stt_tasks[task_id]["result"] = result.text
        except Exception as e:
            stt_tasks[task_id]["status"] = "failed"
            stt_tasks[task_id]["error"] = str(e)
    
    asyncio.create_task(process())
    return {"task_id": task_id}


@app.get("/v1/audio/transcriptions/async/{task_id}")
async def get_stt_task(task_id: str):
    """查询任务状态"""
    if task_id not in stt_tasks:
        raise HTTPException(404, "任务不存在")
    return stt_tasks[task_id]


# === Voice Blend API ===
class VoiceBlendRequest(BaseModel):
    voice1: str
    voice2: str
    weight1: float = 0.5
    weight2: float = 0.5
    lang_code: str = "a"


@app.post("/v1/audio/voice/blend")
async def blend_voices(payload: VoiceBlendRequest):
    """混合两个声音创建新声音"""
    import base64
    import numpy as np
    
    model = get_tts_model(config.model.default_tts_model)
    pipeline = model._get_pipeline(payload.lang_code)
    
    voice1_emb = pipeline.load_voice(payload.voice1)
    voice2_emb = pipeline.load_voice(payload.voice2)
    
    blended = voice1_emb * payload.weight1 + voice2_emb * payload.weight2
    blended_np = np.array(blended)
    
    return {
        "blended_voice": base64.b64encode(blended_np.tobytes()).decode(),
        "shape": list(blended_np.shape),
        "dtype": str(blended_np.dtype)
    }


# === MCP Routes ===
@app.get("/mcp/tools")
async def mcp_list_tools():
    return {
        "tools": [
            {"name": "tts", "description": "Text to Speech - 支持中英日"},
            {"name": "stt", "description": "Speech to Text"},
            {"name": "list_models", "description": "List loaded models"},
        ]
    }


@app.post("/mcp/call/{tool_name}")
async def mcp_call_tool(tool_name: str, params: dict):
    if tool_name == "tts":
        model = get_tts_model(params.get("model", config.model.default_tts_model))
        lang_code = params.get("lang_code", "a")
        voice = params.get("voice") or LANG_DEFAULT_VOICE.get(lang_code, "af_heart")
        results = list(model.generate(
            params["text"],
            voice=voice,
            speed=params.get("speed", 1.0),
            lang_code=lang_code,
        ))
        if results:
            path = config.model.output_dir / f"tts_{int(time.time())}.wav"
            sf.write(str(path), results[0].audio, results[0].sample_rate)
            return {"status": "success", "file": str(path)}
        return {"status": "error", "message": "No audio generated"}
    
    elif tool_name == "stt":
        model = get_stt_model(params.get("model", config.model.default_stt_model))
        result = model.generate(params["audio_path"])
        return {"text": result.text}
    
    elif tool_name == "list_models":
        return memory_manager.get_stats()
    
    raise HTTPException(404, f"Tool '{tool_name}' not found")


# === Static Files (UI) ===
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MLX-Audio Server")
    parser.add_argument("--host", default=config.server.host)
    parser.add_argument("--port", type=int, default=config.server.port)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    
    print(f"🚀 MLX-Audio Server: http://{args.host}:{args.port}")
    print(f"📚 API Docs: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "mlx_audio.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
