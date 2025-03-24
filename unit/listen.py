import speech_recognition as sr

r = sr.Recognizer()

def recognize_audio():
    while True:
        print("waiting")
        try:
            with sr.Microphone(sample_rate=44100, device_index=2) as source:
                if source.stream is None:
                    raise Exception("Microphone not initialized.")
                
                listening = False  # Initialize variable for feedback
                
                try:
                    print("🎤 Waiting for input...")
                    audio = r.listen(source, timeout=2, phrase_time_limit=15)
                    text = r.recognize_google(audio, language="ko-KR")

                    print(text)
                        
                except sr.WaitTimeoutError:
                    if listening:
                        print("Still listening but timed out, waiting for phrase...")
                    else:
                        print("Timed out, waiting for phrase to start...")
                        listening = True
                        
                except sr.UnknownValueError:
                    print("Could not understand audio, waiting for a new phrase...")
                    listening = False
                        
        except sr.WaitTimeoutError:
            if source and source.stream:
                source.stream.close()

if __name__ == "__main__":
    recognize_audio()