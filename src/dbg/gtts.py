from gtts import gTTS
import pygame.mixer as mixer
from io import BytesIO
from pydub import AudioSegment

text = "네!"

SPEED = 1.5
mp3_fp = BytesIO()
tts = gTTS(text, lang='ko')
tts.write_to_fp(mp3_fp)

mixer.init()
mp3_fp.seek(0)
audio = AudioSegment.from_file(mp3_fp, format="mp3")
adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * SPEED)}).set_frame_rate(audio.frame_rate)

adjusted_audio.export("temp_output.wav", format="wav")

mixer.music.load("temp_output.wav")
mixer.music.play()

while mixer.music.get_busy():
    continue
