from logger import logger
import os
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
    """환경 변수 초기화"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise KeyError("환경 변수 오류: OPENAI_API_KEY가 설정되지 않았습니다.")
        print(f"✅ OPENAI_API_KEY: {api_key}")
    except KeyError as e:
        logger.write(f"⚠️ {e}\n")
        print(e)
        exit(1)

def wake_word(sensitivity=0.8):
    """키워드 감지를 위한 wake word 함수"""
    keywords = ["computer", "jarvis"]
    sensitivities = [sensitivity] * len(keywords)

    try:
        print("wake_word1")
        porcupine = pvporcupine.create(
            keywords=keywords,
            access_key=os.getenv("PV_ACCESS_KEY"),
            sensitivities=sensitivities
        )
        print("wake_word2")

        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        os.close(devnull)

        print("wake_word3")
        wake_pa = pyaudio.PyAudio()
        device_rate = 44100
        frames_to_read = int(porcupine.frame_length * device_rate / porcupine.sample_rate)

        # wav 파일 설정
        wav_file = wave.open("recorded_audio.wav", "wb")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(wake_pa.get_sample_size(pyaudio.paInt16))
        wav_file.setframerate(device_rate)

        porcupine_audio_stream = wake_pa.open(
            rate=device_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=frames_to_read
        )

        Detect = True
        print(f"Detect: {Detect}")

        while Detect:
            try:
                raw_audio_data = porcupine_audio_stream.read(frames_to_read, exception_on_overflow=False)
                wav_file.writeframes(raw_audio_data)
                audio_data = struct.unpack_from("h" * frames_to_read, raw_audio_data)
                audio_data = np.array(audio_data)
                resampled_data = resample(audio_data, porcupine.frame_length)
                resampled_data = resampled_data.astype(np.int16)
                porcupine_pcm = tuple(resampled_data)
            except Exception as e:
                logger.write(f"⚠️ Audio stream error: {e}\n")
                print(f"Audio stream error: {e}")
                continue

            porcupine_keyword_index = porcupine.process(porcupine_pcm)

            if porcupine_keyword_index >= 0:
                keyword = keywords[porcupine_keyword_index]
                Detect = False

    except Exception as e:
        logger.write(f"⛔ Error in wake_word function: {e}\n")
        print(f"Error in wake_word function: {e}")

    finally:
        try:
            porcupine_audio_stream.stop_stream()
            porcupine_audio_stream.close()
            porcupine.delete()
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
            wav_file.close()
            wake_pa.terminate()
        except Exception as e:
            logger.write(f"⛔ wake_word 종료 중 오류 발생: {e}\n")
            print(f"wake_word 종료 중 오류 발생: {e}")

def speak_response():
    """음성 출력 함수"""
    try:
        mixer.init()
        settings = load_settings()
        if not settings:
            raise FileNotFoundError("⚠️ 설정 파일(settings.json) 불러오기 실패.")

        response_wave = "../res/" + settings["response_wave"]
        mixer.music.load(response_wave)  # WAV 파일 로드
        mixer.music.play()
        print("speak")
    except FileNotFoundError as e:
        logger.write(f"⚠️ 음성 파일 로드 실패: {e}\n")
        print(e)
    except pygame.error as e:
        logger.write(f"⚠️ pygame 오류 발생: {e}\n")
        print("음성을 재생할 수 없습니다.")
    except Exception as e:
        logger.write(f"⛔ 음성 출력 중 오류 발생: {e}\n")
        print("음성 출력 중 오류가 발생했습니다.")
