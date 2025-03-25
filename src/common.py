from logger import logger
import os
import sys
import json
import wave
import struct
import numpy as np
import time
import threading
import pyaudio
import pygame.mixer as mixer
from pathlib import Path
from scipy.signal import resample
import pvporcupine
import speech_recognition as sr

try:
    from gtts import gTTS
except:
    print(f"gTTS import exception\n")

from io import BytesIO
from pydub import AudioSegment
from pydub.playback import play
from concurrent.futures import ThreadPoolExecutor
import pygame
import tempfile

SOURCE_DIR = Path(__file__).parent
log_file_path = SOURCE_DIR / "log/events.log"

def load_settings():
    """설정 파일 로드 함수"""
    settings_path = SOURCE_DIR / "settings.json"
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
            return settings
    except FileNotFoundError:
        logger.write("⚠️ 설정 파일(settings.json)을 찾을 수 없습니다.\n")
        return None
    except json.JSONDecodeError:
        logger.write("⚠️ 설정 파일 형식 오류 (JSONDecodeError)\n")
        return None
    except Exception as e:
        logger.write(f"⛔ 설정 파일 로드 중 오류 발생: {e}\n")
        return None

def initialize_system():
    return None

def wake_word(sensitivity=1.0):
    """키워드 감지를 위한 wake word 함수"""
    with open("settings.json", "r") as f:
        settings = json.load(f)
        custom_keyword = settings["keyword"]

    keywords = ["computer", "jarvis"]
    if custom_keyword is not None:
        if custom_keyword != "":
            keywords.append(custom_keyword)
    print(keywords)

    sensitivities = [sensitivity] * len(keywords)

    try:
        # 환경 변수에서 액세스 키 가져오기 (설정되지 않으면 예외 발생)
        pv_access_key = os.getenv("PV_ACCESS_KEY")
        if not pv_access_key:
            raise KeyError("🚨 환경 변수 오류: PV_ACCESS_KEY가 설정되지 않았습니다.")

        porcupine = pvporcupine.create(
            keywords=keywords,
            access_key=pv_access_key,
            sensitivities=sensitivities
        )

        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        os.close(devnull)

        wake_pa = pyaudio.PyAudio()
        try:
            device_rate = 44100
            frames_to_read = int(porcupine.frame_length * device_rate / porcupine.sample_rate)

            # 마이크 입력 스트림 설정
            porcupine_audio_stream = wake_pa.open(
                rate=device_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=frames_to_read
            )

        except Exception as e:
            raise RuntimeError(f"🚨 오디오 장치 초기화 실패: {e}")

        Detect = True

        print("ready~")
        while Detect:
            try:
                # 마이크에서 오디오 데이터 읽기
                raw_audio_data = porcupine_audio_stream.read(frames_to_read, exception_on_overflow=False)

                # 데이터 변환 (byte → numpy 배열 → 16-bit PCM)
                audio_data = struct.unpack_from("h" * frames_to_read, raw_audio_data)
                audio_data = np.array(audio_data)

                # 샘플링 속도 변환 (44100Hz → 16000Hz)
                resampled_data = resample(audio_data, porcupine.frame_length)
                resampled_data = resampled_data.astype(np.int16).tolist()

                # Wake Word 감지
                porcupine_keyword_index = porcupine.process(resampled_data)

                if porcupine_keyword_index >= 0:
                    keyword = keywords[porcupine_keyword_index]
                    logger.info(f"🔊 Wake Word 감지됨: {keyword}!")
                    Detect = False

            except Exception as e:
                logger.error(f"⚠️ Audio stream error: {e}")
                continue

    except KeyError as e:
        logger.error(f"⛔ 환경 변수 오류: {e}\n")

    except RuntimeError as e:
        logger.error(f"⛔ 시스템 오류 발생: {e}\n")

    except Exception as e:
        logger.error(f"⛔ Wake Word 감지 중 예기치 않은 오류 발생: {e}\n")

    finally:
        os.dup2(old_stderr, 2)  # stderr을 원래 상태로 복구
        os.close(old_stderr)  # 기존 stderr 닫기

def speak_ack():
    """음성 출력 함수"""
    try:
        mixer.init()
        settings = load_settings()
        if not settings:
            raise FileNotFoundError("⚠️ 설정 파일(settings.json) 불러오기 실패.")

        response_wave = "../res/" + settings["response_wave"]
        mixer.music.load(response_wave)  # WAV 파일 로드
        mixer.music.play()
    except FileNotFoundError as e:
        logger.write(f"⚠️ 음성 파일 로드 실패: {e}\n")
        print(e)
    except pygame.error as e:
        logger.write(f"⚠️ pygame 오류 발생: {e}\n")
        print("음성을 재생할 수 없습니다.")
    except Exception as e:
        logger.write(f"⛔ 음성 출력 중 오류 발생: {e}\n")
        print("음성 출력 중 오류가 발생했습니다.")

# Recognizer 객체 생성
r = sr.Recognizer()

