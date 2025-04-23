import os
import sys
import datetime
import inspect

# ✅ 로그 파일 설정
LOG_DIR = "../log"
LOG_FILE = os.path.join(LOG_DIR, "events.log")
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

# ✅ 로그 디렉토리 생성 (없으면 자동 생성)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_next_log_filename():
    """ 파일 크기가 10MB를 초과하면 새로운 로그 파일 이름을 생성 """
    index = 1
    while True:
        new_log_file = os.path.join(LOG_DIR, f"events-{index}.log")
        if not os.path.exists(new_log_file):
            return new_log_file
        index += 1

def check_log_file():
    """ 로그 파일 크기를 확인하고 10MB 이상이면 새로운 파일로 회전 """
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        new_log_file = get_next_log_filename()
        os.rename(LOG_FILE, new_log_file)  # 기존 로그 파일 이름 변경

class Logger:
    """ 터미널 출력과 로그 파일 저장을 동시에 수행하는 클래스 """
    def __init__(self, filename=LOG_FILE):
        check_log_file()  # 로그 파일 크기 확인 및 변경
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def _get_caller_info(self):
        """ 로그를 호출한 코드의 파일명과 라인 번호 반환 """
        stack = inspect.stack()
        caller_frame = stack[2]  # [0]은 현재 함수, [1]은 write(), [2]는 실제 호출한 함수
        filename = os.path.basename(caller_frame.filename)  # 파일명만 추출
        line_number = caller_frame.lineno
        return f"{filename}:{line_number}"

    def write(self, message):
        """ 터미널과 로그 파일에 동시에 기록 (호출된 코드의 파일과 라인 번호 포함) """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caller_info = self._get_caller_info()
        formatted_message = f"{timestamp} [{caller_info}]: {message}"
        
        self.terminal.write(message)
        self.terminal.flush()
        self.log.write(formatted_message)
        self.log.flush()  # 즉시 파일에 기록

    def error(self, message):
        """ 에러 메시지 기록 (호출된 코드 정보 포함) """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caller_info = self._get_caller_info()
        formatted_message = f"{timestamp} [{caller_info}] [ERROR]: {message}\n"
        
        self.terminal.write(formatted_message)
        self.terminal.flush()
        self.log.write(formatted_message)
        self.log.flush()

    def info(self, message):
        """ 일반 정보 메시지 기록 (호출된 코드 정보 포함) """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caller_info = self._get_caller_info()
        formatted_message = f"{timestamp} [{caller_info}] [INFO]: {message}\n"
        
        self.terminal.write(formatted_message)
        self.terminal.flush()
        self.log.write(formatted_message)
        self.log.flush()
    
    def warning(self, message):
        """ 일반 정보 메시지 기록 (호출된 코드 정보 포함) """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caller_info = self._get_caller_info()
        formatted_message = f"{timestamp} [{caller_info}] [WARN]: {message}\n"
        
        self.terminal.write(formatted_message)
        self.terminal.flush()
        self.log.write(formatted_message)
        self.log.flush()

    def flush(self):
        """ 터미널과 로그 버퍼 동기화 """
        self.terminal.flush()
        self.log.flush()

# ✅ 로거 인스턴스 생성
logger = Logger()

# ✅ 표준 출력 및 표준 에러를 로그 파일로 리디렉션
sys.stdout = logger
sys.stderr = logger

# ✅ 테스트 실행
if __name__ == "__main__":
    print("✅ 프로그램 시작")
    logger.info("This is an info log.")
    logger.error("This is an error log.")
    print("✅ 프로그램 종료")
