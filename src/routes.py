from semantic_router.layer import RouteLayer
import semantic_router.encoders as encoders
from semantic_router import Route

from actions import *
from dotenv import load_dotenv

from alarm_agent import alarm_action
from volume_agent import volume_control_action
from weather_agent import weather_action

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

encoder = encoders.OpenAIEncoder(
    name="text-embedding-3-large", score_threshold=0.5, dimensions=256
)

# Define routes
volume_route = Route(
    name="volume_control_action",
    utterances=[
        "소리 크게",
        "볼륨 크게",
        "소리 작게",
        "볼륨 작게",
        "소리 최대",
        "소리 최소",
        "볼륨 최대",
        "볼륨 최소",
        "음소거"
    ]
)

alarm_route = Route(
    name="alarm_action",
    utterances=[
        "몇 시에 알람해 줘",
        "몇 시 몇 분에 알람",
        "알람 취소",
        "몇 분 타이머",
        "몇 시간 타이머",
        "몇 분 후에 알려줘",
        "몇 시간 후에 알려줘",
        "몇 시간 몇 분 후에 알람",
        "타이머 취소"
    ]
)

youtube_route = Route(
    name="youtube_action",
    utterances=[
        "음악 재생",
        "음악 켜줘",
        "다음 곡",
        "이전 곡",
        "음악 꺼줘"
    ]
)

weather_route = Route(
    name="weather_action",
    utterances = [
        "날씨?"
        "오늘 날씨?",
        "날씨 알려줘",
        "현재 기온이 몇 도야?",
        "비 올 예정이야?",
        "어제 보다 오늘 날씨?",
        "미세 먼지",
        "내일 추워?"
    ]
)

aquarium_route = Route(
    name="aquarium_action",
    utterances = [
        "어항 켜줘",
        "어항 꺼줘"
    ]
)

general_route = Route(
    name="llm_action",
    utterances = [
        "어떻게 지내?",
        "농담 하나 해줘",
        "지금 몇 시야?",
        "잘 지내?",
        "삶의 의미가 뭐야?",
        "프랑스의 수도는 어디야?",
        "파이썬 2와 파이썬 3의 차이점이 뭐야?",
        "가장 좋은 프로그래밍 언어는 뭐야?",
        "미국의 첫 번째 대통령은 누구야?",
        "가장 큰 포유류는 뭐야?"
    ]
)

routes = [volume_route, alarm_route, youtube_route, weather_route, aquarium_route, general_route]

# Initialize RouteLayer with the encoder and routes
rl = RouteLayer(encoder=encoder, routes=routes)

class ActionRouter:
    def __init__(self):
        self.route_layer = rl

    def resolve(self, text):
        logger.info(f"Resolving text: {text}")
        try:
            result = self.route_layer(text)
            action_name = result.name if result else "llm_action"
            logger.info(f"Resolved action: {action_name}")
            return action_name
        except Exception as e:
            logger.error(f"Error resolving text: {e}")
            return "llm_action"

class Action:
    def __init__(self, action_name, text):
        self.action_name = action_name
        self.text = text

    def perform(self, **kwargs):
        try:
            action_func = globals()[self.action_name]
            # logger.info(f"Performing action: {self.action_name} with text: {self.text}")
            return action_func(self.text, **kwargs)
        except KeyError:
            logger.warning(f"Action {self.action_name} not found. Falling back to llm_action.")
            action_func = globals()["llm_action"]
            return action_func(self.text, **kwargs)
        except Exception as e:
            logger.error(f"Error performing action {self.action_name}: {e}")
            return "Action failed due to an error."

def action_router(text: str, router=ActionRouter()):
    try:
        action_name = router.resolve(text)
        act = Action(action_name, text)
        return act.perform()
    except Exception as e:
        logger.error(f"Error in action_router: {e}")
        return "Action routing failed due to an error."
