from semantic_router.layer import RouteLayer
import semantic_router.encoders as encoders
from semantic_router import Route

from actions import *

API_KEY = ""

def refresh_api_key():
    with open("settings.json", "r") as f:
        API_KEY = json.load(f)["openai_api_key"]
    os.environ["OPENAI_API_KEY"] = API_KEY

refresh_api_key()

encoder = encoders.OpenAIEncoder(
    name="text-embedding-3-large", score_threshold=0.5, dimensions=256
)

# Define routes
alarm_route = Route(
    name="alarm_reminder_action",
    utterances=[
        "알람 설정해줘",
        "나 깨워줘",
        "몇 분 후에 알려줘"
    ]
)

spotify_route = Route(
    name="spotify_action",
    utterances=[
        "play some music",
        "next song",
        "pause the music",
        "play earth wind and fire on Spotify",
        "play my playlist"
    ]
)

weather_route = Route(
    name="open_weather_action",
    utterances = [
        "오늘 날씨 어때?",
        "날씨 알려줘",
        "현재 기온이 몇 도야?",
        "비 올 예정이야?",
        "서울울의 날씨는 어때?"
    ]

)

lights_route = Route(
    name="philips_hue_action",
    utterances=[
        "turn on the lights",
        "switch off the lights",
        "dim the lights",
        "change the color of the lights",
        "set the lights to red"
    ]
)

calendar_route = Route(
    name="caldav_action",
    utterances = [
        "회의 일정 잡아줘",
        "내 일정에 뭐가 있어?",
        "이벤트 추가해줘",
        "오늘 남은 할 일이 뭐야?"
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

routes = [alarm_route, spotify_route, weather_route, lights_route, calendar_route, general_route]

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

    async def perform(self, **kwargs):
        try:
            action_func = globals()[self.action_name]
            logger.info(f"Performing action: {self.action_name} with text: {self.text}")
            return await action_func(self.text, **kwargs)
        except KeyError:
            logger.warning(f"Action {self.action_name} not found. Falling back to llm_action.")
            action_func = globals()["llm_action"]
            return await action_func(self.text, **kwargs)
        except Exception as e:
            logger.error(f"Error performing action {self.action_name}: {e}")
            return "Action failed due to an error."

async def action_router(text: str, router=ActionRouter()):
    refresh_api_key()
    try:
        action_name = router.resolve(text)
        act = Action(action_name, text)
        return await act.perform()
    except Exception as e:
        logger.error(f"Error in action_router: {e}")
        return "Action routing failed due to an error."
