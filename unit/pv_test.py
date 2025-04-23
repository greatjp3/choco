import pvporcupine
import os
from dotenv import load_dotenv

load_dotenv()

access_key = os.getenv("PV_ACCESS_KEY")

try:
    porcupine = pvporcupine.create(
        keywords=["porcupine"],  # ✅ 유효한 키워드만
        access_key=access_key,
        sensitivities=[0.6]
    )
    print("Wake word engine initialized!")
except pv_test.PorcupineActivationRefusedError:
    print("❌ 유효하지 않은 Access Key 또는 API 제한 초과")
except pv_test.PorcupineInvalidArgumentError:
    print("❌ 잘못된 키워드 또는 인자 전달")
except Exception as e:
    print("❌ 기타 오류:", e)
