"""MLX-Audio 统一配置管理"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 2
    reload: bool = False
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            host=os.getenv("MLX_AUDIO_HOST", "0.0.0.0"),
            port=int(os.getenv("MLX_AUDIO_PORT", "8000")),
            workers=int(os.getenv("MLX_AUDIO_WORKERS", "2")),
        )


@dataclass
class ModelConfig:
    """模型配置"""
    default_tts_model: str = "mlx-community/Kokoro-82M-bf16"
    default_stt_model: str = "mlx-community/whisper-large-v3-turbo"
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "mlx_audio")
    output_dir: Path = field(default_factory=lambda: Path.home() / ".mlx_audio" / "outputs")
    idle_timeout: int = 300
    preload_models: list = field(default_factory=lambda: [
        "mlx-community/Kokoro-82M-bf16",
        "mlx-community/whisper-large-v3-turbo",
    ])
    verified_tts_models: list = field(default_factory=lambda: [
        "mlx-community/Kokoro-82M-bf16",
    ])
    
    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class TTSConfig:
    """TTS默认参数"""
    voice: str = "af_heart"
    speed: float = 1.0
    lang_code: str = "a"
    temperature: float = 0.7
    sample_rate: int = 24000


@dataclass
class STTConfig:
    """STT默认参数"""
    language: Optional[str] = None
    sample_rate: int = 16000


@dataclass
class Config:
    """全局配置"""
    server: ServerConfig = field(default_factory=ServerConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    
    @classmethod
    def load(cls) -> "Config":
        return cls(server=ServerConfig.from_env())


# 全局配置实例
config = Config.load()
