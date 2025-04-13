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
import pygame
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

PLAYLIST_DIR = "/home/rpi/choco/music/"
saved_music_list = []
music_list = []  # 플레이리스트
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
last_resume_time = None  # 최근 resume 요청 시각

def is_playing():
    return is_playing

def is_pause():
    return is_paused

def playing(play):
    global is_playing
    is_playing = play 

def paused(pause):
    global is_paused
    is_paused = pause

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

    print(f"🎵 총 {len(saved_music_list)}곡이 검색되었습니다.")
    for idx, title in enumerate(saved_music_list, start=1):
        print(f"{idx}. {title}")

def download_and_tag(music_list, output_dir=PLAYLIST_DIR):
    for song in music_list:
        if download_stop_event.is_set():
            print("🛑 다운로드 중단 요청 수신. 종료합니다.")
            break
        
        title, url, thumb_url = song

        if title in saved_music_list:
            print(f"✅ 이미 존재함: {title}, 건너뜁니다.")
            continue
        
        output_base = os.path.join(output_dir, title)
        audio_path = output_base + ".opus"

        def check_stop_hook(d):
            if download_stop_event.is_set():
                raise Exception("🛑 다운로드 중단 요청 감지됨.")
            
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
                print(f"🎧 다운로드 완료: {audio_path}")
            save_thumbnail(audio_path, title, thumb_url, output_dir)
            saved_music_list.append(title)
        except Exception as e:
            print(f"❌ {title} 다운로드 중 오류 발생: {e}")
            continue  # 다음 곡으로 진행

def download_worker():
    while True:
        command = download_command_queue.get()  # 블로킹 대기
        if command == "download":
            if not music_list:
                print("📭 다운로드할 music_list가 없습니다.")
                continue
            print("⬇️ 다운로드 시작...")
            download_stop_event.clear()
            download_and_tag(music_list)
            print("✅ 다운로드 완료. 대기 중...")
        elif command == "stop":
            print("🛑 다운로드 중단 요청 수신.")
            download_stop_event.set()

