import json
import wave
import numpy as np
from scipy.signal import resample
import pygame.mixer as mixer
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
log_file_path = SOURCE_DIR / "log/events.log"

def load_settings():
    settings_path = SOURCE_DIR / "settings.json"
    with open(settings_path, "r") as f:
        settings = json.load(f)
        return settings

def initialize_system():
    a=1

def wake_word(sensitivity=0.8):
    keywords = ["computer", "jarvis"]
    sensitivities = [sensitivity] * len(keywords)

    try:
        print("wake_word1")
        porcupine = pvporcupine.create(
            keywords=keywords,
            access_key=pv_access_key,
            sensitivities=sensitivities
        )
        print("wake_word2")
        # ALSA 에러 출력을 무시하기 위한 설정
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        os.close(devnull)
        print("wake_word3")
        wake_pa = pyaudio.PyAudio()
        # 오디오 장치의 기본 샘플 레이트 (예: 44100 Hz)
        device_rate = 44100
        # porcupine이 요구하는 프레임 길이에 맞게 읽어야 하는 샘플 수 계산
        frames_to_read = int(porcupine.frame_length * device_rate / porcupine.sample_rate)

        # wav 파일 설정 (원본 오디오 데이터를 저장)
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
                # 원본 오디오 데이터를 읽음 (44100 Hz)
                raw_audio_data = porcupine_audio_stream.read(frames_to_read, exception_on_overflow=False)
                # 동시에 wav 파일에 기록
                wav_file.writeframes(raw_audio_data)
                # Porcupine 처리를 위해 데이터 변환
                audio_data = struct.unpack_from("h" * frames_to_read, raw_audio_data)
                audio_data = np.array(audio_data)
                # 44100 Hz 데이터를 16000 Hz (porcupine.sample_rate)로 리샘플링
                resampled_data = resample(audio_data, porcupine.frame_length)
                resampled_data = resampled_data.astype(np.int16)
                porcupine_pcm = tuple(resampled_data)
            except Exception as e:
                print(f"Audio stream error: {e}")
                continue

            porcupine_keyword_index = porcupine.process(porcupine_pcm)

            if porcupine_keyword_index >= 0:
                keyword = keywords[porcupine_keyword_index]
                Detect = False

    except Exception as e:
        print(f"Error in wake_word function: {e}")

    finally:
        porcupine_audio_stream.stop_stream()
        porcupine_audio_stream.close()
        porcupine.delete()
        os.dup2(old_stderr, 2)
        os.close(old_stderr)
        wav_file.close()  # wav 파일 닫기
        wake_pa.terminate()

def speak_response():
    mixer.init()
    with open("settings.json", "r") as f:
        response_wave = "../res/" + json.load(f)["response_wave"]
    mixer.music.load(response_wave)  # WAV 파일 로드
    mixer.music.play()
    print("speak")
