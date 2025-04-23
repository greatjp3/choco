import os
import time
import json
import arrow
import threading
import requests
import arrow
import urllib.parse
import datetime

from dotenv import load_dotenv
from logger import logger

# ✅ 환경 변수 로드
load_dotenv()

# ✅ 기본 위치 (서울 잠원동)
DEFAULT_LOCATION = "서울 잠원동"

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

# ✅ 설정
LOCATION = "서울 잠원동"
STATION_NAME = "서초구"  # 미세먼지 측정소
DATA_DIR = "weather_data"
FETCH_INTERVAL_HOURS = 3  # 3시간마다
START_HOUR = 2
START_MINUTE = 30
KEEP_DAYS = 3

# ✅ 디렉토리 생성
os.makedirs(DATA_DIR, exist_ok=True)

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

def fetch_weather_data(grid_x, grid_y, category, fcst_date, fcst_time, page_no, data_type="forecast", base_date=None, base_time=None):
    """
    기상청 예보/초단기 예보 데이터를 가져오는 통합 함수입니다.
      - data_type: "forecast" → getVilageFcst
                   "ultra"    → getUltraSrtFcst
      - fcst_date: 예보 대상 날짜 (YYYYMMDD 형식)
      - fcst_time: 예보 대상 시간 (HHMM 형식)
      - category: "SKY", "T1H", "TMX" 등
    """
    try:
        if not base_date:
            base_date = arrow.now("Asia/Seoul").format("YYYYMMDD")
        if not base_time:
            base_time = get_nearest_forecast_time()

        # 발표 가능한 base_time 목록
        possible_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]

        # URL 결정
        if data_type == "ultra":
            KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
        else:
            KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

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

            # 응답 내용이 비어 있는지 확인합니다.
            if not response.text.strip():
                logger.info(f"🚨 응답이 비어 있습니다. base_date: {base_date}, base_time: {base_time}")
                # 이전 발표 시간으로 변경 후 재시도
                index = possible_times.index(base_time)
                base_time = possible_times[index - 1] if index > 0 else "0200"
                continue

            try:
                data = response.json()
            except ValueError as ve:
                logger.error(f"🚨 JSON 파싱 오류: {ve}. base_date: {base_date}, base_time: {base_time}, 응답 내용: {response.text}")
                # 이전 발표 시간으로 변경 후 재시도
                index = possible_times.index(base_time)
                base_time = possible_times[index - 1] if index > 0 else "0200"
                continue

            if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                items = data["response"]["body"]["items"]["item"]
                for item in items:
                    # 카테고리와 fcstDate를 확인합니다.
                    if item["category"] != category:
                        continue
                    if item.get("fcstDate") != fcst_date:
                        continue

                    item_time = item.get("fcstTime")
                    if not item_time:
                        continue

                    try:
                        t1 = datetime.datetime.strptime(fcst_time, "%H%M")
                        t2 = datetime.datetime.strptime(item_time, "%H%M")
                        diff = abs((t1 - t2).total_seconds()) / 60
                        if diff <= 60:
                            return item["fcstValue"]
                    except ValueError:
                        logger.error("ValueError")
                        continue

            logger.warning(f"🚨 NO_DATA: {base_date} {base_time}, 이전 발표 시간으로 변경")
            index = possible_times.index(base_time)
            base_time = possible_times[index - 1] if index > 0 else "0200"

        return None

    except Exception as e:
        logger.error(f"🚨 날씨 업데이트 오류: {e}")
        return None
    
# def get_weather():
#     try:
#         location = DEFAULT_LOCATION
#         date = arrow.now("Asia/Seoul").format("YYYYMMDD")

#         # ✅ 격자 좌표
#         grid_coords = get_grid_coordinates(location)
#         if not grid_coords:
#             return f"❌ '{location}'에 대한 날씨 정보를 찾을 수 없습니다."
#         grid_x, grid_y = grid_coords

#         # ✅ 시간 설정 및 현재 여부 판단
#         now = arrow.now("Asia/Seoul")
#         today = now.format("YYYYMMDD")

#         base_datetime = now.shift(minutes=-40)
#         time = base_datetime.format("HHmm")

#         # ✅ 현재 날씨 (초단기예보)
#         current_temperature = fetch_weather_data(grid_x, grid_y, "T1H", time, "1", data_type="ultra", base_date=date)
#         sky = fetch_weather_data(grid_x, grid_y, "SKY", time, "1", data_type="ultra", base_date=date)
#         precipitation = fetch_weather_data(grid_x, grid_y, "PTY", time, "1", data_type="ultra", base_date=date)
#         lowest_temp = fetch_weather_data(grid_x, grid_y, "TMN", "0600", "5", data_type="forecast", base_date=date)
#         highest_temp = fetch_weather_data(grid_x, grid_y, "TMX", "1500", "16", data_type="forecast", base_date=date)

