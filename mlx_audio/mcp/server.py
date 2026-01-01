"""MLX-Audio MCP服务器 - 支持HTTP模式和stdio模式"""
import sys
import time
from pathlib import Path
from typing import Optional

import soundfile as sf
from fastmcp import FastMCP

from mlx_audio.config import config
from mlx_audio.models.memory_manager import memory_manager
from mlx_audio.utils import load_model

mcp = FastMCP("mlx-audio", description="MLX-Audio TTS/STT on Apple Silicon")


def _get_model(name: str):
    return memory_manager.get_model(name, lambda: load_model(name))


@mcp.tool()
async def tts(
    text: str,
    model: str = config.model.default_tts_model,
    voice: str = config.tts.voice,
    speed: float = config.tts.speed,
    lang_code: str = config.tts.lang_code,
) -> str:
    """文本转语音 - 生成音频文件并返回路径"""
    tts_model = _get_model(model)
    results = list(tts_model.generate(text, voice=voice, speed=speed, lang_code=lang_code))
    
    if not results:
        return "Error: No audio generated"
    
    path = config.model.output_dir / f"tts_{int(time.time())}.wav"
    sf.write(str(path), results[0].audio, results[0].sample_rate)
    return f"Audio saved: {path}"


@mcp.tool()
async def stt(
    audio_path: str,
    model: str = config.model.default_stt_model,
    language: Optional[str] = None,
) -> str:
    """语音转文字 - 转录音频文件"""
    if not Path(audio_path).exists():
        return f"Error: File not found: {audio_path}"
    
    stt_model = _get_model(model)
    result = stt_model.generate(audio_path, language=language)
    return result.text


@mcp.tool()
async def list_models() -> str:
    """列出已加载的模型"""
    stats = memory_manager.get_stats()
    return f"Loaded: {stats['loaded_models']}, Count: {stats['count']}"


@mcp.tool()
async def unload_model(model_name: str) -> str:
    """卸载指定模型释放内存"""
    if memory_manager.release(model_name):
        return f"Model {model_name} unloaded"
    return f"Model {model_name} not found"


def main():
    """入口点 - 自动检测模式"""
    if "--stdio" in sys.argv or not sys.stdin.isatty():
        # stdio模式 - Claude Desktop兼容
        mcp.run()
    else:
        # 提示使用HTTP模式
        print("MCP Server - stdio mode")
        print("Usage: mlx_audio.mcp --stdio")
        print("Or integrate with FastAPI: http://localhost:8000/mcp/*")
        mcp.run()


if __name__ == "__main__":
    main()
