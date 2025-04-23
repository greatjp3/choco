from logger import logger

import yt_dlp
import re
import os
import requests
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
import base64
import time
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import subprocess
import socket

PLAYLIST_DIR = "/home/rpi/choco/music/"
saved_music_list = []
music_list = []
current_track_index = -1
is_playing = False
is_paused = False
play_stop_event = threading.Event()
command_queue = Queue()
command_lock = threading.Lock()
download_command_queue = Queue()
download_stop_event = threading.Event()
search_command_queue = Queue()
search_stop_event = threading.Event()
last_resume_time = None
mpv_process = None
stop_requested = False
player_thread = None

MPV_SOCKET = os.path.expanduser("~/.mpvsocket")

def wait_for_socket(timeout=3):
    for _ in range(timeout * 10):
        if os.path.exists(MPV_SOCKET):
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(MPV_SOCKET)
                    return True
            except (ConnectionRefusedError, OSError):
                pass
        time.sleep(0.1)
    return False

def send_mpv_json(command_list):
    if not wait_for_socket():
        logger.warning("MPV 소켓 연결 실패 (mpv가 실행 중인지 확인)")
        return None
    if not os.path.exists(MPV_SOCKET):
        logger.warning("MPV 소켓이 존재하지 않습니다.")
        return None
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(MPV_SOCKET)
        payload = json.dumps({"command": command_list}) + "\n"
        client.sendall(payload.encode("utf-8"))
        response = client.recv(1024).decode("utf-8")
        client.close()
        return response
    except Exception as e:
        logger.error(f"mpv 전송 오류: {e}")
        return None

def pause_resume():
    global is_paused
    send_mpv_json(["cycle", "pause"])
    is_paused = not is_paused

def stop_mpv():
    global mpv_process
    send_mpv_json(["quit"])
    mpv_process = None

def play_with_mpv(filepath):
    global mpv_process
    stop_mpv()
    if os.path.exists(MPV_SOCKET):
        os.remove(MPV_SOCKET)
    mpv_process = subprocess.Popen([
        "mpv",
        "--no-video",
        "--quiet",
        f"--input-ipc-server={MPV_SOCKET}",
        filepath
    ])

