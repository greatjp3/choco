import threading
from logger import logger
from common import *
import redis
import hashlib
from routes import *
import subprocess
import volume_agent

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
stop_event = threading.Event()
process_thread = None

def process_agent(text):
    print(f"질문: {text}")
    try:
        response = action_router(text)
        if stop_event.is_set():
            return
    except Exception as e:
        logger.error(f"process_agent 실행 중 오류 발생: {e}")

    if response :
        text_to_speech(response)
        print(f"응답: {response}")
    
def main():
    global process_thread
    already_wakeup = False

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
        test()
    except Exception as e:
        print("exception11")

    while True:
        if already_wakeup == False:
            wake_word()

        speak_ack()
        print("ack!")

        if process_thread and process_thread.is_alive():
            print("stop!!")
            stop_event.set()
            process_thread.join()
            print("stop!!")

        already_wakeup = False;           
        text = recognize_audio()

        if text == None:
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
