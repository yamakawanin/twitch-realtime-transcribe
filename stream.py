import subprocess
import numpy as np
import whisper
import sys
import time

# 使用更快的模型以降低延迟
# 使用更好的显卡提升明显
model = whisper.load_model("small")  # 你也可以换成 "medium" 或 "large" 提高准确率，但延迟会增加

# Twitch 信息
TWITCH_USER = "msdvil"
AUTH_TOKEN = "fgy19lst1f7sgyubegs8l8j8vmsjk7"
PERSISTENT = "1144830479%3A%3Abhux3uqwf9q76jyapoxtw7hsumy0in"

def get_hls_url(username):
    cookie_header = f"auth-token={AUTH_TOKEN}; persistent={PERSISTENT}"
    cmd = ["yt-dlp", f"https://www.twitch.tv/{username}", "--add-header", f"Cookie:{cookie_header}", "-g"]
    try:
        url = subprocess.check_output(cmd, text=True).strip()
        return url
    except subprocess.CalledProcessError:
        return None

def audio_to_text(audio_data):
    audio_data = whisper.pad_or_trim(audio_data)
    mel = whisper.log_mel_spectrogram(audio_data).to(model.device)
    options = whisper.DecodingOptions(language="en")  # 限制为英语
    result = whisper.decode(model, mel, options)
    return result.text.strip()

def main():
    # 获取 HLS
    while True:
        hls_url = get_hls_url(TWITCH_USER)
        if hls_url:
            print("获取到 HLS 流:", hls_url)
            break
        else:
            print("主播未开播或获取失败，等待 30 秒...")
            time.sleep(30)

    # ffmpeg 实时获取音频
    process = subprocess.Popen([
        "ffmpeg",
        "-re",                   # 实时读取
        "-i", hls_url,
        "-f", "s16le",           # PCM16 输出
        "-acodec", "pcm_s16le",
        "-ac", "1",              # 单声道
        "-ar", "16000",          # 16 kHz
        "pipe:1"
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    buffer = b''
    step = 16000 // 2  # 0.5 秒音频

    print("开始实时识别英语字幕...")

    try:
        while True:
            in_bytes = process.stdout.read(step * 2)
            if not in_bytes:
                continue

            buffer += in_bytes
            audio_data = np.frombuffer(buffer, np.int16).astype(np.float32) / 32768.0

            if len(audio_data) >= step:
                text = audio_to_text(audio_data)
                if text:
                    sys.stdout.write("\r" + text + " " * 20)  # 覆盖上一行，实现滚动输出
                    sys.stdout.flush()
                buffer = buffer[-step*2:]  # 保留上一段音频，避免断句延迟

    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        print("\n程序已退出")

if __name__ == "__main__":
    main()