#         if None in [sky, precipitation, lowest_temp, highest_temp, current_temperature]:
#             return "❌ 날씨 정보를 가져오지 못했습니다. 😢"

#         return sky, precipitation, lowest_temp, highest_temp, current_temperature

#     except Exception as e:
#         return f"❌ 날씨 정보 처리 중 오류 발생: {e}"

def get_weather(fcst_date: str=None, time: str = None ):
    location = DEFAULT_LOCATION
    try:
        # ✅ "오늘", "어제", "내일"이 location으로 들어오면 date로 변환
        if not fcst_date or fcst_date.strip() == "":
            fcst_date = arrow.now("Asia/Seoul").format("YYYYMMDD")
        else:
            fcst_date = parse_date(fcst_date.strip())

        # ✅ 격자 좌표
        grid_coords = get_grid_coordinates(location)
        grid_x, grid_y = grid_coords

        # ✅ 시간 설정 및 현재 여부 판단
        now = arrow.now("Asia/Seoul")
        today = now.format("YYYYMMDD")

        if not time or time.strip() == "":
            base_datetime = now.shift(minutes=-40)
            time = base_datetime.format("HHmm")
        else:
            time = time.strip()

        if today == fcst_date:
            temperature = fetch_weather_data(grid_x, grid_y, "T1H", fcst_date, time, "1", data_type="ultra", base_date=today)
            sky = fetch_weather_data(grid_x, grid_y, "SKY", fcst_date, time, "1", data_type="ultra", base_date=today)
            precipitation = fetch_weather_data(grid_x, grid_y, "PTY", fcst_date, time, "1", data_type="ultra", base_date=today)
            lowest_temp = fetch_weather_data(grid_x, grid_y, "TMN", fcst_date, "0600", "5", data_type="forecast", base_date=today)
            highest_temp = fetch_weather_data(grid_x, grid_y, "TMX", fcst_date, "1500", "16", data_type="forecast", base_date=today)

            if None in [temperature, sky, precipitation, lowest_temp, highest_temp]:
                return "❌ 날씨 정보를 가져오지 못했습니다. 😢"
            
            return temperature, sky, precipitation, lowest_temp, highest_temp
        else:
            sky = fetch_weather_data(grid_x, grid_y, "SKY", fcst_date, time, "1", data_type="forecast", base_date=today)
            precipitation = fetch_weather_data(grid_x, grid_y, "PTY", fcst_date, time, "1", data_type="forecast", base_date=today)
            lowest_temp = fetch_weather_data(grid_x, grid_y, "TMN", fcst_date, "0600", "5", data_type="forecast", base_date=today)
            highest_temp = fetch_weather_data(grid_x, grid_y, "TMX", fcst_date, "1500", "16", data_type="forecast", base_date=today)

            if None in [sky, precipitation, lowest_temp, highest_temp]:
                return "❌ 날씨 정보를 가져오지 못했습니다. 😢"

            return sky, precipitation, lowest_temp, highest_temp

    except Exception as e:
        return f"❌ 날씨 정보 처리 중 오류 발생: {e}"

def classify_pm10(pm10_value):
    try:
        value = float(pm10_value)
    except (ValueError, TypeError):
        return "잘못된 입력"

    if 0 <= value <= 30:
        return "좋음"
    elif 31 <= value <= 80:
        return "보통"
    elif 81 <= value <= 150:
        return "나쁨"
    elif value >= 151:
        return "매우 나쁨"
    else:
        return "잘못된 입력"
    
def classify_pm25(pm25_value):
    try:
        value = float(pm25_value)
    except (ValueError, TypeError):
        return "잘못된 입력"

    if 0 <= value <= 15:
        return "좋음"
    elif 16 <= value <= 35:
        return "보통"
    elif 36 <= value <= 75:
        return "나쁨"
    elif value >= 76:
        return "매우 나쁨"
    else:
        return "잘못된 입력"

    
