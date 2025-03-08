from logger import logger
import time
import re
import threading

# 실행 중인 타이머 저장
active_timers = {}
timer_count = 0  # 타이머 ID를 숫자로 관리

def parse_duration(duration: str) -> int:
    """'1h 30m 10s' 같은 복합 시간 형식을 초 단위로 변환"""
    try:
        pattern = r'(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?'
        match = re.match(pattern, duration.strip())

        if not match:
            raise ValueError("올바른 형식으로 시간을 입력하세요. 예: '10s', '5m', '1h 30m 10s'")

        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0

        total_seconds = hours * 3600 + minutes * 60 + seconds

        if total_seconds <= 0:
            raise ValueError("시간은 0초보다 커야 합니다.")

        return total_seconds

    except ValueError as e:
        logger.write(f"⚠️ 타이머 설정 오류 (ValueError): {duration} | {e}\n")
        return -1

    except Exception as e:
        logger.write(f"⛔ 예상치 못한 오류 발생 (parse_duration): {duration} | {e}\n")
        return -1

def timer_thread(timer_id: str, total_seconds: int):
    """타이머 실행 스레드"""
    try:
        time.sleep(total_seconds)
        if timer_id in active_timers:
            print(f"⏰ {timer_id} 종료! {total_seconds}초가 지났습니다.")
            logger.write(f"✅ {timer_id} 종료: {total_seconds}초 경과\n")
            del active_timers[timer_id]
    except Exception as e:
        logger.write(f"⛔ 타이머 실행 중 오류 발생 ({timer_id}): {e}\n")
        print(f"⛔ 타이머 실행 중 오류 발생: {e}")

def start_timer(duration: str) -> str:
    """타이머 설정 및 실행"""
    global timer_count
    total_seconds = parse_duration(duration)

    if total_seconds <= 0:
        return "올바른 형식으로 시간을 입력하세요. 예: '10s', '5m', '1h 30m 10s'"

    try:
        timer_count += 1
        timer_id = f"{timer_count}번 타이머"
        timer_thread_instance = threading.Thread(target=timer_thread, args=(timer_id, total_seconds))
        timer_thread_instance.start()

        active_timers[timer_id] = (timer_thread_instance, total_seconds)
        logger.write(f"✅ {timer_id} 시작: {duration} 후 알림!\n")
        return f"⏳ {timer_id} 시작: {duration} 후 알림!"

    except threading.ThreadError as e:
        logger.write(f"⛔ 타이머 스레드 시작 실패: {e}\n")
        return "타이머를 설정하는 중 오류가 발생했습니다."

def cancel_timer(timer_id: str) -> str:
    """설정된 타이머 취소"""
    try:
        if timer_id in active_timers:
            del active_timers[timer_id]
            logger.write(f"⏹ {timer_id} 취소됨\n")
            return f"⏹ {timer_id}가 취소되었습니다."
        logger.write(f"⚠️ 타이머 취소 실패: {timer_id}가 존재하지 않음\n")
        return f"⚠️ '{timer_id}' 타이머를 찾을 수 없습니다."
    except KeyError as e:
        logger.write(f"⛔ 타이머 취소 중 오류 발생 ({timer_id}): {e}\n")
        return "타이머 취소 중 오류가 발생했습니다."

def list_timers() -> str:
    """현재 실행 중인 타이머 목록 반환"""
    try:
        if not active_timers:
            logger.write("🔍 현재 실행 중인 타이머 없음\n")
            return "🔍 현재 실행 중인 타이머가 없습니다."

        timer_list = "\n".join([f"⏳ {timer_id} - 남은 시간: {duration}초" for timer_id, (_, duration) in active_timers.items()])
        logger.write(f"📋 현재 실행 중인 타이머 목록 요청\n")
        return f"📋 현재 실행 중인 타이머 목록:\n{timer_list}"

    except Exception as e:
        logger.write(f"⛔ 타이머 목록 조회 중 오류 발생: {e}\n")
        return "타이머 목록을 불러오는 중 오류가 발생했습니다."
