"""MLX-Audio 资源管理器 - 懒加载+自动释放+线程安全+异步兼容"""
import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import mlx.core as mx


@dataclass
class ModelEntry:
    """模型条目"""
    model: Any
    last_access: float
    load_time: float


class MemoryManager:
    """统一资源管理器"""
    
    def __init__(self, idle_timeout: int = 300):
        self._models: Dict[str, ModelEntry] = {}
        self._lock = threading.RLock()
        self._idle_timeout = idle_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def get_model(self, name: str, load_func: Callable[[], Any]) -> Any:
        """获取模型（懒加载）"""
        with self._lock:
            if name in self._models:
                self._models[name].last_access = time.time()
                return self._models[name].model
            
            start = time.time()
            model = load_func()
            self._models[name] = ModelEntry(
                model=model,
                last_access=time.time(),
                load_time=time.time() - start
            )
            return model
    
    async def get_model_async(self, name: str, load_func: Callable[[], Any]) -> Any:
        """异步获取模型"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_model, name, load_func)
    
    def release(self, name: str) -> bool:
        """释放指定模型"""
        with self._lock:
            if name in self._models:
                del self._models[name]
                mx.clear_cache()
                return True
            return False
    
    def release_all(self):
        """释放所有模型"""
        with self._lock:
            self._models.clear()
            mx.clear_cache()
    
    def cleanup_idle(self):
        """清理空闲模型"""
        now = time.time()
        with self._lock:
            to_remove = [
                name for name, entry in self._models.items()
                if now - entry.last_access > self._idle_timeout
            ]
            for name in to_remove:
                del self._models[name]
            if to_remove:
                mx.clear_cache()
        return to_remove
    
    async def start_cleanup_loop(self, interval: int = 60):
        """启动自动清理循环"""
        self._running = True
        while self._running:
            await asyncio.sleep(interval)
            self.cleanup_idle()
    
    def stop_cleanup_loop(self):
        """停止清理循环"""
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            # 使用MLX Metal API获取实际内存
            try:
                if hasattr(mx.metal, 'get_active_memory'):
                    memory_bytes = mx.metal.get_active_memory()
                else:
                    memory_bytes = mx.metal.get_peak_memory() if hasattr(mx.metal, 'get_peak_memory') else 0
            except:
                memory_bytes = 0
            
            return {
                "loaded_models": list(self._models.keys()),
                "count": len(self._models),
                "memory_mb": memory_bytes / 1e6,
            }
    
    def list_models(self) -> list:
        """列出已加载模型"""
        with self._lock:
            return list(self._models.keys())


# 全局实例
memory_manager = MemoryManager()