def get_dust_summary(date: str = None, location: str = None, mode: str=None):
    try:
        if not location or location.strip() == "":
            location = DEFAULT_LOCATION
        if not date or date.strip() == "":
            date = "오늘"

        now = arrow.now("Asia/Seoul")
        target_date = (
            now.format("YYYY-MM-DD") if date == "오늘" else
            now.shift(days=1).format("YYYY-MM-DD") if date == "내일" else
            arrow.get(date, "YYYYMMDD").format("YYYY-MM-DD")
        )

        location_keyword = location.split()[0]

        if mode == "forecast":
            # --- 1. 예보 등급 데이터 (PM10, PM2.5) ---
            forecast_url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMinuDustFrcstDspth"
            forecast_params = {
                "serviceKey": os.getenv("KMA_API_KEY"),
                "returnType": "json",
                "searchDate": now.format("YYYY-MM-DD"),
                "numOfRows": 100,
                "ver": "1.1"
            }

            forecast_res = requests.get(forecast_url, params=forecast_params)
            forecast_data = forecast_res.json()
            items = forecast_data["response"]["body"]["items"]

            pm10_grade = None
            pm25_grade = None
            pm10_info = ""
            pm25_info = ""

            for item in items:
                if item.get("informData") == target_date:
                    code = item.get("informCode")
                    if code == "PM10":
                        pm10_info = item.get("informGrade", "")
                    elif code == "PM25":
                        pm25_info = item.get("informGrade", "")

            for part in pm10_info.split(","):
                if location_keyword in part:
                    pm10_grade = part.split(":")[1].strip() if ":" in part else None
            for part in pm25_info.split(","):
                if location_keyword in part:
                    pm25_grade = part.split(":")[1].strip() if ":" in part else None

            return 0, pm10_grade, 0, pm25_grade
        else:
            # --- 2. 실시간 수치 조회 ---
            realtime_url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
            realtime_params = {
                "serviceKey": os.getenv("KMA_API_KEY"),
                "returnType": "json",
                "sidoName": location_keyword,
                "numOfRows": "100",
                "ver": "1.0"
            }

            realtime_res = requests.get(realtime_url, params=realtime_params)
            realtime_data = realtime_res.json()

            for item in realtime_data["response"]["body"]["items"]:
                if item["stationName"] == "서초구":  # 원하는 측정소
                    pm10_val = item["pm10Value"]
                    pm25_val = item["pm25Value"]
                    break
                            
            if pm10_val and pm25_val and pm10_val != "-" and pm25_val != "-":
                return pm10_val, classify_pm10(pm10_val), pm25_val, classify_pm25(pm25_val)
            else:
                return "❌ 미세먼지 정보를 가져오지 못했습니다."
    except Exception as e:
        return f"❌ 대기질 정보 처리 중 오류 발생: {e}"

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

def save_data_past(dates:str, times:str, sky:str, precipitation:str, lowest_temp:str, highest_temp:str, current_temperature:str, pm10_val:str, pm10_grade:str, pm25_val:str, pm25_grade:str):
    filename = os.path.join(DATA_DIR, f"{dates}_{times}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "date": dates,
            "time": times,
            "sky": sky,
            "precipitation": precipitation,
            "lowest_temp": lowest_temp,
            "highest_temp": highest_temp,
            "current_temperature": current_temperature, 
            "pm10_val": pm10_val, 
            "pm10_grade": pm10_grade, 
            "pm25_val": pm25_val,
            "pm25_grade": pm25_grade
        }, f, ensure_ascii=False, indent=2)

def save_data_forecast(dates:str, times:str, sky:str, precipitation:str, lowest_temp:str, highest_temp:str, pm10_val:str, pm10_grade:str, pm25_val:str, pm25_grade:str):
    filename = os.path.join(DATA_DIR, f"{dates}_{times}_forecast.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "date": dates,
            "time": times,
            "sky": sky,
            "precipitation": precipitation,
            "lowest_temp": lowest_temp,
            "highest_temp": highest_temp,
            "pm10_val": pm10_val, 
            "pm10_grade": pm10_grade, 
            "pm25_val": pm25_val,
            "pm25_grade": pm25_grade
        }, f, ensure_ascii=False, indent=2)

def cleanup_old_files():
    cutoff = arrow.now().shift(days=-KEEP_DAYS)
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            try:
                # 파일명 예: "20250404_1637.json" 또는 "20250404_1637_forecast.json"
                # ".json" 제거 후 "_" 기준으로 분리하여 첫 두 요소(날짜, 시간)를 결합합니다.
                parts = filename.replace(".json", "").split("_")
                ts = "_".join(parts[:2])
                file_time = arrow.get(ts, "YYYYMMDD_HHmm")
                if file_time < cutoff:
                    os.remove(filepath)
                    logger.info(f"🧹 오래된 파일 삭제: {filename}")
            except Exception as e:
                logger.error(f"⚠️ 파일 삭제 중 오류: {e}")

def should_run_now():
    now = arrow.now("Asia/Seoul")
    # 시작 시각 기준으로 3시간 간격인지 확인
    base = now.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
    diff = (now - base).total_seconds()
    return diff >= 0 and diff % (FETCH_INTERVAL_HOURS * 3600) < 60  # 1분 오차 허용

