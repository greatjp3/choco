import os
import time
import re
import json
import datetime
import arrow
from dotenv import load_dotenv
from weather_daemon import get_saved_weather_data
from logger import logger

# ✅ 환경 변수에서 API 키 로드
load_dotenv()

# ✅ 예보 항목 (기상청 코드)
CATEGORY_MAP = {
    "TMN": "최저 기온",
    "TMX": "최고 기온",
    "SKY": "하늘 상태",
    "PTY": "강수 형태",
}

STATUS_OF_SKY = {
    "1": "맑음",
    "3": "구름 많음",
    "4": "흐림"
}

STATUS_OF_PRECIPITATION = {
    "0": "강수 없음",
    "1": "비",
    "2": "비 또는 눈",
    "3": "눈",
    "5": "빗방울",
    "6": "눈날림",
    "7": "소나기"
}
        
def parse_date(date_str: str):
    """ 
    자연어 날짜 ('오늘', '어제', '내일')를 YYYYMMDD 형식으로 변환
    """
    today = arrow.now("Asia/Seoul")
    date_mapping = {
        "오늘": today,
        "어제": today.shift(days=-1),
        "내일": today.shift(days=1),
    }
    return date_mapping.get(date_str, today).format("YYYYMMDD")

def convert_date_to_natural(date_str: str) -> str:
    """
    YYYYMMDD 형식의 날짜 문자열을 현재 날짜와 비교하여
    "어제", "오늘", "내일" 등의 자연어로 변환합니다.
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y%m%d").date()
    except Exception as e:
        logger.error(f"날짜 변환 오류: {e}")
        return date_str  # 변환 실패 시 원본 문자열 반환

    today = datetime.datetime.now().date()
    if date_obj == today - datetime.timedelta(days=1):
        return "어제"
    elif date_obj == today:
        return "오늘"
    elif date_obj == today + datetime.timedelta(days=1):
        return "내일"
    else:
        return date_obj.strftime("%Y-%m-%d")

def get_saved_weather(date: str = None):
    if date is None:
        # 현재 날짜를 "YYYYMMDD" 형식으로 구합니다.
        date = "오늘"

    dates = parse_date(date)
    # 저장된 날씨 정보를 불러옵니다.
    result = get_saved_weather_data(dates)
    if result is None:
        return True, "weather", "해당 날짜의 날씨 정보가 없습니다."
    
    data, sky, precipitation, lowest_temp, highest_temp, current_temp, pm10_val, pm10_grade, pm25_val, pm25_grade = result
       
    if precipitation == "0" :
        weather_description = f"{STATUS_OF_SKY.get(sky, '❓ 알 수 없음')}"
    else:
        weather_description = f"{STATUS_OF_PRECIPITATION.get(precipitation, '❓ 알 수 없음')}"
    
    # date를 자연어로 변환 ("어제", "오늘", "내일" 등)
    natural_date = convert_date_to_natural(dates)
    
    # 전체 날씨 메시지 생성
    if natural_date == "오늘":
        weather_msg = (f"{natural_date} 잠원동의 날씨는 {weather_description}입니다. "
                    f"최저 온도는 {int(float(lowest_temp))}도, 최고 온도는 {int(float(highest_temp))}도, 현재 온도는 {int(float(current_temp))}도입니다. 미세먼지는 {pm10_val}, {pm10_grade}, 초미세먼지는 {pm25_val}, {pm25_grade} 입니다.")
    else:    
        weather_msg = (f"{natural_date} 잠원동의 날씨는 {weather_description}입니다. "
                    f"최저 온도는 {int(float(lowest_temp))}도, 최고 온도는 {int(float(highest_temp))}도 입니다. 미세먼지는 {pm10_grade}, 초미세먼지는 {pm25_grade} 입니다.")

    return True, "weather", weather_msg

def compare_saved_weather(date1: str, date2: str):
    # 입력된 자연어 날짜를 "YYYYMMDD" 형식으로 변환합니다.
    dates1 = parse_date(date1)  # 예: "어제" → "20250404"
    dates2 = parse_date(date2)  # 예: "오늘" → "20250405"

    # 각 날짜의 날씨 데이터를 불러옵니다.
    result1 = get_saved_weather_data(dates1)
    result2 = get_saved_weather_data(dates2)

    if result1 is None or result2 is None:
        return "날씨 정보를 불러올 수 없습니다."
    
    # get_saved_weather_data()의 반환값: 
    # (data, sky, precipitation, lowest_temp, highest_temp, current_temp, pm10_val, pm10_grade, pm25_val, pm25_grade)
    _, _, _, lowest_temp1, highest_temp1, _, _, _, _, _ = result1
    _, _, _, lowest_temp2, highest_temp2, _, _, _, _, _ = result2

    # 온도를 실수 → 정수로 변환
    low1 = int(float(lowest_temp1))
    high1 = int(float(highest_temp1))
    low2 = int(float(lowest_temp2))
    high2 = int(float(highest_temp2))
    
    if low2 > low1 :
        low_diff_deg = low2 - low1
    else:
        low_diff_deg = low1 - low2
    if high2 > high1 :
        high_diff_deg = high2 - high1
    else:
        high_diff_deg = high1 - high2

    # 최저 온도 및 최고 온도의 차이 판단 ("높습니다.", "낮습니다.", "같습니다.")
    low_diff = "높습니다." if low2 > low1 else "낮습니다." if low2 < low1 else "같습니다."
    high_diff = "높습니다." if high2 > high1 else "낮습니다." if high2 < high1 else "같습니다."
    
    # 날짜를 자연어(예: "어제", "오늘", "내일")로 변환하여 메시지에 반영
    natural_date1 = convert_date_to_natural(dates1)
    natural_date2 = convert_date_to_natural(dates2)
    
    weather_msg = (
        f"{natural_date2} 잠원동의 날씨는 {natural_date1}에 비해, "
        f"최저 온도는 {low_diff_deg}도 {low_diff}, 최고 온도는 {high_diff_deg}도 {high_diff}"
    )
    
    return True, "weather", weather_msg

def get_saved_dust(date: str):
    weather_msg = None
    return weather_msg

def weather_action(text):
    # 1. 미세먼지 관련 요청 처리
    # if "미세먼지" in text:
    #     if re.search(r"내일\s*미세먼지", text):
    #         return get_saved_dust("내일")
    #     elif re.search(r"오늘\s*미세먼지", text):
    #         return get_saved_dust("오늘")
    #     else:
    #         return get_saved_dust()
    
    # 2. 날씨 비교 요청: "어제보다 오늘 날씨" 또는 "오늘보다 내일 날씨"
    compare_match = re.search(r"(어제|오늘)\s*보다\s*(오늘|내일)\s*날씨", text)
    if compare_match:
        start_day, end_day = compare_match.groups()
        return compare_saved_weather(start_day, end_day)
    
    # 3. 단일 날짜에 대한 날씨 요청: "어제 날씨", "오늘 날씨", "내일 날씨"
    single_match = re.search(r"(어제|오늘|내일)\s*날씨", text)
    if single_match:
        day = single_match.group(1)
        return get_saved_weather(day)
    
    # 4. "날씨"만 포함된 경우 기본적으로 오늘 날씨 조회
    if "날씨" in text:
        return get_saved_weather("오늘")
    
    return False, "weather", None
    
# ✅ 테스트 실행
if __name__ == "__main__":
    texts = ["날씨?",
        "오늘 날씨?",
        "내일 날씨?",
        "날씨 알려줘",
        "현재 기온이 몇 도야?",
        "비 올 예정이야?",
        "어제 보다 오늘 날씨?",
        "미세 먼지",
        "내일 추워?"]

    for text in texts:
        print(f"input:{text}")
        print(weather_action(text))


