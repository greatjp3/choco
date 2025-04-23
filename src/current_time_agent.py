from logger import logger
import datetime

def get_current_time() -> str:
    """현재 시간을 반환"""
    try:
        now = datetime.datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        logger.write(f"✅ 현재 시간 요청: {current_time}\n")
        return f"🕒 현재 시간: {current_time}"
    except Exception as e:
        logger.write(f"⛔ 현재 시간 조회 중 오류 발생: {e}\n")
        return "현재 시간을 불러오는 중 오류가 발생했습니다."
   
def compare_time(target_time: str) -> str:
    """현재 시간과 입력된 시간을 비교"""
    try:
        now = datetime.datetime.now()
        target_datetime = datetime.datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
        
        if now < target_datetime:
            diff = target_datetime - now
            return f"⏳ 입력한 시간({target_time})까지 {diff} 남았습니다."
        elif now > target_datetime:
            diff = now - target_datetime
            return f"⌛ 입력한 시간({target_time})은 {diff} 전에 지났습니다."
        else:
            return "⏰ 입력한 시간과 현재 시간이 동일합니다."
    except ValueError:
        logger.write(f"⚠️ 잘못된 시간 형식 입력: {target_time}\n")
        return "올바른 시간 형식으로 입력하세요. 예: '2025-03-08 15:30:00'"
    except Exception as e:
        logger.write(f"⛔ 시간 비교 중 오류 발생: {e}\n")
        return "시간을 비교하는 중 오류가 발생했습니다."
