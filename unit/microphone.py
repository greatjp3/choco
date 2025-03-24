import speech_recognition as sr
import wave

print("사용 가능한 마이크 목록:")
for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"{index}: {name}")

def record_audio(filename="output.wav", duration=5, sample_rate=44100):
    recognizer = sr.Recognizer()

    with sr.Microphone(sample_rate=sample_rate, device_index=2) as source:
        print("🎤 녹음 시작... {}초 동안 말하세요.".format(duration))
        
        recognizer.adjust_for_ambient_noise(source, duration=1)  # 배경 소음 조정
        audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)  # 음성 녹음
        
        print("🎤 녹음 완료. 파일 저장 중...")

    # 녹음한 오디오를 WAV 파일로 저장
    with wave.open(filename, "wb") as f:
        f.setnchannels(1)  # 모노 채널
        f.setsampwidth(2)  # 16-bit 샘플링
        f.setframerate(sample_rate)  # 샘플링 레이트 설정
        f.writeframes(audio.get_wav_data())  # 녹음한 데이터 저장

    print(f"✅ 녹음 완료! 파일이 저장됨: {filename}")

# 실행: 5초 동안 녹음 후 output.wav로 저장
record_audio("output.wav", duration=5)
