import traceback
import logging
import litellm
from common import *
from litellm import completion

logger = logging.getLogger(__name__)

def llm_action(text, retries=3):
    # Load settings from settings.json
    settings = load_settings()
    base_max_tokens = settings.get("max_tokens", 256)
    temperature = settings.get("temperature", 0.7)
    model = settings.get("model", "gpt-4-turbo")
    custom_instructions = settings.get("custom_instructions", "")

    # 🧠 길이 조정 키워드 기준 분석
    long_keywords = ["길게", "자세하게", "더 자세히", "길고"]
    short_keywords = ["짧게", "간단히", "간략히", "간단한", "짧은"]

    # 기본값 기준으로 길이 조절
    max_tokens = base_max_tokens
    if any(word in text for word in long_keywords):
        max_tokens = base_max_tokens * 2
    elif any(word in text for word in short_keywords):
        max_tokens = max(base_max_tokens // 2, 64)  # 너무 작아지지 않도록 하한선 설정

    messages = [
        {"role": "system", "content": f"You are a helpful assistant. {custom_instructions}"},
        {"role": "user", "content": f"Human: {text}\nAI:"}
    ]

    for i in range(retries):
        try:
            response = completion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            response_content = response.choices[0].message.content.strip()
            if response_content:
                return True, "llm", response_content
            else:
                logger.warning(f"[Retry {i+1}] Empty response from LLM.")
        except litellm.exceptions.BadRequestError:
            logger.error(traceback.format_exc())
            return (False, "llm", 
                f"The API key you provided for `{model}` is not valid.\n"
                "Double check the API key corresponds to the model/provider you are trying to call."
            )
        except Exception as e:
            logger.error(f"[Retry {i+1}] Unexpected error: {e}")
            logger.debug(traceback.format_exc())
            if i == retries - 1:
                return False, "llm", f"Something went wrong after {retries} retries: {e}\n{traceback.format_exc()}"