def run_daemon():
    logger.info("Weather Daemon 시작...")

    try:
        # 시작 시 한 번 즉시 업데이트
        now = arrow.now("Asia/Seoul")
        times = now.format("HHmm")
        if(times <= "0300"):
            dates = now.format("YYYYMMDD")
        else:   
            dates = now.shift(days=-1).format("YYYYMMDD")

        current_temperature, sky, precipitation, lowest_temp, highest_temp = get_weather("오늘")
        pm10_val, pm10_grade, pm25_val, pm25_grade = get_dust_summary(date="오늘", location=LOCATION, mode="realtime")
        save_data_past(dates, times, sky, precipitation, lowest_temp, highest_temp, current_temperature, pm10_val, pm10_grade, pm25_val, pm25_grade)

        dates = now.shift(days=1).format("YYYYMMDD")
        sky, precipitation, lowest_temp, highest_temp = get_weather("내일") #fcst_date=dates)
        pm10_val, pm10_grade, pm25_val, pm25_grade = get_dust_summary(date=dates, location=LOCATION, mode="forecast")
        save_data_forecast(dates, times, sky, precipitation, lowest_temp, highest_temp, None, pm10_grade, None, pm25_grade)

        cleanup_old_files()
        logger.info("✅ 초기 저장 완료")
    except Exception as e:
        logger.error("failed to get weather info")
    
    while True:
        if should_run_now():
            now = arrow.now("Asia/Seoul")
            timestamp = now.format("YYYYMMDD_HHmm")

            logger.info(f"업데이트: {timestamp}")
            sky, precipitation, lowest_temp, highest_temp, current_temperature = get_weather(location=LOCATION)
            pm10_val, pm10_grade, pm25_val, pm25_grade = get_dust_summary(location=LOCATION)
            save_data_past(dates, times, sky, precipitation, lowest_temp, highest_temp, current_temperature, pm10_val, pm10_grade, pm25_val, pm25_grade)
            cleanup_old_files()

            logger.info("저장 완료")
            time.sleep(60)  # 1분 대기 후 다음 체크로 넘어감
        else:
            time.sleep(30)  # 대기 중

def start_weather_daemon():
    daemon_thread = threading.Thread(target=run_daemon, daemon=True)
    daemon_thread.start()
    logger.info("Weather Daemon 스레드 시작됨")

def get_saved_weather_data(date: str):
    matched_files = []
    
    # DATA_DIR 디렉토리 내의 파일들 중 지정된 날짜로 시작하는 JSON 파일을 찾습니다.
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json") and filename.startswith(f"{date}_"):
            # 파일명이 "날짜_시간.json" 또는 "날짜_시간_forecast.json" 형식인지 확인합니다.
            time_part = filename[len(date) + 1: len(date) + 5]  # 날짜 뒤의 '_' 이후 4자리 추출
            if len(time_part) == 4 and time_part.isdigit():
                matched_files.append(filename)
    
    if not matched_files:
        return None  # 해당 날짜의 파일이 없으면 None 반환합니다.
    
    # _forecast가 없는 파일을 우선적으로 사용합니다.
    non_forecast_files = [f for f in matched_files if "_forecast" not in f]
    if non_forecast_files:
        matched_files = non_forecast_files
    
    # 시간 부분(HHMM)을 기준으로 내림차순 정렬합니다 (가장 늦은 시간 우선).
    matched_files.sort(key=lambda x: x[len(date) + 1: len(date) + 5], reverse=True)
    
    # 정렬된 파일 목록에서 데이터가 비어 있지 않은 파일을 찾아 반환합니다.
    for filename in matched_files:
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:  # 데이터가 비어 있지 않으면 반환합니다.
                sky = data.get("sky")
                precipitation = data.get("precipitation")
                lowest_temp = data.get("lowest_temp")
                highest_temp = data.get("highest_temp")
                current_temp = data.get("current_temperature")
                pm10_val = data.get("pm10_val")
                pm10_grade = data.get("pm10_grade")
                pm25_val = data.get("pm25_val")
                pm25_grade = data.get("pm25_grade")
                return data, sky, precipitation, lowest_temp, highest_temp, current_temp, pm10_val, pm10_grade, pm25_val, pm25_grade
        except Exception as e:
            logger.error(f"⚠️ 파일 읽기 오류: {e}")
    
    # 모든 파일의 데이터가 비어 있으면 None 반환합니다.
    return None

if __name__ == "__main__":
    run_daemon()
    #start_weather_daemon()
    # while True:
    #     # 메인 스레드에서 다른 작업 수행 가능
    #     print("날씨 메인 스레드 실행 중...")
    # print(get_dust_summary(date="오늘", location=LOCATION))
    # print(get_dust_summary(date="내일", location=LOCATION))

