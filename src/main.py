from common import *
from agent import *

def main_loop():
    speak_response()
    while True:
        # wake_word()
        #speak_response()
        response1 = agent.run("07:30 알람을 설정해줘.")
        print("응답 1:", response1)
    

if __name__ == "__main__":
    initialize_system()
    main_loop()

