from pydub import AudioSegment

def trim_wav(input_file, output_file, start_time, end_time):
    """
    WAV 파일의 특정 부분을 잘라서 저장하는 함수
    :param input_file: 원본 WAV 파일 경로
    :param output_file: 잘라낸 WAV 파일 저장 경로
    :param start_time: 시작 시간 (밀리초, 예: 5000은 5초)
    :param end_time: 종료 시간 (밀리초, 예: 10000은 10초)
    """
    audio = AudioSegment.from_wav(input_file)  # WAV 파일 불러오기
    trimmed_audio = audio[start_time:end_time]  # 부분 잘라내기
    trimmed_audio.export(output_file, format="wav")  # 새 파일로 저장

# 사용 예제: 5초~10초 부분을 잘라서 저장
trim_wav("yes_sir_org.wav", "yes_sir.wav", start_time=0, end_time=1000)