def test(sensitivity=0.5):
    """키워드 감지를 위한 wake word 함수"""
    with open("settings.json", "r") as f:
        settings = json.load(f)
        custom_keyword = settings["keyword"]

    keywords = ["computer", "jarvis"]
    if custom_keyword is not None:
        if custom_keyword != "":
            keywords.append(custom_keyword)
    print(keywords)

    sensitivities = [sensitivity] * len(keywords)

    try:
        # 환경 변수에서 액세스 키 가져오기 (설정되지 않으면 예외 발생)
        pv_access_key = os.getenv("PV_ACCESS_KEY")
        if not pv_access_key:
            raise KeyError("🚨 환경 변수 오류: PV_ACCESS_KEY가 설정되지 않았습니다.")

        porcupine = pvporcupine.create(
            keywords=keywords,
            access_key=pv_access_key,
            sensitivities=sensitivities
        )

        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        os.close(devnull)

        wake_pa = pyaudio.PyAudio()
        try:
            device_rate = 44100
            frames_to_read = int(porcupine.frame_length * device_rate / porcupine.sample_rate)

            # 마이크 입력 스트림 설정
            porcupine_audio_stream = wake_pa.open(
                rate=device_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=frames_to_read
            )

        except Exception as e:
            print("exception")

    except KeyError as e:
        logger.error(f"⛔ 환경 변수 오류: {e}\n")

    except RuntimeError as e:
        logger.error(f"⛔ 시스템 오류 발생: {e}\n")

    except Exception as e:
        logger.error(f"⛔ Wake Word 감지 중 예기치 않은 오류 발생: {e}\n")

    finally:
        os.dup2(old_stderr, 2)  # stderr을 원래 상태로 복구
        os.close(old_stderr)  # 기존 stderr 닫기

    with sr.Microphone(sample_rate=44100, device_index=2) as source:
        return None
    
def recognize_audio():
    """ 마이크 입력을 받아 음성을 인식하는 함수 """
    try:
        with sr.Microphone(sample_rate=44100, device_index=2) as source:
            # 마이크가 정상적으로 초기화되었는지 확인
            if source.stream is None:
                raise Exception("Microphone not initialized.")

            # 잡음 줄이기
            r.adjust_for_ambient_noise(source, duration=1)

            listening = False  # 피드백 플래그
            try:
                print("🎤 Waiting for input...")
                audio = r.listen(source, timeout=2, phrase_time_limit=10)
                text = r.recognize_google(audio, language="ko-KR")

                if text:
                    return text

            except sr.WaitTimeoutError:
                if listening:
                    logger.info("⌛ Still listening, but timed out. Waiting for a new phrase...")
                else:
                    logger.info("⏳ Timed out, waiting for phrase to start...")
                    listening = True

            except sr.UnknownValueError:
                logger.info("🤷 Could not understand audio. Please try again...")
                listening = False

            except sr.RequestError as e:
                logger.error(f"🌐 API error: {e}")
                return None

    except OSError as e:
        logger.error(f"🔊 Microphone access error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

    return None

SPEED = 1.3  # 음성 속도 조절

async def speak(text: str):
    """음성을 출력하는 함수 (gTTS + Pygame 사용)"""
    def _speak():
        try:
            # 🔹 1. gTTS로 음성 변환
            try:
                mp3_fp = BytesIO()
                tts = gTTS(text, lang='ko')
                tts.write_to_fp(mp3_fp)
                print("mp3")
            except Exception as e:
                logger.error(f"⛔ gTTS 변환 오류: {e}")
                return
            
            # 🔹 2. Pygame 믹서 초기화
            try:
                mixer.init()
            except pygame_error as e:
                logger.error(f"⛔ Pygame 믹서 초기화 오류: {e}")
                return

            mp3_fp.seek(0)

            # 🔹 3. mp3 데이터를 Pydub로 변환
            try:
                audio = AudioSegment.from_file(mp3_fp, format="mp3")
            except CouldntDecodeError:
                logger.error("⛔ MP3 파일 디코딩 오류. 올바른 오디오 데이터를 사용하세요.")
                return

            # 🔹 4. 속도 조정 후 mp3로 저장
            try:
                adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * SPEED)}).set_frame_rate(audio.frame_rate)
                output_path = "temp_output.mp3"
                adjusted_audio.export(output_path, format="mp3")
            except Exception as e:
                logger.error(f"⛔ 오디오 처리 오류: {e}")
                return

            # 🔹 5. MP3 재생
            try:
                mixer.music.load(output_path)
                mixer.music.play()
            except pygame_error as e:
                logger.error(f"⛔ MP3 로드 및 재생 오류: {e}")
                return

            # 🔹 6. 음악 재생 종료까지 대기
            event = threading.Event()
            while mixer.music.get_busy():
                event.wait(0.1)  # CPU 부하 방지

        except Exception as e:
            logger.error(f"⛔ 알 수 없는 오류 발생: {e}")
        finally:
            # 🔹 7. 리소스 정리
            if mixer.get_init():
                mixer.quit()
            if os.path.exists("temp_output.mp3"):
                os.remove("temp_output.mp3")  # 임시 파일 삭제
    
    await loop.run_in_executor(executor, _speak)
    stop_event.set()

def change_speed(sound, speed=1.3):
    """오디오의 재생 속도를 변경 (speed=1.0 기본, 1.5는 1.5배 빠름, 0.5는 절반 속도)"""
    new_frame_rate = int(sound.frame_rate * speed)
    return sound._spawn(sound.raw_data, overrides={'frame_rate': new_frame_rate}).set_frame_rate(44100)

def text_to_speech(text, speed=1.3):
    """TTS 생성 후 지정된 속도로 재생"""
    tts = gTTS(text, lang='ko')

    # 임시 파일 생성 후 gTTS 결과 저장
    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)  # gTTS 음성을 임시 파일에 저장
        temp_audio.seek(0)  # 파일 포인터 초기화

        # pydub을 이용하여 mp3 불러오기
        sound = AudioSegment.from_file(temp_audio.name, format="mp3")

        # 속도 조절 적용
        modified_sound = change_speed(sound, speed)

        # 변환된 오디오 재생
        play(modified_sound)