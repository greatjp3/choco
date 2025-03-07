import time
import re
import threading

# 실행 중인 타이머 저장
active_timers = {}
timer_count = 0  # 타이머 ID를 숫자로 관리

def parse_duration(duration: str) -> int:
    """'1h 30m 10s' 같은 복합 시간 형식을 초 단위로 변환"""
    pattern = r'(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?'
    match = re.match(pattern, duration.strip())

    if not match:
        return -1

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    return hours * 3600 + minutes * 60 + seconds

def timer_thread(timer_id: str, total_seconds: int):
    """타이머 실행 스레드"""
    time.sleep(total_seconds)
    if timer_id in active_timers:
        print(f"⏰ {timer_id} 종료! {total_seconds}초가 지났습니다.")
        del active_timers[timer_id]

def start_timer(duration: str) -> str:
    """타이머 설정 및 실행"""
    global timer_count
    total_seconds = parse_duration(duration)

    if total_seconds <= 0:
        return "올바른 형식으로 시간을 입력하세요. 예: '10s', '5m', '1h 30m 10s'"

    timer_count += 1
    timer_id = f"{timer_count}번 타이머"  # ID를 "1번 타이머", "2번 타이머" 형식으로 변경
    timer_thread_instance = threading.Thread(target=timer_thread, args=(timer_id, total_seconds))
    timer_thread_instance.start()

    active_timers[timer_id] = (timer_thread_instance, total_seconds)  # 타이머 저장

    return f"⏳ {timer_id} 시작: {duration} 후 알림!"

def cancel_timer(timer_id: str) -> str:
    """설정된 타이머 취소"""
    if timer_id in active_timers:
        del active_timers[timer_id]
        return f"⏹ {timer_id}가 취소되었습니다."
    return f"⚠️ '{timer_id}' 타이머를 찾을 수 없습니다."

def list_timers() -> str:
    """현재 실행 중인 타이머 목록 반환"""
    if not active_timers:
        return "🔍 현재 실행 중인 타이머가 없습니다."

    timer_list = "\n".join([f"⏳ {timer_id} - 남은 시간: {duration}초" for timer_id, (_, duration) in active_timers.items()])
    return f"📋 현재 실행 중인 타이머 목록:\n{timer_list}"
