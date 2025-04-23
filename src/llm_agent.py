from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from alarm_agent import alarm_action
from volume_agent import volume_control_action
from weather_agent import weather_action
from youtube_agent import youtube_action
from logger import logger
from init_agent import init_action  # ✅ 추가

tools = [
    Tool(name="youtube_action", func=youtube_action, description="유튜브에서 음악을 검색하거나 재생하는 기능"),
    Tool(name="alarm_action", func=alarm_action, description="알람 설정 또는 타이머 관리 기능"),
    Tool(name="volume_control_action", func=volume_control_action, description="볼륨을 높이거나 낮추는 기능"),
    Tool(name="weather_action", func=weather_action, description="날씨 정보나 미세먼지 상태를 알려주는 기능"),
    Tool(name="init_action", func=init_action, description="시스템을 리부팅하는 기능")  # ✅ 추가
]

prompt_templates = {
    "youtube": PromptTemplate.from_template("""
사용자의 원래 요청:
"{text}"

이 요청은 "youtube_action" 액션으로 처리되었지만 실패하거나 부적절한 결과가 발생했습니다.
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

아래와 같은 명령어 형태로 수정해주세요:
- "아이유 노래 틀어줘"
- "다음 곡", "멈춰", "꺼줘", "이전 곡" 등

유튜브 음악 재생 기능에 적합한 명확한 명령어 텍스트로 변환한 후 다시 실행하세요.
"""),

    "alarm": PromptTemplate.from_template("""
사용자의 원래 요청:
"{text}"

이 요청은 "alarm_action" 액션으로 처리되었지만 실패하거나 부적절한 결과가 발생했습니다.
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

다음과 같은 형식으로 명확히 표현해주세요:
- 알람/타이머 설정: "오전 7시 알람 맞춰줘", "10분 뒤 깨워줘"
- 삭제: "알람 삭제해줘"
- 정지: "타이머 꺼줘"

시간 표현과 알람/타이머 키워드를 포함한 문장으로 다시 작성하여 실행하세요.
"""),

    "weather": PromptTemplate.from_template("""
사용자의 원래 요청:
"{text}"

이 요청은 "weather_action" 액션으로 처리되었지만 실패하거나 부적절한 결과가 발생했습니다.
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

아래와 같은 명령어를 참고하여 다시 작성해주세요:
- "오늘 날씨 알려줘", "내일 날씨는 어때?"
- "어제보다 오늘 날씨 어때?"

날짜와 날씨 키워드를 포함한 간단한 문장으로 다시 작성하여 실행하세요.
"""),

    "volume": PromptTemplate.from_template("""
사용자의 원래 요청:
"{text}"

이 요청은 "volume_control_action" 액션으로 처리되었지만 실패하거나 부적절한 결과가 발생했습니다.
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

다음과 같이 명확한 볼륨 제어 명령어로 표현해주세요:
- "볼륨 크게", "소리 작게"
- "볼륨 최대", "조용히 해줘"

볼륨 또는 소리 조절에 관련된 간단한 명령어로 다시 작성하여 실행하세요.
"""),

    "init": PromptTemplate.from_template("""
사용자의 원래 요청:
"{text}"

이 요청은 "init_action" 액션으로 처리되었지만 실패하거나 부적절한 결과가 발생했습니다.
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

다음과 같이 명확한 시스템 재시작 명령어로 표현해주세요:
- "시스템 리부팅해줘", "다시 켜줘"
- "껐다 켜줘", "라즈베리파이 재부팅해줘"

'리부팅' 또는 '초기화' 키워드를 포함한 간결한 문장으로 다시 작성하여 실행하세요.
""")
}

llm = ChatOpenAI(temperature=0.7)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def fallback_to_llm_with_tools(text, action_name, result, response):
    prompt_template = prompt_templates.get(result)

    if prompt_template is None:
        logger.warning(f"No specific prompt found for result type '{result}', falling back to default prompt.")
        return text  # 또는 default_prompt.run(...)

    full_prompt = prompt_template.format(
        text=text,
        action_name=action_name,
        result=result,
        response=response
    )

    return agent.run(full_prompt)


