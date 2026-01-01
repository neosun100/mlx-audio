# MLX-Audio

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![MLX](https://img.shields.io/badge/MLX-0.25.2+-green.svg)](https://github.com/ml-explore/mlx)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0+-red.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-Required-black.svg)](https://support.apple.com/en-us/116943)

Text-to-Speech (TTS) and Speech-to-Text (STT) library based on Apple's MLX framework, optimized for Apple Silicon.

## 🚀 Two Versions Available

### 🌐 Web UI Version
- **For Developers**: Full API access, customizable, extensible
- **Installation**: Clone repo + run scripts
- **Size**: ~2GB (models downloaded separately)
- **Best for**: Development, integration, customization

### 📱 Mac App Version  
- **For End Users**: One-click installation, no setup required
- **Installation**: Download 592MB All-in-One DMG
- **Size**: 592MB (models included)
- **Best for**: Quick usage, non-technical users

## ✨ Features

### 🌊 Real-time Streaming
- **Stream-as-you-generate** - First audio <500ms
- **PCM format** - Real-time Web Audio API playback
- **Smart sentence splitting** - Split by punctuation (`,;:。！？`)
- **Performance monitoring** - Real-time TTFB, playback time, data size

### 🚀 Performance Optimized
- **Model preloading** - Load 3 models to unified memory at startup
- **Fine-grained splitting** - Split by commas, periods for faster first byte
- **Non-blocking playback** - Stream while receiving, 250ms buffer

### 📊 Performance Metrics

| Model | Load Time | Generation Speed | Memory |
|-------|-----------|------------------|--------|
| Kokoro-82M | 2.5s | 1.6s/sentence | 1.9GB |
| VoxCPM1.5 | 1.2s | 1.0s/sentence | 2.0GB |
| Whisper-Turbo | Preloaded | Real-time | - |

**Streaming Performance**:
- First byte latency: <500ms
- Playback start: <500ms
- Real-time data increment display

## 🎯 Quick Start

### Web UI Version

```bash
# Install dependencies
./scripts/setup.sh

# Start service
./scripts/start.sh

# Access
open http://localhost:8002
```

### Mac App Version

1. Download the 592MB All-in-One DMG from [Releases](https://github.com/jiasunm/mlx-audio/releases)
2. Double-click to mount the DMG
3. Drag MLX-Audio.app to Applications folder
4. Launch from Applications or Launchpad
5. No additional setup required - models included!

## 🔧 Installation & Deployment

### Web UI Version Requirements
- Python >=3.10
- MLX >=0.25.2
- FastAPI >=0.110.0
- Apple Silicon (M-series chip)

### Detailed Setup
```bash
# Clone repository
git clone https://github.com/jiasunm/mlx-audio.git
cd mlx-audio

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download models (first run)
python -m mlx_audio.download_models

# Start server
uvicorn mlx_audio.main:app --host 0.0.0.0 --port 8002
```

## ⚙️ Configuration

```python
# mlx_audio/config.py
preload_models = [
    "mlx-community/Kokoro-82M-bf16",      # TTS - Chinese/English/Japanese
    "mlx-community/VoxCPM1.5",            # TTS - Chinese/English bilingual
    "mlx-community/whisper-large-v3-turbo", # STT
]
```

## 📡 Usage Examples

### TTS - Text to Speech

**Streaming Mode** (Recommended - stream while generating)
```bash
curl -X POST http://localhost:8002/v1/audio/speech/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello world, this is a streaming output test.",
    "lang_code": "a",
    "voice": "af_bella"
  }' -o output.pcm
```

**Standard Mode** (Generate complete WAV file)
```bash
curl -X POST http://localhost:8002/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello world",
    "lang_code": "a", 
    "voice": "af_bella",
    "speed": 1.0
  }' -o output.wav
```

### STT - Speech to Text

```bash
curl -X POST http://localhost:8002/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "language=en" \
  -F "prompt=Technical terms, names, etc."
```

## 🎤 Supported Languages & Voices

### Kokoro-82M (Recommended)

**Chinese** (lang_code: "z")
- zf_xiaobei (Xiaobei ♀)
- zf_xiaoni (Xiaoni ♀)
- zf_xiaoxiao (Xiaoxiao ♀)
- zm_yunjian (Yunjian ♂)

**English** (lang_code: "a"/"b")
- af_heart, af_nova, af_bella (American ♀)
- am_adam, am_michael (American ♂)
- bf_emma, bf_isabella (British ♀)
- bm_george, bm_lewis (British ♂)

**Japanese** (lang_code: "j")
- jf_alpha, jf_gongitsune (♀)
- jm_kumo (♂)

### VoxCPM1.5 (Bilingual)
- Supports Chinese & English
- Auto language detection

## 🛠️ Tech Stack

- **Core**: Python 3.10+, Apple MLX Framework
- **Web**: FastAPI, Uvicorn, WebSockets
- **Audio**: librosa, soundfile, numpy
- **Models**: Kokoro-82M, VoxCPM1.5, Whisper-Turbo
- **Frontend**: HTML5, Web Audio API, JavaScript

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 Changelog

### v0.3.2 (Latest)
- ✨ Real-time streaming output with <500ms latency
- 🚀 Model preloading and performance optimization
- 📊 Performance monitoring and metrics
- 🌊 Smart sentence splitting for faster first byte

### v0.3.1
- 🎤 Added Whisper-Turbo STT support
- 🔧 Improved model loading efficiency
- 🐛 Fixed memory management issues

### v0.3.0
- 🎯 Initial release with Kokoro-82M and VoxCPM1.5
- 🌐 Web UI and API endpoints
- 📱 Multi-language support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=jiasunm/mlx-audio&type=Date)](https://star-history.com/#jiasunm/mlx-audio&Date)

## 📱 Follow Us

<div align="center">
  <img src="https://via.placeholder.com/200x200/000000/FFFFFF?text=QR+Code" alt="WeChat QR Code" width="200">
  <p><strong>Follow our WeChat Official Account</strong></p>
  <p>Get latest updates and tutorials</p>
</div>

---

<div align="center">
  <p>Made with ❤️ for Apple Silicon</p>
  <p>If you find this project helpful, please give it a ⭐!</p>
</div>