def get_playlist():
    try:
        with open(PLAYLIST_DIR + "playlist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        playlist = [(item["title"], item["url"], item["thumb_url"]) for item in data]
        return playlist
    except Exception as e:
        logger.error(f"재생 목록 로딩 오류: {e}")
        return []

def player_worker():
    global current_track_index, is_playing, is_paused
    while True:
        if stop_requested:
            # logger.info("재생 중단 요청됨. 대기 중...")
            is_playing = False
            is_paused = False
            time.sleep(1)
            continue
        if not music_list or current_track_index >= len(music_list):
            # logger.info("재생할 곡이 없습니다. 대기 중...")
            is_playing = False
            time.sleep(1)
            continue
        title, _, _ = music_list[current_track_index]
        filepath = os.path.join(PLAYLIST_DIR, title + ".opus")
        if len(music_list) == 1 and not os.path.exists(filepath):
            logger.info(f"{filepath} 다운로드 대기 (최대 60초)")
            for _ in range(60):
                if os.path.exists(filepath):
                    break
                time.sleep(1)
            else:
                logger.warning("파일 없음. 다음 곡으로 이동")
                current_track_index += 1
                continue
        logger.info(f"재생 시작: {filepath}")
        is_playing = True
        is_paused = False
        play_with_mpv(filepath)
        if mpv_process:
            mpv_process.wait()
            if mpv_process:
                current_track_index += 1
        is_playing = False
        is_paused = False

def is_playing():
    return is_playing

def is_pause():
    return is_paused

def pause(state):
    global is_paused
    is_paused = state


def update_music_list(path):
    global saved_music_list
    saved_music_list.clear()
    if not os.path.exists(path):
        logger.warning(f"경로가 존재하지 않습니다: {path}")
        return
    for file in os.listdir(path):
        if file.endswith(".opus"):
            title = os.path.splitext(file)[0]
            saved_music_list.append(title)

def download_and_tag(music_list, output_dir=PLAYLIST_DIR):
    for song in music_list:
        if download_stop_event.is_set():
            logger.info("다운로드 중단 요청 수신. 종료합니다.")
            break
        title, url, thumb_url = song
        if title in saved_music_list:
            continue
        output_base = os.path.join(output_dir, title)
        audio_path = output_base + ".opus"
        def check_stop_hook(d):
            if download_stop_event.is_set():
                raise Exception("다운로드 중단 요청 감지됨.")
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
            "progress_hooks": [check_stop_hook],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([url])
                logger.info(f"다운로드 완료: {audio_path}")
            save_thumbnail(audio_path, title, thumb_url, output_dir)
            saved_music_list.append(title)
        except Exception as e:
            logger.error(f"{title} 다운로드 중 오류 발생: {e}")
            continue

def download_worker():
    while True:
        command = download_command_queue.get()
        if command == "download":
            if not music_list:
                logger.info("📭 다운로드할 music_list가 없습니다.")
                continue
            logger.info("⬇️ 다운로드 시작...")
            download_stop_event.clear()
            download_and_tag(music_list)
            logger.info("✅ 다운로드 완료. 대기 중...")
        elif command == "stop":
            logger.info("🛑 다운로드 중단 요청 수신.")
            download_stop_event.set()

def search_worker():
    global music_list
    while True:
        text = search_command_queue.get()
        search_stop_event.clear()
        results = search_query_update_list(text)
        if results:
            music_list = results
            update_playlist(music_list)
            download_command_queue.put("download")
        else:
            logger.warning("❌ 검색 결과 없음 또는 중단됨.")

def save_thumbnail(audio_path, title, thumb_url, output_dir="/home/rpi/choco/music"):
    filename = f"{title}.jpg"
    image_path = os.path.join(output_dir, filename)
    try:
        res = requests.get(thumb_url, timeout=10)
        if res.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(res.content)
            return image_path
        else:
            logger.warning("썸네일 다운로드 실패")
    except Exception as e:
        logger.error(f"썸네일 요청 오류: {e}")
    try:
        audio = OggOpus(audio_path)
        audio["title"] = title
        if image_path:
            with open(image_path, "rb") as img_file:
                image_data = img_file.read()
            pic = Picture()
            pic.data = image_data
            pic.type = 3
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]
        audio.save()
    except Exception as e:
        logger.error(f"태깅 오류: {e}")
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def search_query_update_list(query, max_results=10):
    result = []
    search_query = f"ytsearch{max_results}:music {query}"
    ydl_opts_info = {
        "quiet": False,
        "extract_flat": True,
        "skip_download": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if "entries" in info:
            for entry in info["entries"]:
                if search_stop_event.is_set():
                    logger.info("🛑 검색 중단 요청 수신. 종료합니다.")
                    return []
                title = sanitize_filename(entry.get("title", "unknown_title"))
                url = entry.get("url", "unknown_url")
                thumbnails = entry.get("thumbnails", [])
                if not thumbnails:
                    return None
                best_thumb = thumbnails[-1]
                thumb_url = best_thumb.get("url")
                result.append((title, url, thumb_url))
        else:
            logger.warning("검색 결과가 없습니다.")
    return result

def init_youtube_agent():
    global is_playing, is_paused, music_list, current_track_index
    is_paused = False
    is_playing = False
    update_music_list(PLAYLIST_DIR)
    music_list = get_playlist()
    current_track_index = 0
    threading.Thread(target=download_worker).start()
    threading.Thread(target=search_worker).start()

def update_playlist(playlist):
    data = [
        {"title": title, "url": url, "thumb_url": thumb_url}
        for title, url, thumb_url in playlist
    ]
    try:
        with open(PLAYLIST_DIR + "playlist.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ 파일 저장 중 오류 발생: {e}")

def get_playlist():
    try:
        with open(PLAYLIST_DIR + "playlist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        playlist = [
            (item["title"], item["url"], item["thumb_url"])
            for item in data
        ]
        return playlist
    except FileNotFoundError:
        logger.warning(f"❌ 파일이 존재하지 않습니다: {PLAYLIST_DIR + 'playlist.json'}")
        return []
    except Exception as e:
        logger.error(f"❌ 파일 읽기 오류: {e}")
        return []

def youtube_search(text):
    global music_list, current_track_index
    download_stop_event.set()
    search_stop_event.set()
    search_query = f"ytsearch1:music {text}"
    ydl_opts_info = {
        "quiet": False,
        "format": "bestaudio[ext=opus]/bestaudio",
        "extract_flat": True,
        "skip_download": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if "entries" in info:
            for entry in info["entries"]:
                title = sanitize_filename(entry.get("title", "unknown_title"))
                url = entry.get("url", "unknown_url")
                thumbnails = entry.get("thumbnails", [])
                if not thumbnails:
                    return None
                best_thumb = thumbnails[-1]
                thumb_url = best_thumb.get("url")
                music_list = [(title, url, thumb_url)]
        else:
            logger.warning("검색 결과가 없습니다.")
    if not music_list:
        return "검색 결과가 없습니다."
    else:
        update_playlist(music_list)
        current_track_index = 0
        download_command_queue.put("download")
        search_command_queue.put(text)
        return True

def youtube_play():
    global is_playing, music_list, stop_requested, player_thread
    stop_requested = False
    music_list = get_playlist()
    if not music_list:
        return True, "youtube", "재생할 곡이 없습니다."
    if is_playing:
        stop_mpv()
    if not player_thread:
        logger.info(f"player_thread: {player_thread}")
        player_thread = threading.Thread(target=player_worker, daemon=True)
        player_thread.start()

    return True, "youtube", None

def youtube_stop():
    global stop_requested
    stop_requested = True
    stop_mpv()
    download_stop_event.set()
    search_stop_event.set()
    return True, "youtube", None

def youtube_pause():
    if is_playing:
        pause_resume()
        return True, "youtube", None
    return True, "youtube", "재생 중인 음악이 없습니다."


def youtube_resume():
    if is_paused:
        pause_resume()
        return True, "youtube", None
    return True, "youtube", "일시정지된 상태가 아닙니다."


def youtube_next():
    global current_track_index, stop_requested
    stop_requested = False

    if music_list:
        stop_mpv()
        current_track_index = (current_track_index + 1 ) % len(music_list)
        return True, "youtube", None
    return True, "youtube", "다음 곡이 없습니다."


def youtube_prev():
    global current_track_index, stop_requested
    stop_requested = False

    if music_list:
        stop_mpv()
        current_track_index = (current_track_index - 1) % len(music_list)
        return True, "youtube", None
    return True, "youtube", "이전 곡이 없습니다."

def youtube_action(text):
    text = text.strip().lower()
    search_match = re.search(r"(?x)^\s*(?P<query>.+?)\s*(노래|음악)?\s*(틀어\s*줘|재생\s*해\s*줘|틀어|켜\s*줘|켜줄래|틀어줄래|재생해|재생|플레이|들려\s*줘)?\s*$", text)
    play_match = re.fullmatch(r"(재생|노래\s*(재생|틀어줘|켜줘)|음악\s*(재생|틀어줘|켜줘))", text)
    stop_match = re.search(r"(꺼|정지|중지)", text)
    pause_match = re.search(r"(일시\s*정지|멈춰)", text)
    next_match = re.search(r"(다음\s*곡)", text)
    prev_match = re.search(r"(이전\s*곡)", text)
    if stop_match:
        return youtube_stop()
    elif pause_match:
        return youtube_pause()
    elif next_match:
        return youtube_next()
    elif prev_match:
        return youtube_prev()
    elif play_match:
        if is_paused and is_playing:
            logger.info("play_match: resume")
            return youtube_resume()
        else:
            logger.info("play_match: new play")
            return youtube_play()
    elif search_match:
        query = search_match.group(1).strip()
        logger.info(f"🔍 검색어 추출: {query}")
        if youtube_search(query) == True:
            logger.info("search_match")
            return youtube_play()
        else:
            return True, "youtube", "검색 결과가 없습니다."
    else:
        return False, "youtube", None

# ✅ 테스트 실행
if __name__ == "__main__":
    texts = [#"레드벨벳 노래 틀어줘",
            #"멈춰",
            "음악 재생",
            # "음악 꺼줘",
            # "음악 재생",
            # "음악 꺼줘",
            # "음악 켜줘",
            "다음 곡",
            "다음 곡",
            "이전 곡",
            "음악 꺼줘",
            "음악 틀어줘",
            "음악 꺼줘",
            ]

    for text in texts:
        print(f"input:{text}")
        print(youtube_action(text))
        time.sleep(10)

