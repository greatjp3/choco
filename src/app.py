import threading
from logger import logger
from common import *
from agent import *
import redis
import hashlib

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
stop_event = threading.Event()
process_thread = None

def process_agent(text):
    print(f"질문: {text}")
    try:
        request_hash = hashlib.sha256(text.encode()).hexdigest()
        response = redis_client.get(request_hash)
        if not response:
            response = agent.invoke(text)            
            redis_client.setex(request_hash, 3600*2, json.dumps(response))
            print(f"llm")
        else:
            json.loads(response)
            print(f"cached")
        if stop_event.is_set():
            return
    except Exception as e:
        logger.error(f"process_agent 실행 중 오류 발생: {e}")
    response = "날씨가 좋아요."
    if response :
        text_to_speech(response)
        print(f"응답: {response}")
    
def main():
    global process_thread
    already_wakeup = False

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
