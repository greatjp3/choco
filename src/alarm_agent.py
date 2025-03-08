from logger import logger
import time
import threading
import datetime

# 실행 중인 알람 저장
active_alarms = {}
alarm_count = 0  # 알람 ID를 숫자로 관리

def alarm_thread(alarm_id: str, alarm_time: str):
    """알람 실행 스레드"""
    try:
        alarm_datetime = datetime.datetime.strptime(alarm_time, "%H:%M")
        while datetime.datetime.now().time() < alarm_datetime.time():
            time.sleep(1)  # 1초마다 현재 시간 확인

        if alarm_id in active_alarms:
            print(f"🔔 {alarm_id} 알람! 설정된 시간({alarm_time})이 되었습니다!")
            del active_alarms[alarm_id]
    except Exception as e:
        logger.write(f"⛔ 알람 실행 중 오류 발생 ({alarm_id}): {e}\n")
        print(f"⛔ 알람 실행 중 오류 발생: {e}")

def set_alarm(alarm_time: str) -> str:
    """알람 설정 및 실행"""
    global alarm_count
    try:
        # 입력된 시간을 확인하고 변환
        datetime.datetime.strptime(alarm_time, "%H:%M")
    except ValueError:
        logger.write(f"⚠️ 잘못된 시간 형식 입력: {alarm_time}\n")
        return "올바른 시간 형식으로 입력하세요. 예: '07:30', '15:00'"

    try:
        alarm_count += 1
        alarm_id = f"{alarm_count}번 알람"  # ID를 "1번 알람", "2번 알람" 형식으로 변경
        alarm_thread_instance = threading.Thread(target=alarm_thread, args=(alarm_id, alarm_time))
        alarm_thread_instance.start()

        active_alarms[alarm_id] = (alarm_thread_instance, alarm_time)  # 알람 저장
        logger.write(f"✅ {alarm_id} 설정: {alarm_time}에 알림!\n")
        return f"🔔 {alarm_id} 설정: {alarm_time}에 알림!"
    except threading.ThreadError as e:
        logger.write(f"⛔ 알람 스레드 시작 실패: {e}\n")
        return "알람을 설정하는 중 오류가 발생했습니다."

def cancel_alarm(alarm_id: str) -> str:
    """설정된 알람 취소"""
    try:
        if alarm_id in active_alarms:
            del active_alarms[alarm_id]
            logger.write(f"⏹ {alarm_id} 취소됨\n")
            return f"⏹ {alarm_id}가 취소되었습니다."
        logger.write(f"⚠️ 알람 취소 실패: {alarm_id}가 존재하지 않음\n")
        return f"⚠️ '{alarm_id}' 알람을 찾을 수 없습니다."
    except KeyError as e:
        logger.write(f"⛔ 알람 취소 중 오류 발생 ({alarm_id}): {e}\n")
        return "알람 취소 중 오류가 발생했습니다."

def list_alarms() -> str:
    """현재 실행 중인 알람 목록 반환"""
    try:
        if not active_alarms:
            logger.write("🔍 현재 설정된 알람이 없음\n")
            return "🔍 현재 설정된 알람이 없습니다."

        alarm_list = "\n".join([f"🔔 {alarm_id} - 알람 시간: {alarm_time}" for alarm_id, (_, alarm_time) in active_alarms.items()])
        logger.write(f"📋 현재 알람 목록 요청\n")
        return f"📋 현재 설정된 알람 목록:\n{alarm_list}"
    except Exception as e:
        logger.write(f"⛔ 알람 목록 조회 중 오류 발생: {e}\n")
        return "알람 목록을 불러오는 중 오류가 발생했습니다."
