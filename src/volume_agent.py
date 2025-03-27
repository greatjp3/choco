
import subprocess
import re
import logging
import os
from pydub.playback import play
from common import load_settings
from common import save_settings

logger = logging.getLogger(__name__)

class Volume:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.levels = [0, 40, 60, 80, 100]
        self.current_volume = self.load_volume()

    def load_volume(self):
        try:
            settings = load_settings()
            if not settings:
                raise FileNotFoundError("⚠️ 설정 파일(settings.json) 불러오기 실패.")
            volume = settings["volume"]
        except:
            logger.error("settings.json(volume) load failed")
        return volume
    
    def save_volume(self, volume):
        try:
            settings = load_settings()
            if settings is None:
                settings = {}
            settings["volume"] = volume
            save_settings(settings)
        except Exception as e:
            logger.error(f"settings.json(volume) save failed: {e}")
            
    def get_default_sink(self):
        result = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True)
        return result.stdout.strip()

    def get_current_volume(self):
        try:
            sink = self.get_default_sink()
            result = subprocess.run(
                ["pactl", "get-sink-volume", sink],
                capture_output=True, text=True
            )
            match = re.search(r'/\s*(\d+)%', result.stdout)
            if match:
                vol = int(match.group(1))
                closest = min(self.levels, key=lambda x: abs(x - vol))
                return closest
        except Exception as e:
            self.logger.error(f"🔍 현재 볼륨 가져오기 실패: {e}")
        return 60  # 기본값

    def volume_speak(self, volume):
        file_name = f"../res/volume{volume}.wav"
        if os.path.exists(file_name):
            try:
                subprocess.run(["aplay", file_name], check=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"🔈 aplay 실패: {e}")
        else:
            self.logger.warning(f"🔇 오디오 파일이 존재하지 않음: {file_name}")

    def volume_control(self, volume):
        try:
            if not isinstance(volume, int) or not (0 <= volume <= 100):
                raise ValueError("볼륨 값은 0에서 100 사이의 정수여야 합니다.")

            sink = self.get_default_sink()
            subprocess.run(["pactl", "set-sink-volume", sink, f"{volume}%"], check=True)
            self.current_volume = volume
            self.logger.info(f"🔊 시스템 볼륨이 {volume}%로 설정되었습니다.")
            self.volume_speak(self.levels.index(volume))  # 리턴 전에 호출
            self.save_volume(volume)
        except Exception as e:
            self.logger.error(f"⛔ PulseAudio 볼륨 설정 실패: {e}")
        return None

    def volume_up(self):
        try:
            idx = self.levels.index(self.current_volume)
            if idx < len(self.levels) - 1:
                new_volume = self.levels[idx + 1]
                self.volume_control(new_volume)  # ✅ 볼륨 값 전달
                self.current_volume = new_volume
            else:
                new_volume = self.levels[idx]
                self.volume_control(new_volume)  # ✅ 볼륨 값 전달

        except ValueError:
            self.logger.error(f"현재 볼륨({self.current_volume})이 levels 목록에 없습니다.")
        return None

    def volume_down(self):
        try:
            idx = self.levels.index(self.current_volume)
            if idx > 0:
                new_volume = self.levels[idx - 1]
                self.volume_control(new_volume)  # ✅ 볼륨 값 전달
                self.current_volume = new_volume
        except ValueError:
            self.logger.error(f"현재 볼륨({self.current_volume})이 levels 목록에 없습니다.")
        return None

    def volume_max(self):
        new_volume = self.levels[-1]
        self.volume_control(new_volume)
        self.current_volume = new_volume
        return None

    def volume_min(self):
        new_volume = self.levels[0]
        self.volume_control(new_volume)
        self.current_volume = new_volume
        return None

v = Volume()

def volume_control_action(text):
    up_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*크게\b',
        text,
        re.IGNORECASE
    )
    down_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*작게\b',
        text,
        re.IGNORECASE
    )
    max_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*최대\b',
        text,
        re.IGNORECASE
    )
    min_match = re.search(
        r'(?:볼륨|소리)\s*(?:\w+)?\s*최소\b|조용히|음소거',
        text,
        re.IGNORECASE
    )

     # ✅ 명령 우선순위 정리: 삭제 → 중지 → 스누즈 → 리마인더 → 설정
    if up_match:
        return v.volume_up()
    elif down_match:
        return v.volume_down()
    elif max_match:
        return v.volume_max()
    elif min_match:
        return v.volume_min()
    else:
        return "아빠 도와줘요"
