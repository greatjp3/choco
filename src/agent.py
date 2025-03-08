import os
from dotenv import load_dotenv
import json
from langchain.tools import Tool

from timer_agent import start_timer, cancel_timer, list_timers
from alarm_agent import set_alarm, cancel_alarm, list_alarms
from date_converter_agent import convert_date_format
from calculator_agent import simple_calculator
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from alarm_agent import *
from calculator_agent import *
from date_converter_agent import *
from timer_agent import *

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"set OPENAI_API_KEY")

# 타이머 도구
timer_tool = Tool(
    name="Timer",
    func=start_timer,
    description="설정된 시간 후에 알림을 보냅니다. 복합 형식 지원. 예: '10s', '5m', '1h 30m 10s'"
)

cancel_timer_tool = Tool(
    name="Cancel_Timer",
    func=cancel_timer,
    description="설정된 타이머를 취소합니다. 예: '1번 타이머'"
)

list_timer_tool = Tool(
    name="List_Timers",
    func=list_timers,
    description="현재 실행 중인 타이머 목록을 확인합니다. 예: '타이머 목록'"
)

# 알람 도구
alarm_tool = Tool(
    name="Alarm",
    func=set_alarm,
    description="특정 시간에 알람을 설정합니다. 예: '07:30', '15:00'"
)

cancel_alarm_tool = Tool(
    name="Cancel_Alarm",
    func=cancel_alarm,
    description="설정된 알람을 취소합니다. 예: '1번 알람'"
)

list_alarm_tool = Tool(
    name="List_Alarms",
    func=list_alarms,
    description="현재 설정된 알람 목록을 확인합니다. 예: '알람 목록'"
)

# 날짜 변환 도구
date_tool = Tool(
    name="Date_Converter",
    func=convert_date_format,
    description="YYYY-MM-DD 형식의 날짜를 'YYYY년 MM월 DD일' 형식으로 변환합니다."
)

# 계산기 도구
calculator_tool = Tool(
    name="Calculator",
    func=simple_calculator,
    description="기본적인 숫자 연산을 수행합니다. 예: '2 + 3', '10 / 2'"
)

# LangChain AI Agent 설정
llm = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=api_key)

agent = initialize_agent(
    tools=[timer_tool, cancel_timer_tool, list_timer_tool, alarm_tool, cancel_alarm_tool, list_alarm_tool, date_tool, calculator_tool],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,  # OpenAI의 Function Calling 사용
    verbose=True
)

### 7. 사용자 입력에 따라 에이전트 실행 ###
if __name__ == "__main__":
    # 예제 1: 07:30 알람 설정
    response1 = agent.run("07:30 알람을 설정해줘.")
    print("응답 1:", response1)

    # 예제 2: 15:00 알람 설정
    response2 = agent.run("15:00 알람을 설정해줘.")
    print("응답 2:", response2)

    # 예제 3: 현재 설정된 알람 목록 확인
    response3 = agent.run("알람 목록을 보여줘.")
    print("응답 3:", response3)

    # 예제 4: 특정 알람 취소
    response4 = agent.run("1번 알람을 취소해줘.")
    print("응답 4:", response4)

    # 예제 5: 다시 알람 목록 확인
    response5 = agent.run("알람 목록을 보여줘.")
    print("응답 5:", response5)