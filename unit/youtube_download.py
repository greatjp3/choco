import subprocess

def download_best_audio(youtube_url, output_path="output_audio.opus"):
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=opus]/bestaudio",
        "-o", output_path,
        "--extract-audio",
        "--audio-format", "opus",
        "--audio-quality", "0",  # best
        youtube_url
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    download_best_audio("https://www.youtube.com/watch?v=hhxWBmH-Hj4")