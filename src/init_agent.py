import re
import os
import subprocess
from logger import logger

def init_action(text: str):
    """
    사용자 입력에서 재부팅 관련 명령을 감지하여 Raspberry Pi를 재부팅합니다.
    """
    text = text.strip().lower()

    reboot_match = re.search(r"(리부팅|재부팅|초기화|껐다\s*켜줘|다시\s*켜줘|꺼\s*다\s*켜|재시작)", text)
    
    if reboot_match:
        logger.info(f"🔁 재부팅 명령 감지됨: '{text}' → 시스템 재부팅 실행")
        try:
            # 안전한 재부팅 명령 (비동기)
            subprocess.Popen(["sudo", "reboot"])
            return True, "init", "시스템을 재부팅합니다."
        except Exception as e:
            logger.error(f"재부팅 중 오류 발생: {str(e)}")
            return True, "init", f"재부팅 실패: {str(e)}"
    else:
        return False, "init", None
