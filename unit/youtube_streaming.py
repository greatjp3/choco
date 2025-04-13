import subprocess
import yt_dlp
import re
import time
from pydub import AudioSegment
from pydub.playback import play
import requests

def get_audio_url(video_url):
    """Extract the best audio URL quickly using yt-dlp with optimizations"""
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        "--get-url",
        "--no-playlist",
        "--extractor-args", "youtube:skip=hls,dash",
        "--force-ipv4",
        video_url
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        audio_url, _ = process.communicate()  # 결과를 즉시 가져옴
        return audio_url.strip()
    
    except Exception as e:
        print(f"❌ Error fetching audio URL: {e}")
        return None

def play_youtube_audio(video_url):
    print(f"Buffering: {video_url}")
    audio_url = get_audio_url(video_url)
    if not audio_url:
        print("Failed to extract audio URL")
        return

    print(f"Playing: {video_url}")
    subprocess.run(["mpv", "--no-video", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  

def get_audio_duration(video_url):
    """Get the total duration of the YouTube audio in seconds."""
    try:
        command = [
            "yt-dlp",
            "--print", "duration",
            "--no-playlist",
            video_url
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        duration = result.stdout.strip()
        return int(float(duration)) if duration else None
    except Exception as e:
        print(f"❌ Error fetching audio duration: {e}")
        return None

def format_time(seconds):
    """Convert seconds into HH:MM:SS format."""
    if seconds is None:
        return "Unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"

def search_youtube(query, max_results=10):
    """Search YouTube and return a list of video titles and URLs."""
    search_query = f"ytsearch{max_results}:music {query}"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,  # Only get URLs, no downloads
    }

    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if "entries" in info:
            for entry in info["entries"]:
                if entry:
                    results.append((entry["title"], entry["url"]))  # (title, URL)

    return results

def volume_control(vol, card=0, control="Headphone"):
    if not (0 <= vol <= 100):
        print("⚠️ Volume must be between 0 and 100.")
        return

    try:
        # ALSA는 -10239 ~ 400 dB의 볼륨 범위를 사용하므로 변환 필요
        min_db, max_db = -10239, 400
        volume_db = int(min_db + (vol / 100) * (max_db - min_db))

        # 볼륨 조절 명령 실행
        subprocess.run(["amixer", "-c", str(card), "sset", control, f"{vol}%"], check=True)
        print(f"🔊 Volume set to {vol}% ({volume_db} dB) using '{control}' on card {card}")

    except subprocess.CalledProcessError:
        print(f"❌ Failed to change volume for {control} on card {card}.")

# 🔥 Raspberry Pi의 `bcm2835 Headphones` 볼륨 조절
volume_control(70, card=0, control="Headphone")  # 볼륨 50% 설정

# Example usage:
query = "color of the night"  # Search term
results = search_youtube(query)

print("\n🎵 YouTube Search Results:")
for i, (title, url) in enumerate(results, 1):
    print(f"{i}. {title} - {url}")

# Example: Play YouTube Audio
play_youtube_audio(results[0][1])

