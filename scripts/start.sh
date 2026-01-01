#!/bin/bash
# MLX-Audio 启动脚本

set -e

PORT=${MLX_AUDIO_PORT:-8000}
HOST=${MLX_AUDIO_HOST:-0.0.0.0}

# 检查端口占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 自动选择可用端口
while check_port $PORT; do
    echo "⚠️  Port $PORT in use, trying $((PORT+1))..."
    PORT=$((PORT+1))
done

echo "🚀 MLX-Audio Server"
echo "   URL: http://$HOST:$PORT"
echo "   Docs: http://$HOST:$PORT/docs"
echo ""

# 启动服务
exec uv run uvicorn mlx_audio.api.app:app --host $HOST --port $PORT
