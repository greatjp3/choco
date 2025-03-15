import contextlib
import asyncio
from logger import logger
from common import *
from agent import *

def main_loop():
    try:
        while True:
            wake_word()
            speak_ack()
            text = recognize_audio()
            try:
                response = agent.run(text)
                speak(response)

                print(f"응답: {response}")
            except Exception as e:
                print(f"에이전트 실행 중 오류 발생: {e}")

    except ImportError as e:
        print(f"필수 모듈을 불러오는 중 오류 발생: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"메인 루프 실행 중 오류 발생: {e}")
        sys.exit(1)
   

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n사용자 종료 (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"프로그램 실행 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)


