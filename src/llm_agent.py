from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from alarm_agent import alarm_action
from volume_agent import volume_control_action
from weather_agent import weather_action
from youtube_agent import youtube_action

tools = [
    Tool(name="youtube_action", func=youtube_action, description="유튜브에서 음악을 검색하거나 재생하는 기능"),
    Tool(name="alarm_action", func=alarm_action, description="알람 설정 또는 타이머 관리 기능"),
    Tool(name="volume_control_action", func=volume_control_action, description="볼륨을 높이거나 낮추는 기능"),
    Tool(name="weather_action", func=weather_action, description="날씨 정보나 미세먼지 상태를 알려주는 기능")
]

prompt = PromptTemplate.from_template("""
사용자가 다음 요청을 했습니다:
"{text}"

원래 이 요청은 "{action_name}" 액션으로 처리되었으며 다음과 같은 결과가 있었습니다:
- 시스템 응답: "{response}"
- 내부 처리 결과: "{result}"

하지만 이 결과는 실패하거나 부적절했습니다.  
당신은 상황을 분석하고, 필요하다면 아래 도구 중 하나를 사용하여 적절한 기능을 다시 실행하세요.
""")

llm = ChatOpenAI(temperature=0.7)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def fallback_to_llm_with_tools(text, action_name, result, response):
    full_prompt = prompt.format(
        text=text,
        action_name=action_name,
        result=result,
        response=response
    )
    return agent.run(full_prompt)

