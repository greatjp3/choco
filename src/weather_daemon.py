import os
import time
import json
import arrow
import threading
from dotenv import load_dotenv
from weather_agent import get_current_weather, get_dust_summary

# ✅ 환경 변수 로드
load_dotenv()

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

def save_data(dates:str, times:str, sky:str, precipitation:str, lowest_temp:str, highest_temp:str, current_temperature:str, pm10_val:str, pm10_grade:str, pm25_val:str, pm25_grade:str):
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

def cleanup_old_files():
    cutoff = arrow.now().shift(days=-KEEP_DAYS)
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            try:
                ts = filename.replace(".json", "")
                file_time = arrow.get(ts, "YYYYMMDD_HHmm")
                if file_time < cutoff:
                    os.remove(filepath)
                    print(f"🧹 오래된 파일 삭제: {filename}")
            except Exception as e:
                print(f"⚠️ 파일 삭제 중 오류: {e}")

def should_run_now():
    now = arrow.now("Asia/Seoul")
    # 시작 시각 기준으로 3시간 간격인지 확인
    base = now.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
    diff = (now - base).total_seconds()
    return diff >= 0 and diff % (FETCH_INTERVAL_HOURS * 3600) < 60  # 1분 오차 허용

def run_daemon():
    print("🌤️ Weather Daemon 시작...")

    # 시작 시 한 번 즉시 업데이트
    now = arrow.now("Asia/Seoul")
    dates = now.format("YYYYMMDD")
    times = now.format("HHmm")
    sky, precipitation, lowest_temp, highest_temp, current_temperature = get_current_weather(location=LOCATION)
    pm10_val, pm10_grade, pm25_val, pm25_grade = get_dust_summary(location=LOCATION)
    save_data(dates, times, sky, precipitation, lowest_temp, highest_temp, current_temperature, pm10_val, pm10_grade, pm25_val, pm25_grade)
    cleanup_old_files()
    print("✅ 초기 저장 완료")
    while True:
        if should_run_now():
            now = arrow.now("Asia/Seoul")
            timestamp = now.format("YYYYMMDD_HHmm")

            print(f"⏰ 업데이트: {timestamp}")
            sky, precipitation, lowest_temp, highest_temp, current_temperature = get_current_weather(location=LOCATION)
            pm10_val, pm10_grade, pm25_val, pm25_grade = get_dust_summary(location=LOCATION)
            save_data(dates, times, sky, precipitation, lowest_temp, highest_temp, current_temperature, pm10_val, pm10_grade, pm25_val, pm25_grade)
            cleanup_old_files()

            print("✅ 저장 완료")
            time.sleep(60)  # 1분 대기 후 다음 체크로 넘어감
        else:
            time.sleep(30)  # 대기 중

def start_weather_daemon():
    daemon_thread = threading.Thread(target=run_daemon, daemon=True)
    daemon_thread.start()
    print("🧵 Weather Daemon 스레드 시작됨")

def get_saved_weather(dates: str):
    matched_files = []
    
    # DATA_DIR 디렉토리 내의 파일들 중 지정된 날짜로 시작하는 JSON 파일 선별
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json") and filename.startswith(f"{dates}_"):
            # 파일명의 형식이 "날짜_시간.json"인지 확인 (예: 20250404_2210.json)
            time_part = filename[len(dates) + 1: len(dates) + 5]  # 날짜 뒤의 '_' 이후 4자리 추출
            if len(time_part) == 4 and time_part.isdigit():
                matched_files.append(filename)
    
    if not matched_files:
        return None  # 해당 날짜의 파일이 없으면 None 반환
    
    # 시간 부분(HHMM)을 기준으로 내림차순 정렬 (가장 늦은 시간 우선)
    matched_files.sort(key=lambda x: x[len(dates) + 1: len(dates) + 5], reverse=True)
    
    # 정렬된 파일 목록에서 데이터가 비어 있지 않은 파일을 찾아 반환
    for filename in matched_files:
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:  # 데이터가 비어 있지 않으면 반환
                return data
        except Exception as e:
            print(f"⚠️ 파일 읽기 오류: {e}")
    
    # 모든 파일의 데이터가 비어 있으면 None 반환
    return None

if __name__ == "__main__":
    # run_daemon()
    # start_weather_daemon()
    # while True:
    #     # 메인 스레드에서 다른 작업 수행 가능
    #     print("날씨 메인 스레드 실행 중...")
    # time.sleep(60*60)  # 60분마다 로그 출력
    print(get_saved_weather("20250404"))