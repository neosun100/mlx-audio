#!/bin/bash
# MLX-Audio 环境配置脚本

set -e

echo "🔧 MLX-Audio Setup"

# 检查UV
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 同步依赖
echo "📦 Syncing dependencies..."
uv sync

# 验证MLX
echo "🔍 Verifying MLX..."
uv run python -c "import mlx.core as mx; print(f'MLX OK - Device: {mx.default_device()}')"

echo "✅ Setup complete!"
echo ""
echo "Run: ./scripts/start.sh"
