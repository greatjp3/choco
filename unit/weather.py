import threading
import time
import json
import requests
import arrow
import os

# ✅ 환경 설정
KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
KMA_API_KEY = "dZJTmfJTYUbmN8dTZRtaJZ2kp8GyfbT6OtK7DAoW3jr261/sVlNtI/AKGnX0BAPrCqyTnahGAvPO45PU8h/kNQ=="  # 기상청 API 키
GRID_X, GRID_Y = 60, 127  # 서울시 잠원동 좌표
WEATHER_FILE = "weather_data.json"  # 저장할 파일
UPDATE_INTERVAL = 5 * 60  # 5분 (초 단위)

# ✅ 예보 발표 시간 (5분 후 업데이트)
FORECAST_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]

# ✅ 하늘 상태 (기상청 코드)
STATUS_OF_SKY = {"1": "☀ 맑음", "3": "⛅ 구름 많음", "4": "☁ 흐림"}
STATUS_OF_PRECIPITATION = {"0": "🌞 강수 없음", "1": "🌧 비", "2": "🌨 비/눈", "3": "❄ 눈", "5": "🌫 빗방울", "6": "🌨 눈날림", "7": "🌦 소나기"}

def get_latest_forecast_time():
    """ 현재 시간 기준 가장 가까운 발표 시간 반환 """
    now = arrow.now("Asia/Seoul")
    for hour in reversed(FORECAST_HOURS):
        if now.hour >= hour:
            return f"{hour:02}00"
    return "0200"  # 기본값 (새벽 2시)

def get_nearest_forecast_time():
    """ 현재 시간 기준 가장 가까운 발표 시간 반환 """
    now = arrow.now("Asia/Seoul")
    possible_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
    
    for time in reversed(possible_times):
        if now.hour >= int(time[:2]):  # 현재 시간보다 같거나 작은 발표 시간 찾기
            return time
    
    return "0200"  # 기본값 (새벽 2시)

def fetch_weather_data(base_date=None, base_time=None):
    """ 기상청 API에서 날씨 데이터 가져오기 (직전 발표된 데이터까지 탐색) """
    try:
        if not base_date:
            base_date = arrow.now("Asia/Seoul").format("YYYYMMDD")

        if not base_time:
            base_time = get_nearest_forecast_time()

        possible_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
        
        while base_time in possible_times:
            params = {
                "serviceKey": KMA_API_KEY,
                "numOfRows": "1000",
                "pageNo": "1",
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": GRID_X,
                "ny": GRID_Y,
            }

            response = requests.get(KMA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # ✅ 데이터가 존재하면 반환
            if data.get("response", {}).get("header", {}).get("resultCode") != "03":  
                return data
            
            # ❌ NO_DATA 발생 시 이전 발표 시간으로 변경
            print(f"🚨 NO_DATA: {base_date} {base_time}, 이전 발표 시간으로 변경")
            index = possible_times.index(base_time)
            base_time = possible_times[index - 1] if index > 0 else "0200"

        return None  # 모든 시간에서 데이터가 없으면 None 반환

    except Exception as e:
        print(f"🚨 날씨 업데이트 오류: {e}")
        return None

def save_weather_data(weather_data):
    """ 날씨 데이터를 JSON 파일에 저장 (최대 7일 유지) """
    if not weather_data:
        return

    try:
        if os.path.exists(WEATHER_FILE):
            with open(WEATHER_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        else:
            saved_data = []

        # ✅ 기존 데이터에 추가 (최신 데이터를 맨 앞에 추가)
        saved_data.insert(0, weather_data)

        # ✅ 1주일치 데이터 유지
        saved_data = saved_data[:7]

        # ✅ JSON 파일로 저장
        with open(WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump(saved_data, f, indent=4, ensure_ascii=False)

        print(f"✅ {weather_data['date']} 날씨 저장 완료!")

    except Exception as e:
        print(f"🚨 날씨 저장 오류: {e}")

def load_past_weather():
    """ 1주일치 데이터가 없으면 지난 데이터를 가져와 저장 """
    if os.path.exists(WEATHER_FILE):
        with open(WEATHER_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
    else:
        saved_data = []

    if len(saved_data) >= 7:
        return  # 이미 1주일치 데이터가 있으면 추가 저장 안 함

    print("⏳ 저장된 데이터 부족. 지난 날씨 데이터 가져오는 중...")

    # ✅ 부족한 날짜만큼 데이터 가져오기
    missing_days = 7 - len(saved_data)
    for i in range(1, missing_days + 1):
        past_date = arrow.now("Asia/Seoul").shift(days=-i).format("YYYYMMDD")
        past_weather = fetch_weather_data(base_date=past_date)

        if past_weather:
            saved_data.append(past_weather)

    # ✅ 업데이트된 데이터를 다시 저장
    with open(WEATHER_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_data, f, indent=4, ensure_ascii=False)

    print("✅ 지난 날씨 데이터 보완 완료.")

def get_weather_at_date(date: str):
    """ 특정 날짜의 날씨 데이터를 조회 (시간 무시) """
    if not os.path.exists(WEATHER_FILE):
        return "🚨 저장된 날씨 데이터가 없습니다."

    try:
        with open(WEATHER_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        for weather in saved_data:
            if weather["date"] == date:
                return (
                    f"📅 {weather['date']} 서울 잠원동 날씨\n"
                    f"🌏 하늘 상태: {weather['forecast']['SKY']}\n"
                    f"🌦 강수 형태: {weather['forecast']['PTY']}\n"
                    f"🔼 최고 기온: {weather['forecast'].get('TMX', '❓')}°C\n"
                    f"🔽 최저 기온: {weather['forecast'].get('TMN', '❓')}°C"
                )

        return "🚨 해당 날짜의 날씨 데이터가 없습니다."

    except Exception as e:
        return f"🚨 특정 날짜 날씨 불러오기 오류: {e}"

def update_weather_thread():
    """ 백그라운드에서 일정 간격으로 날씨 업데이트 """
    while True:
        now = arrow.now("Asia/Seoul")
        next_update_time = now.replace(minute=5)  # 발표 시간 5분 후
        wait_time = (next_update_time - now).seconds

        print(f"⏳ 다음 업데이트: {next_update_time.format('HH:mm:ss')} (약 {wait_time}초 후)")
        time.sleep(wait_time)

        weather_data = fetch_weather_data()
        save_weather_data(weather_data)

# ✅ 지난 날씨 데이터 로드
load_past_weather()

# ✅ 백그라운드에서 날씨 업데이트 실행
weather_thread = threading.Thread(target=update_weather_thread, daemon=True)
weather_thread.start()

# ✅ 테스트 실행
if __name__ == "__main__":
    time.sleep(2)
    print(get_weather_at_date("20250309"))  # 특정 날짜의 날씨 조회
