import os
import requests
import arrow
import urllib.parse
from dotenv import load_dotenv
import time
import re

# ✅ 환경 변수에서 API 키 로드
load_dotenv()
KMA_API_KEY = os.getenv("KMA_API_KEY")

# ✅ 기상청 단기예보 API URL
KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

# ✅ 기본 위치 (서울 잠원동)
DEFAULT_LOCATION = "서울 잠원동"

# class weather:
#     def __init__(self, time, timer):


# ✅ 격자 좌표 변환을 위한 지역 좌표 딕셔너리
GRID_COORDINATES = {
    "서울 잠원동": (60, 127),
    "부산": (98, 76),
    "대구": (89, 90),
    "광주": (58, 74),
    "인천": (55, 124),
    "대전": (67, 100),
    "울산": (102, 84),
    "제주": (52, 38),
    "강남구": (61, 125),
    "강북구": (61, 130),
    "송파구": (63, 124),
    "강서구": (58, 126),
    "노원구": (61, 129),
}

# ✅ 예보 항목 (기상청 코드)
CATEGORY_MAP = {
    "TMN": "최저 기온",
    "TMX": "최고 기온",
    "SKY": "하늘 상태",
    "PTY": "강수 형태",
}

STATUS_OF_SKY = {
    "1": "☀ 맑음",
    "3": "⛅ 구름 많음",
    "4": "☁ 흐림"
}

STATUS_OF_PRECIPITATION = {
    "0": "🌞 강수 없음",
    "1": "🌧 비",
    "2": "🌨 비/눈",
    "3": "❄ 눈",
    "5": "🌫 빗방울",
    "6": "🌨 눈날림",
    "7": "🌦 소나기"
}

def get_grid_coordinates(location: str):
    """ 지역명을 격자 좌표(nX, nY)로 변환 """
    if location in GRID_COORDINATES:
        return GRID_COORDINATES[location]
    return None  # 지원되지 않는 지역이면 None 반환

def get_nearest_forecast_time():
    """ 현재 시간 기준 가장 가까운 발표 시간 반환 """
    now = arrow.now("Asia/Seoul")
    possible_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
    
    for time in reversed(possible_times):
        if now.hour >= int(time[:2]):  # 현재 시간보다 같거나 작은 발표 시간 찾기
            return time
    
    return "0200"  # 기본값 (새벽 2시)

def fetch_weather_data(grid_x, grid_y, category, fcst_time, page_no, base_date=None, base_time=None):
    """ 기상청 API에서 특정 예보 데이터를 가져오는 함수 """
    try:
        if not base_date:
            base_date = arrow.now("Asia/Seoul").format("YYYYMMDD")

        if not base_time:
            base_time = get_nearest_forecast_time()

        possible_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
        
        while base_time in possible_times:
            params = {
                "serviceKey": os.getenv("KMA_API_KEY"),
                "numOfRows": "1000",
                "pageNo": page_no,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": grid_x,
                "ny": grid_y,
            }

            response = requests.get(KMA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # ✅ 응답 데이터에서 예보 값만 반환
            if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                items = data["response"]["body"]["items"]["item"]
                for item in items:
                    if item["category"] == category and item["fcstTime"] == fcst_time:
                        return item["fcstValue"]  # 🔹 올바른 예보 값만 반환

            # ❌ NO_DATA 발생 시 이전 발표 시간으로 변경
            print(f"🚨 NO_DATA: {base_date} {base_time}, 이전 발표 시간으로 변경")
            index = possible_times.index(base_time)
            base_time = possible_times[index - 1] if index > 0 else "0200"

        return None  # 모든 시간에서 데이터가 없으면 None 반환

    except Exception as e:
        print(f"🚨 날씨 업데이트 오류: {e}")
        return None

def get_latest_base_time():
    """ 현재 시각 기준 가장 가까운 기상청 발표 시간을 반환 """
    current_hour = arrow.now("Asia/Seoul").hour
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]  # 기상청 발표 시간
    latest_base_time = max([t for t in base_times if t <= current_hour])
    return f"{latest_base_time:02}00"  # 예: "1400"

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

