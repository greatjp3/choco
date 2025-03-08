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
import pvporcupine
import speech_recognition as sr

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

pv_api_key = os.getenv("PV_ACCESS_KEY")        

def wake_word(sensitivity=0.5):
    """키워드 감지를 위한 wake word 함수"""
    with open("settings.json", "r") as f:
        settings = json.load(f)
        custom_keyword = settings["keyword"]
    print(custom_keyword)
    keywords = ["computer", "jarvis"]
    if custom_keyword != "":
        keywords.append(custom_keyword)
    print(keywords)

    sensitivities = [sensitivity] * len(keywords)

    try:
        # 환경 변수에서 액세스 키 가져오기 (설정되지 않으면 예외 발생)
        pv_access_key = os.getenv("PV_ACCESS_KEY")
        if not pv_access_key:
            raise KeyError("🚨 환경 변수 오류: PV_ACCESS_KEY가 설정되지 않았습니다.")

        print("🔄 wake_word 초기화 중...")
        porcupine = pvporcupine.create(
            keywords=keywords,
            access_key=pv_access_key,
            sensitivities=sensitivities
        )
        print("✅ wake_word 초기화 완료!")

        # 표준 오류 출력을 무시 (ALSA 관련 에러 무시 목적)
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        os.close(devnull)

        # 오디오 장치 초기화
        print("🔊 오디오 장치 초기화 중...")
        wake_pa = pyaudio.PyAudio()

        try:
            device_rate = 44100
            frames_to_read = int(porcupine.frame_length * device_rate / porcupine.sample_rate)

            # WAV 파일 생성
            wav_file = wave.open("recorded_audio.wav", "wb")
            wav_file.setnchannels(1)
            wav_file.setsampwidth(wake_pa.get_sample_size(pyaudio.paInt16))
            wav_file.setframerate(device_rate)

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

        print("🎤 Wake Word 감지 대기 중... (Ctrl+C로 종료)")
        Detect = True

        while Detect:
            try:
                # 마이크에서 오디오 데이터 읽기
                raw_audio_data = porcupine_audio_stream.read(frames_to_read, exception_on_overflow=False)
                wav_file.writeframes(raw_audio_data)  # WAV 파일에 기록

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
                    print(f"🔊 Wake Word 감지됨: {keyword}!")
                    Detect = False

            except Exception as e:
                print(f"⚠️ Audio stream error: {e}")
                continue

    except KeyError as e:
        logger.write(f"⛔ 환경 변수 오류: {e}\n")
        print(e)

    except RuntimeError as e:
        logger.write(f"⛔ 시스템 오류 발생: {e}\n")
        print(e)

    except Exception as e:
        logger.write(f"⛔ Wake Word 감지 중 예기치 않은 오류 발생: {e}\n")
        print(f"⛔ Wake Word 감지 중 예기치 않은 오류 발생: {e}")

    finally:
        print("🛑 시스템 종료 중...")
        try:
            if 'porcupine_audio_stream' in locals() and porcupine_audio_stream:
                porcupine_audio_stream.stop_stream()
                porcupine_audio_stream.close()
            
            if 'porcupine' in locals() and porcupine:
                porcupine.delete()

            if 'wake_pa' in locals() and wake_pa:
                wake_pa.terminate()

            if 'wav_file' in locals() and wav_file:
                wav_file.close()

            os.dup2(old_stderr, 2)
            os.close(old_stderr)

            print("✅ 정상적으로 종료되었습니다.")

        except Exception as e:
            logger.write(f"⛔ wake_word 종료 중 오류 발생: {e}\n")
            print(f"🚨 wake_word 종료 중 오류 발생: {e}")

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

r = sr.Recognizer()
def recognize_audio():
        print("waiting")
        try:
            with sr.Microphone(sample_rate=44100, device_index=2) as source:
                if source.stream is None:
                    raise Exception("Microphone not initialized.")
                
                listening = False  # Initialize variable for feedback
                
                try:
                    audio = r.listen(source, timeout=5, phrase_time_limit=15)
                    text = r.recognize_google(audio, language="ko-KR")

                    print(text)
                    if text:  # If text is found, break the loop
                        return text
                        
                except sr.WaitTimeoutError:
                    if listening:
                        logger.info("Still listening but timed out, waiting for phrase...")
                    else:
                        logger.info("Timed out, waiting for phrase to start...")
                        listening = True
                        
                except sr.UnknownValueError:
                    logger.info("Could not understand audio, waiting for a new phrase...")
                    listening = False
                        
        except sr.WaitTimeoutError:
            if source and source.stream:
                source.stream.close()

