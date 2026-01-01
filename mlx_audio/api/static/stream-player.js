class StreamPlayer {
    constructor() {
        this.audioContext = null;
        this.source = null;
        this.chunks = [];
        this.isPlaying = false;
    }

    async initialize() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    async streamTTS(url, params) {
        await this.initialize();
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // 检查是否支持流式响应
            if (!response.body || !response.body.getReader) {
                // 回退到普通模式
                const blob = await response.blob();
                return this.playBlob(blob);
            }

            const reader = response.body.getReader();
            const chunks = [];
            let totalLength = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                chunks.push(value);
                totalLength += value.length;
                
                // 当累积足够数据时开始播放
                if (totalLength > 8192 && !this.isPlaying) {
                    this.startStreaming(chunks);
                }
            }

            // 确保所有数据都被处理
            if (!this.isPlaying) {
                this.startStreaming(chunks);
            }

        } catch (error) {
            console.error('Streaming error:', error);
            throw error;
        }
    }

    async startStreaming(chunks) {
        this.isPlaying = true;
        
        // 合并所有chunk
        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        const combined = new Uint8Array(totalLength);
        let offset = 0;
        
        for (const chunk of chunks) {
            combined.set(chunk, offset);
            offset += chunk.length;
        }

        try {
            // 解码音频数据
            const audioBuffer = await this.audioContext.decodeAudioData(combined.buffer);
            
            // 播放音频
            this.source = this.audioContext.createBufferSource();
            this.source.buffer = audioBuffer;
            this.source.connect(this.audioContext.destination);
            this.source.start();
            
            // 更新UI中的音频元素
            const audio = document.getElementById('tts-audio');
            const downloadBtn = document.getElementById('download-btn');
            const blob = new Blob([combined], { type: 'audio/wav' });
            audio.src = URL.createObjectURL(blob);
            audio.classList.remove('hidden');
            downloadBtn.classList.remove('hidden');
            
        } catch (error) {
            console.error('Audio decode error:', error);
            // 回退到普通播放
            const blob = new Blob([combined], { type: 'audio/wav' });
            this.playBlob(blob);
        }
    }

    async playBlob(blob) {
        const audio = document.getElementById('tts-audio');
        const downloadBtn = document.getElementById('download-btn');
        audio.src = URL.createObjectURL(blob);
        audio.classList.remove('hidden');
        downloadBtn.classList.remove('hidden');
        audio.play();
    }

    stop() {
        if (this.source) {
            this.source.stop();
            this.source = null;
        }
        this.isPlaying = false;
    }
}

window.StreamPlayer = StreamPlayer;