def get_weather(date: str = None, time: str = None, location: str = None):
    """
    특정 지역과 날짜, 시간의 날씨 정보를 가져옴
    기본값: 오늘 날짜, 서울 잠원동, 가장 최근 기상청 발표 시간
    """
    try:
        # ✅ "오늘", "어제", "내일"이 location으로 들어오면 date로 변환
        if location in ["오늘", "어제", "내일"]:
            date = location
            location = None  # location이 아닌 date로 인식
        
        # ✅ 기본값 설정 (날짜: 오늘, 장소: 서울 잠원동, 시간: 최근 발표시간)
        if not location or location.strip() == "":
            location = DEFAULT_LOCATION
        if not date or date.strip() == "":
            date = arrow.now("Asia/Seoul").format("YYYYMMDD")  # 기본값: 오늘
        else:
            date = parse_date(date.strip())  # "오늘", "어제", "내일" 변환

        if not time or time.strip() == "":
            time = get_latest_base_time()

        print(f"🔍 요청: {date} {time}, 지역: {location}")

        # ✅ 지역명을 격자 좌표로 변환
        grid_coords = get_grid_coordinates(location)
        if not grid_coords:
            return f"❌ '{location}'에 대한 날씨 정보를 찾을 수 없습니다."

        grid_x, grid_y = grid_coords

        # ✅ 예보 데이터 가져오기
        sky = fetch_weather_data(grid_x, grid_y, "SKY", time, "3", date)
        precipitation = fetch_weather_data(grid_x, grid_y, "PTY", time, "4", date)
        lowest_temp = fetch_weather_data(grid_x, grid_y, "TMN", "0600", "5", date)
        highest_temp = fetch_weather_data(grid_x, grid_y, "TMX", "1500", "16", date)

        # ✅ 데이터 확인 및 변환
        if None in [sky, precipitation, lowest_temp, highest_temp]:
            return "❌ 날씨 정보를 가져오지 못했습니다. 😢"

        weather_description = f"{STATUS_OF_SKY.get(sky, '❓ 알 수 없음')} (강수: {STATUS_OF_PRECIPITATION.get(precipitation, '❓ 알 수 없음')})"

        # ✅ 최종 날씨 정보 정리
        weather_msg = (
            f"📅 {arrow.get(date, 'YYYYMMDD').format('YYYY년 MM월 DD일 dddd', locale='ko_kr')}\n"
            f"🕒 조회 시간: {time}\n"
            f"🌏 현재 날씨: {weather_description}\n"
            f"🔼 최고 기온: {highest_temp}°C\n"
            f"🔽 최저 기온: {lowest_temp}°C\n"
            f"📍 관측 지점: {location}"
        )

        return weather_msg

    except Exception as e:
        return f"❌ 날씨 정보 처리 중 오류 발생: {e}"


"오늘 {loction} 날씨는 {style}. 최저 {min_temp}도, 최고 {max_temp}도, 현재 {curr_temp}도. {dust}"
"오늘 미세 먼지는 {fine_dust}, 초미세 먼지는 {super_fine_dust}로 {dust_status}"


def compare_weather(location: str = None, date1: str = None, date2: str = None):
    try:
        weather1 = get_weather(location, date1)
        weather2 = get_weather(location, date2)
        comparison_mode = f"📅 같은 장소({location})의 다른 날짜 비교"

        # ✅ 오류 발생 확인
        if "❌" in weather1 or "❌" in weather2:
            return "⛔ 한 장소 이상의 날씨 정보를 가져오는 데 실패했습니다."

        return (
            f"📊 {comparison_mode}\n"
            f"🌍 {location} ({date1 if date1 else '오늘'}): {weather1}\n"
        )
    except Exception as e:
        return f"❌ 날씨 비교 중 오류 발생: {e}"

def weather_action(text):
    up_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*크게\b',
        text,
        re.IGNORECASE
    )
    down_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*작게\b',
        text,
        re.IGNORECASE
    )
    max_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*최대\b',
        text,
        re.IGNORECASE
    )
    med_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*중간\b',
        text,
        re.IGNORECASE
    )
    min_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*최소\b|조용히|음소거',
        text,
        re.IGNORECASE
    )

    if up_match:
        return v.volume_up()
    elif down_match:
        return v.volume_down()
    elif max_match:
        return v.volume_max()
    elif med_match:
        return v.volume_med()
    elif min_match:
        return v.volume_min()
    else:
        return "아빠 도와줘요"
    
# ✅ 테스트 실행
if __name__ == "__main__":
    start_time = time.time()  # 시작 시간 기록
    print(get_weather())  # 기본값: 서울 잠원동
    end_time = time.time()  # 종료 시간 기록
    elapsed = end_time - start_time  # 걸린 시간 계산
    print(f"⏱️ volume_med 수행 시간: {elapsed:.4f}초")