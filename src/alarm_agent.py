import time
import threading
import datetime

# 실행 중인 알람 저장
active_alarms = {}
alarm_count = 0  # 알람 ID를 숫자로 관리

def alarm_thread(alarm_id: str, alarm_time: str):
    """알람 실행 스레드"""
    alarm_datetime = datetime.datetime.strptime(alarm_time, "%H:%M")
    while datetime.datetime.now().time() < alarm_datetime.time():
        time.sleep(1)  # 1초마다 현재 시간 확인

    if alarm_id in active_alarms:
        print(f"🔔 {alarm_id} 알람! 설정된 시간({alarm_time})이 되었습니다!")
        del active_alarms[alarm_id]

def set_alarm(alarm_time: str) -> str:
    """알람 설정 및 실행"""
    global alarm_count
    try:
        # 입력된 시간을 확인하고 변환
        datetime.datetime.strptime(alarm_time, "%H:%M")
    except ValueError:
        return "올바른 시간 형식으로 입력하세요. 예: '07:30', '15:00'"

    alarm_count += 1
    alarm_id = f"{alarm_count}번 알람"  # ID를 "1번 알람", "2번 알람" 형식으로 변경
    alarm_thread_instance = threading.Thread(target=alarm_thread, args=(alarm_id, alarm_time))
    alarm_thread_instance.start()

    active_alarms[alarm_id] = (alarm_thread_instance, alarm_time)  # 알람 저장

    return f"🔔 {alarm_id} 설정: {alarm_time}에 알림!"

def cancel_alarm(alarm_id: str) -> str:
    """설정된 알람 취소"""
    if alarm_id in active_alarms:
        del active_alarms[alarm_id]
        return f"⏹ {alarm_id}가 취소되었습니다."
    return f"⚠️ '{alarm_id}' 알람을 찾을 수 없습니다."

def list_alarms() -> str:
    """현재 실행 중인 알람 목록 반환"""
    if not active_alarms:
        return "🔍 현재 설정된 알람이 없습니다."

    alarm_list = "\n".join([f"🔔 {alarm_id} - 알람 시간: {alarm_time}" for alarm_id, (_, alarm_time) in active_alarms.items()])
    return f"📋 현재 설정된 알람 목록:\n{alarm_list}"
