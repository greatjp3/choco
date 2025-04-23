from logger import logger
import datetime

def convert_date_format(date_str: str) -> str:
    """YYYY-MM-DD 형식의 날짜를 'YYYY년 MM월 DD일' 형식으로 변환"""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%Y년 %m월 %d일")
        
        # 변환 성공 로그 기록
        logger.write(f"✅ 날짜 변환 성공: {date_str} -> {formatted_date}\n")
        return formatted_date
    
    except ValueError:
        error_msg = "올바른 날짜 형식이 아닙니다. 예: 2025-03-07"
        logger.write(f"⚠️ 날짜 변환 오류 (ValueError): {date_str}\n")
        return error_msg

    except Exception as e:
        error_msg = "날짜 변환 중 오류가 발생했습니다."
        logger.write(f"⛔ 날짜 변환 중 예상치 못한 오류 발생: {date_str} | {e}\n")
        return error_msg
