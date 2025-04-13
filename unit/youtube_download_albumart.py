import subprocess
import re
import os
import requests
from bs4 import BeautifulSoup

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_album_art(query, output_path):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    search_url = f"https://www.google.com/search?tbm=isch&q={query}"
    response = requests.get(search_url, headers=headers)

    if response.status_code != 200:
        print("구글 이미지 검색 실패")
        return False

    soup = BeautifulSoup(response.text, "html.parser")
    img_tags = soup.find_all("img")

    for img in img_tags[1:]:  # 첫 번째는 구글 로고이므로 제외
        img_url = img.get("src")
        try:
            img_data = requests.get(img_url, headers=headers, timeout=10)
            size_kb = len(img_data.content) / 1024
            if size_kb <= 1024:  # 1MB 이하
                with open(output_path, "wb") as f:
                    f.write(img_data.content)
                print(f"앨범 아트 저장 완료: {output_path}")
                return True
        except Exception as e:
            continue

    print("유효한 앨범 아트를 찾지 못했습니다.")
    return False

def download_audio_with_album_art(youtube_url, output_dir="."):
    result = subprocess.run(
        ["yt-dlp", "--get-title", youtube_url],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print("메타데이터를 가져오는 데 실패했습니다.")
        return

    output_lines = result.stdout.strip().split("\n")
    if len(output_lines) < 2:
        print("제목 또는 가수 정보를 가져오지 못했습니다.")
        return

    title = sanitize_filename(output_lines[0])
    uploader = sanitize_filename(output_lines[1])
    filename_base = f"{uploader}_{title}"
    audio_path = os.path.join(output_dir, f"{filename_base}.opus")
    image_path = os.path.join(output_dir, f"{filename_base}.jpg")

    # 오디오 다운로드
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=opus]/bestaudio",
        "-o", audio_path,
        "--extract-audio",
        "--audio-format", "opus",
        "--audio-quality", "0",
        youtube_url
    ]
    subprocess.run(cmd)
    print(f"오디오 다운로드 완료: {audio_path}")

    # 앨범 아트 다운로드
    search_query = f"{uploader} {title} album cover"
    get_album_art(search_query, image_path)

if __name__ == "__main__":
    download_audio_with_album_art("https://www.youtube.com/watch?v=jeqdYqsrsA0")
