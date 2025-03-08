from logger import logger
import os
import warnings
import json
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

# 예외 발생 가능성이 있는 모듈들 로드
try:
    from langchain.tools import Tool
    from langchain_openai import ChatOpenAI
    from langchain.agents import initialize_agent, AgentType

    from timer_agent import start_timer, cancel_timer, list_timers
    from alarm_agent import set_alarm, cancel_alarm, list_alarms
    from date_converter_agent import convert_date_format
    from calculator_agent import simple_calculator

    from alarm_agent import *
    from calculator_agent import *
    from date_converter_agent import *
    from timer_agent import *

except ImportError as e:
    logger.write(f"모듈 임포트 오류 발생: {e}\n")
    print(f"모듈 임포트 오류 발생: {e}")
    exit(1)

load_dotenv()

# OpenAI API 키 로드
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.write("환경 변수 오류: OPENAI_API_KEY가 설정되지 않았습니다.\n")
    print("환경 변수 오류: OPENAI_API_KEY가 설정되지 않았습니다.")
    exit(1)
logger.write("✅ OPENAI_API_KEY가 설정되었습니다.\n")

# 안전한 도구 초기화 (예외 방지)
def safe_tool(name, func, description):
    """ 도구 생성 시 예외 방지 """
    try:
        return Tool(name=name, func=func, description=description)
    except Exception as e:
        logger.write(f"도구 {name} 초기화 실패: {e}\n")
        print(f"도구 {name} 초기화 실패: {e}")
        return None

# 타이머 도구
timer_tool = safe_tool("Timer", start_timer, "설정된 시간 후에 알림을 보냅니다. 복합 형식 지원. 예: '10s', '5m', '1h 30m 10s'")
cancel_timer_tool = safe_tool("Cancel_Timer", cancel_timer, "설정된 타이머를 취소합니다. 예: '1번 타이머'")
list_timer_tool = safe_tool("List_Timers", list_timers, "현재 실행 중인 타이머 목록을 확인합니다.")

# 알람 도구
alarm_tool = safe_tool("Alarm", set_alarm, "특정 시간에 알람을 설정합니다. 예: '07:30', '15:00'")
cancel_alarm_tool = safe_tool("Cancel_Alarm", cancel_alarm, "설정된 알람을 취소합니다. 예: '1번 알람'")
list_alarm_tool = safe_tool("List_Alarms", list_alarms, "현재 설정된 알람 목록을 확인합니다.")

# 날짜 변환 도구
date_tool = safe_tool("Date_Converter", convert_date_format, "YYYY-MM-DD 형식의 날짜를 'YYYY년 MM월 DD일' 형식으로 변환합니다.")

# 계산기 도구
calculator_tool = safe_tool("Calculator", simple_calculator, "기본적인 숫자 연산을 수행합니다. 예: '2 + 3', '10 / 2'")

# 도구 리스트에서 None 제거 (예외로 인해 생성되지 않은 도구 제거)
tools = [tool for tool in [timer_tool, cancel_timer_tool, list_timer_tool, alarm_tool, cancel_alarm_tool, list_alarm_tool, date_tool, calculator_tool] if tool is not None]

# LangChain AI Agent 설정
try:
    llm = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=api_key)
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,  # OpenAI의 Function Calling 사용
        verbose=True
    )
except Exception as e:
    logger.write(f"LangChain 에이전트 초기화 실패: {e}\n")
    print(f"LangChain 에이전트 초기화 실패: {e}")
    exit(1)
