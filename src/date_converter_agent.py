import datetime

def convert_date_format(date_str: str) -> str:
    """YYYY-MM-DD 형식의 날짜를 'YYYY년 MM월 DD일' 형식으로 변환"""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y년 %m월 %d일")
    except ValueError:
        return "올바른 날짜 형식이 아닙니다. 예: 2025-03-07"
