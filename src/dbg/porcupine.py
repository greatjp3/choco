import pvporcupine
import pyaudio
import struct
import os
import wave
import numpy as np
from scipy.signal import resample

import pvporcupine
import pyaudio
import struct
import os
from dotenv import load_dotenv

load_dotenv()

# Picovoice 액세스 키 설정 (Picovoice 계정에서 발급받아야 함)
ACCESS_KEY = os.getenv("PV_ACCESS_KEY")  # 또는 "your_access_key_here"
PPN_PATH = "your_wake_word.ppn"

def test_pvporcupine():
    """pvporcupine Wake Word 감지 테스트"""
    try:
        # 감지할 키워드 목록
        keywords = ["computer", "jarvis"]

        # Porcupine 인스턴스 생성
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keywords=keywords,
            keyword_paths=[PPN_PATH]
        )

        # PyAudio 스트림 설정
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        print("🎤 Wake Word 감지 대기 중... (Ctrl+C로 종료)")

        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                print(f"🔊 Wake Word 감지됨: {keywords[keyword_index]}!")

    except KeyboardInterrupt:
        print("\n프로그램 종료")
    
    except Exception as e:
        print(f"🚨 오류 발생: {e}")
    
    finally:
        # 자원 정리
        if 'audio_stream' in locals():
            audio_stream.stop_stream()
            audio_stream.close()
        if 'pa' in locals():
            pa.terminate()
        if 'porcupine' in locals():
            porcupine.delete()

def wake_word_org(sensitivity=0.5):
    """키워드 감지를 위한 wake word 함수"""
    keywords = ["computer", "jarvis"]
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

if __name__ == "__main__":
    wake_word_org()

