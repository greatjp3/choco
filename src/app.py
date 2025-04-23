import threading
import redis
import hashlib
import subprocess
import volume_agent
import alarm_agent
from logger import logger
from common import *
from routes import *
from pydub.playback import _play_with_simpleaudio
from weather_daemon import start_weather_daemon
from youtube_agent import init_youtube_agent, youtube_pause, youtube_resume, youtube_stop, is_playing, is_pause, pause

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
stop_event = threading.Event()
process_thread = None

def text_to_speech(text, speed=1.3):
    global tts_play_obj, is_speeching

    cleaned = clean_text(text)
    tts = gTTS(cleaned, lang='ko')

    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)
        temp_audio.seek(0)

        sound = AudioSegment.from_file(temp_audio.name, format="mp3")
        modified_sound = change_speed(sound, speed)

        with tts_lock:
            is_speeching = True
            tts_play_obj = _play_with_simpleaudio(modified_sound)

        # 재생 상태 감시하며 stop_event 체크
        while tts_play_obj.is_playing():
            if stop_event.is_set():
                tts_play_obj.stop()
                logger.info("🔇 TTS 재생 중단됨 (stop_event 감지)")
                break
            time.sleep(0.5)  # 너무 자주 체크하면 CPU 점유율이 높아집니다

        with tts_lock:
            is_speeching = False
            tts_play_obj = None

def process_agent(text):
    logger.info(f"질문: {text}")
    try:
        action, result, response = action_router(text)

        if stop_event.is_set():
            return
    except Exception as e:
        logger.error(f"process_agent 실행 중 오류 발생: {e}")

    if result == "volume":
        if is_pause():
            youtube_resume()
            pause(False)
    elif result == "youtube":
        logger.info(f"응답: {result}")
    elif action==True and response != None:
        text_to_speech(response)
        logger.info(f"응답: {response}")
        if is_pause():
            youtube_stop()
            pause(False)
    
def main():
    global process_thread
    already_wakeup = False

    start_weather_daemon()
    init_youtube_agent()

    volume_agent.v.volume_init()
    file_name = "../res/startup.wav"
    if os.path.exists(file_name):
        try:
            subprocess.run(["aplay", file_name], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"🔈 aplay 실패: {e}")
    else:
        logger.warning(f"🔇 오디오 파일이 존재하지 않음: {file_name}")

    try:
        test()      # 부팅 후 첫번째 호출 동작 안됨. 임시 대응
    except Exception as e:
        logger.error("exception11")

    while True:
        if already_wakeup == False:
            wake_word()
            if(alarm_agent.is_any_alarm_running()):
                alarm_agent.stop_alarm()
            
            if is_playing():
                youtube_pause()
                pause(True)

            if is_speech():
                stop_speech()
                
        speak_ack()
        print("ack!")

        if process_thread and process_thread.is_alive():
            stop_event.set()
            process_thread.join()

        already_wakeup = False;           
        text = recognize_audio()

        if text == None:
            if is_pause():
                youtube_resume()
                pause(False)
            continue

        if "computer" in text or "컴퓨터" in text:
            already_wakeup = True
            continue

        stop_event.clear()
        process_thread = threading.Thread(target=process_agent, args=(text,))
        process_thread.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n사용자 종료 (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"프로그램 실행 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)
