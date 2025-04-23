import yt_dlp
import re
import os
import requests
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
import base64
import time

saved_music_list = []

def update_music_list(path):
    global saved_music_list
    saved_music_list.clear()  # 기존 리스트 초기화

    if not os.path.exists(path):
        print(f"경로가 존재하지 않습니다: {path}")
        return

    for file in os.listdir(path):
        if file.endswith(".opus"):
            title = os.path.splitext(file)[0]  # 확장자 제거
            saved_music_list.append(title)

    print(f"🎵 총 {len(saved_music_list)}곡이 로딩되었습니다.")
    for idx, title in enumerate(saved_music_list, start=1):
        print(f"{idx}. {title}")

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def save_thumbnail_as_album_art(entry, artist, title, output_dir="/home/rpi/choco/music"):
    thumbnails = entry.get("thumbnails", [])
    if not thumbnails:
        print("썸네일 정보가 없습니다.")
        return None

    best_thumb = thumbnails[-1]  # 가장 고해상도일 가능성이 높음
    thumb_url = best_thumb.get("url")
    filename = f"{sanitize_filename(artist)}_{sanitize_filename(title)}.jpg"
    image_path = os.path.join(output_dir, filename)

    try:
        res = requests.get(thumb_url, timeout=10)
        if res.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(res.content)
            print(f"앨범아트 저장 완료: {image_path}")
            return image_path
        else:
            print("썸네일 다운로드 실패")
    except Exception as e:
        print("썸네일 요청 오류:", e)
    return None

def tag_album_art_to_opus(opus_path, image_path, artist, title, album):
    try:
        audio = OggOpus(opus_path)
        audio["artist"] = artist
        audio["title"] = title
        audio["album"] = album

        if image_path:
            with open(image_path, "rb") as img_file:
                image_data = img_file.read()
            pic = Picture()
            pic.data = image_data
            pic.type = 3  # front cover
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]

        audio.save()
        print("앨범아트 및 태그 저장 완료")
    except Exception as e:
        print("태깅 오류:", e)

def search_query(query, max_results=10):
    result=[]
    search_query = f"ytsearch{max_results}:music {query}"
    ydl_opts_info = {
        "quiet": True,
        "format": "bestaudio[ext=opus]/bestaudio",
        "extract_flat": False,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if "entries" in info:
            for entry in info["entries"]:
                title = sanitize_filename(entry.get("title", "unknown_title"))
                url = entry.get("url", "unknown_url")
                thumbnails = entry.get("thumbnails", [])
                if not thumbnails:
                    print("썸네일 정보가 없습니다.")
                    return None

                best_thumb = thumbnails[-1]  # 가장 고해상도일 가능성이 높음
                thumb_url = best_thumb.get("url")
                result.append((title, url, thumb_url))
        else:
            print("검색 결과가 없습니다.")

    return result

def download_and_tag(music_list, output_dir="/home/rpi/choco/music"):
    for song in music_list:
        title, url, thumb_url = song

        if title in saved_music_list:
            print(f"✅ 이미 존재함: {title}, 건너뜁니다.")
            continue
        
        output_base = os.path.join(output_dir, title)
        audio_path = output_base + ".opus"

        ydl_opts_download = {
                "quiet": False,
                "format": "bestaudio[ext=opus]/bestaudio",
                "extract_flat": False,
                "skip_download": False,
                "outtmpl": output_base,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": "0",
                }],
            }
                    
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download(url)
            print(f"🎧 다운로드 완료: {audio_path}")

        save_thumbnail(audio_path, title, thumb_url, output_dir)

def save_thumbnail(audio_path, title, thumb_url, output_dir="/home/rpi/choco/music"):
    filename = f"{title}.jpg"
    image_path = os.path.join(output_dir, filename)

    try:
        res = requests.get(thumb_url, timeout=10)
        if res.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(res.content)
            print(f"앨범아트 저장 완료: {image_path}")
            return image_path
        else:
            print("썸네일 다운로드 실패")
    except Exception as e:
        print("썸네일 요청 오류:", e)

    try:
        audio = OggOpus(opus_path)
        audio["title"] = title
 
        if image_path:
            with open(image_path, "rb") as img_file:
                image_data = img_file.read()
            pic = Picture()
            pic.data = image_data
            pic.type = 3  # front cover
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]

        audio.save()
        print("앨범아트 및 태그 저장 완료")
    except Exception as e:
        print("태깅 오류:", e)

def search_download_and_tag(query, output_dir="/home/rpi/choco/music"):
    search_query = f"ytsearch1:music {query}"

    # 1차 검색: 전체 entry 정보 추출
    ydl_opts_info = {
        "quiet": True,
        "format": "bestaudio[ext=opus]/bestaudio",
        "extract_flat": False,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        result = ydl.extract_info(search_query, download=False)
        entry = result["entries"][0]

        title = sanitize_filename(entry.get("title", "unknown_title"))
        artist = sanitize_filename(entry.get("uploader", "unknown_artist"))
        album = sanitize_filename(entry.get("album", ""))  # 없을 수도 있음

        filename_base = f"{artist}_{title}"
        output_base = os.path.join(output_dir, filename_base)
        audio_path = output_base + ".opus"  # 실제 최종 파일 경로
        image_path = save_thumbnail_as_album_art(entry, artist, title, output_dir)

    # 2차 다운로드 실행
    ydl_opts_download = {
        "quiet": False,
        "format": "bestaudio[ext=opus]/bestaudio",
        "extract_flat": False,
        "skip_download": False,
        "outtmpl": output_base,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
            "preferredquality": "0",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
        ydl.download([entry["webpage_url"]])
        print(f"🎧 다운로드 완료: {audio_path}")

    tag_album_art_to_opus(audio_path, image_path, artist, title, album)

if __name__ == "__main__":
    update_music_list("/home/rpi/choco/music")

    user_query = "레드벨벳"
    start_time = time.time()
    music_list = search_query(user_query)
    download_and_tag(music_list)
    end_time = time.time()
    print(f"\n⏱️ 총 소요 시간: {end_time - start_time:.2f}초")
