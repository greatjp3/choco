import asyncio
from logger import logger
from common import *
from agent import *

process_task = None

async def process_agent(text, agent):
    # global process_task
    print("invoke")
    logger.info(f"🔄 process_agent() 실행: {text}")

    try:
        logger.info(f"🛠 agent.ainvoke() 호출 전: {text}")
        response = await agent.ainvoke(text)
        logger.info(f"응답: {response}")

        # process_task3 = asyncio.create_task(speak(response))
        # await process_task3

    except ImportError as e:
        logger.error(f"필수 모듈을 불러오는 중 오류 발생: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"메인 루프 실행 중 오류 발생: {e}")
        sys.exit(1)
    
async def main():
    global input_event
    global process_task

    input_event = asyncio.Queue()  # 비동기 입력 이벤트 관리
    agent = await initialize_async_agent()

    while True:
        await wake_word()
        await speak_ack()
        print("ack!")

        text = await recognize_audio()
        if text is None or "computer" in text.lower() or "jarvis" in text.lower():
            continue
        print(f"🗣 Recognized: {text}")

        if process_task is not None and not process_task.done():
            process_task.cancel()
            try:
                await process_task  # 기존 작업 종료 대기
            except asyncio.CancelledError:
                logger.info("이전 process 강제 취소 완료")

            await asyncio.sleep(0.1)

        try:
            process_task = asyncio.create_task(process_agent(text, agent))
            print("process triggered")
            # await process_task
           
        except Exception as e:
            logger.error(f"🚨 process_task 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    try:
        print("start")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("\n사용자 종료 (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"프로그램 실행 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)
