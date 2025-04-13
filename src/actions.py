import traceback
import logging
import litellm
from common import *
from litellm import completion

logger = logging.getLogger(__name__)

def llm_action(text, retries=3):
    # Load settings from settings.json
    settings = load_settings()
    max_tokens = settings.get("max_tokens", 256)
    temperature = settings.get("temperature", 0.7)
    model = settings.get("model", "gpt-3.5-turbo")
    custom_instructions = settings.get("custom_instructions", "")

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
                return response_content
            else:
                logger.warning(f"[Retry {i+1}] Empty response from LLM.")
        except litellm.exceptions.BadRequestError:
            logger.error(traceback.format_exc())
            return (
                f"The API key you provided for `{model}` is not valid.\n"
                "Double check the API key corresponds to the model/provider you are trying to call."
            )
        except Exception as e:
            logger.error(f"[Retry {i+1}] Unexpected error: {e}")
            logger.debug(traceback.format_exc())
            if i == retries - 1:
                return f"Something went wrong after {retries} retries: {e}\n{traceback.format_exc()}"