def search_worker():
    global music_list

    while True:
        text = search_command_queue.get()  # 블로킹 대기
        search_stop_event.clear()
        print(f"search_worker:{text}")
        results = search_query_update_list(text)
        if results:
            music_list = results
            download_command_queue.put("download")
            print(f"🔎 {len(results)}개 결과")
        else:
            print("❌ 검색 결과 없음 또는 중단됨.")

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

        
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def search_query_update_list(query, max_results=10):
    result=[]
    search_query = f"ytsearch{max_results}:music {query}"
    ydl_opts_info = {
        "quiet": False,
        # "format": "bestaudio[ext=opus]/bestaudio",
        "extract_flat": True,
        "skip_download": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if "entries" in info:
            for entry in info["entries"]:
                if search_stop_event.is_set():
                    print("🛑 검색 중단 요청 수신. 종료합니다.")
                    return []
                
                title = sanitize_filename(entry.get("title", "unknown_title"))
                url = entry.get("url", "unknown_url")
                thumbnails = entry.get("thumbnails", [])
                if not thumbnails:
                    # print("썸네일 정보가 없습니다.")
                    return None

                best_thumb = thumbnails[-1]  # 가장 고해상도일 가능성이 높음
                thumb_url = best_thumb.get("url")
                result.append((title, url, thumb_url))
        else:
            print("검색 결과가 없습니다.")

    return result

def init_youtube_agent():
    global is_playing, is_paused   
    is_paused = False
    is_playing = False
    update_music_list(PLAYLIST_DIR)
    threading.Thread(target=download_worker).start()
    threading.Thread(target=player_worker).start()
    threading.Thread(target=search_worker).start()

def play_current():
    global is_playing, is_paused, current_track_index, last_resume_time

    while True:
        if not (0 <= current_track_index < len(music_list)):
            print("📍 재생할 곡이 없습니다.")
            is_playing = False
            return

        title, _, _ = music_list[current_track_index]
        filename = os.path.join(PLAYLIST_DIR, title + ".opus")

        if not os.path.exists(filename):
            print(f"❌ 파일이 존재하지 않습니다: {filename}")
            
            if len(music_list) == 1:
                print("⏳ 다운로드 대기: 최대 60초")
                for i in range(60):
                    if os.path.exists(filename):
                        print(f"✅ 파일 다운로드 완료됨: {filename}")
                        break
                    time.sleep(1)
                else:
                    print("⛔ 1분 대기 후에도 파일이 존재하지 않아 종료합니다.")
                    return
            else:
                current_track_index += 1
                continue

        graceful_finish = False

        try:
            play_stop_event.clear()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            is_playing = True
            is_paused = False
            print(f"🎵 재생 시작: {filename}")

            while True:
                if play_stop_event.is_set():
                    pygame.mixer.music.stop()
                    print("⏹️ 재생 중지")
                    return

                if not pygame.mixer.music.get_busy():
                    if is_paused:
                        time.sleep(0.1)
                        continue
                    elif last_resume_time and time.time() - last_resume_time < 1.0:
                        # ✅ resume 후 최대 1초까지 기다려줌
                        time.sleep(0.1)
                        continue
                    else:
                        graceful_finish = True
                        break

        except Exception as e:
            print(f"❌ 재생 중 오류 발생: {e}")

        finally:
            if graceful_finish or play_stop_event.is_set():
                is_playing = False
                is_paused = False

        current_track_index += 1


def start_play_thread():
    if not is_playing:
        threading.Thread(target=play_current, daemon=True).start()

def player_worker():
    global current_track_index, is_paused
    print("🎶 player_worker 시작")
    pygame.mixer.init()

    while True:
        cmd = command_queue.get()  # blocking
        print(f"cmd: {cmd}")

        if cmd == "stop":
            if is_playing:
                print("cmd=stop")
                play_stop_event.set()
                print("⏹️ 재생 중지")

        elif cmd == "pause":
            if is_playing and not is_paused:
                print("cmd=pause")
                pygame.mixer.music.pause()
                is_paused = True
                print("⏸️ 일시정지")

        elif cmd == "resume":
            global last_resume_time
            if is_playing and is_paused:
                print("cmd=resume")
                pygame.mixer.music.unpause()
                last_resume_time = time.time()  # ✅ resume 시각 저장
                is_paused = False
                print("▶️ 다시 재생")

        elif cmd == "next":
            if len(music_list) > 0:
                play_stop_event.set()
                current_track_index = (current_track_index + 1) % len(music_list)                

                wait_count = 0
                while is_playing and wait_count < 100:  # 최대 10초 대기
                    time.sleep(0.1)
                    wait_count += 1

                start_play_thread()
        
        elif cmd == "prev":
            if len(music_list) > 0:
                play_stop_event.set()
                current_track_index = (current_track_index - 1) % len(music_list)                

                wait_count = 0
                while is_playing and wait_count < 100:  # 최대 10초 대기
                    time.sleep(0.1)
                    wait_count += 1

                start_play_thread()

        elif cmd == "start":
            print("cmd=start")
            start_play_thread()

        elif cmd == "list":
            print("📄 재생 목록:")
            for idx, track in enumerate(music_list):
                now = "▶️" if idx == current_track_index and is_playing else "  "
                print(f"{now} {idx + 1}. {track[0]}")

def add_command(cmd):
    with command_lock:
        command_queue.put(cmd)
        print(f"📥 명령 추가됨: {cmd}")

def update_playlist(playlist):
    data = [
        {"title": title, "url": url, "thumb_url": thumb_url}
        for title, url, thumb_url in playlist
    ]

    try:
        with open(PLAYLIST_DIR+"playlist.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")

def get_playlist():
    try:
        with open(PLAYLIST_DIR, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 리스트[dict] → 리스트[tuple] 변환
        playlist = [
            (item["title"], item["url"], item["thumb_url"])
            for item in data
        ]
        print(playlist)
        return playlist
    except FileNotFoundError:
        print(f"❌ 파일이 존재하지 않습니다: {PLAYLIST_DIR}")
        return []
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return []
  
def youtube_search(text):
    global music_list, current_track_index

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
                    # print("썸네일 정보가 없습니다.")
                    return None

                best_thumb = thumbnails[-1]  # 가장 고해상도일 가능성이 높음
                thumb_url = best_thumb.get("url")
                music_list=[]
                music_list.append((title, url, thumb_url))
        else:
            print("검색 결과가 없습니다.")

    if not music_list:
        return "검색 결과가 없습니다."
    else:
        update_playlist(music_list)
        current_track_index = 0
        download_command_queue.put("download")
        search_command_queue.put(text)

        return True

play_thread = None

def youtube_wait():
    title, _, _ = music_list[current_track_index]
    filename = os.path.join(PLAYLIST_DIR, title + ".opus")
    if os.path.exists(filename):
        return True
    else:
        return False

def youtube_play():
    if not is_playing and music_list:
        add_command("start")
    return None

def youtube_stop():
    add_command("stop")
    return None

def youtube_pause():
    add_command("pause")
    return None

def youtube_next():
    print("📢 youtube_next() 호출됨")  # 로그 추가
    add_command("next")
    return None

def youtube_prev():
    add_command("prev")
    return None

def youtube_resume():
    add_command("resume")
    return None

def youtube_action(text):
    # 공백 제거 및 소문자 변환 (전처리)
    text = text.strip().lower()

    # 🔍 검색 + 재생 (예: "xxx 노래 틀어줘", "xxx 음악 켜줘")
    search_match = re.search(r"^(.+?)\s*(노래|음악)\s*(재생|틀어줘|켜줘)", text)

    # ▶️ 단순 재생 요청 (예: "재생", "노래 틀어줘", "음악 켜줘")
    play_match = re.search(r"(재생|노래\s*(재생|틀어줘|켜줘)|음악\s*(재생|틀어줘|켜줘))", text)

    # ⏹️ 중지
    stop_match = re.search(r"(꺼줘|정지|중지)", text)

    # ⏸️ 일시정지
    pause_match = re.search(r"(일시\s*정지|멈춰)", text)

    # ⏭️ 다음 곡
    next_match = re.search(r"(다음\s*곡)", text)

    # ⏮️ 이전 곡
    prev_match = re.search(r"(이전\s*곡)", text)

    # 🎯 우선순위 처리
    if search_match:
        query = search_match.group(1).strip()
        print(f"🔍 검색어 추출: {query}")
        if youtube_search(query) == True:
            print("search_match")
            return youtube_play()
        else:
            return "검색 결과가 없습니다."

    elif play_match:
        print("play_match")
        if is_paused and is_playing:
            return youtube_resume()  # 🔁 일시정지 상태면 resume
        else:
            return youtube_play()    # ▶️ 일반 재생

    elif stop_match:
        return youtube_stop()

    elif pause_match:
        return youtube_pause()

    elif next_match:
        return youtube_next()

    elif prev_match:
        return youtube_prev()

    else:
        return "아빠 도와줘요"


# ✅ 테스트 실행
if __name__ == "__main__":
    texts = ["레드벨벳 노래 틀어줘",
            "멈춰",
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
    init_youtube_agent()

    for text in texts:
        print(f"input:{text}")
        print(youtube_action(text))
        time.sleep(20)

