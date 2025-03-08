import os
import sys
import datetime

# 로그 파일 설정
LOG_DIR = "../log"
LOG_FILE = os.path.join(LOG_DIR, "events.log")
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

# 로그 디렉토리 생성 (없으면 자동 생성)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_next_log_filename():
    """파일 크기가 10MB를 초과하면 새로운 로그 파일 이름을 생성"""
    index = 1
    while True:
        new_log_file = os.path.join(LOG_DIR, f"events-{index}.log")
        if not os.path.exists(new_log_file):
            return new_log_file
        index += 1

def check_log_file():
    """로그 파일 크기를 확인하고 10MB 이상이면 새로운 파일로 회전"""
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        new_log_file = get_next_log_filename()
        os.rename(LOG_FILE, new_log_file)  # 기존 로그 파일 이름 변경

class Logger:
    """터미널 출력과 로그 파일 저장을 동시에 수행하는 클래스"""
    def __init__(self, filename=LOG_FILE):
        check_log_file()  # 로그 파일 크기 확인 및 변경
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        """터미널과 로그 파일에 동시에 기록"""
        check_log_file()  # 로그 파일 크기 확인 및 변경
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"{timestamp}: {message}"
        self.terminal.write(message)
        self.log.write(formatted_message)
        self.log.flush()  # 즉시 파일에 기록

    def flush(self):
        """터미널과 로그 버퍼 동기화"""
        self.terminal.flush()
        self.log.flush()

# 로거 인스턴스 생성
logger = Logger()

# 표준 출력 및 표준 에러를 로그 파일로 리디렉션
sys.stdout = logger
sys.stderr = logger
