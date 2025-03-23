import os
import sys
import time
from actions import *

test_word=["1분 후에 알람 해 줘",
           "알람 삭제",
           "1시간 10분 후에 알람 해 줘",
           "50분 후에 알람 해줘",
           "1시간 2분 후에 알람 해 줘",
           "알람 삭제",
           "9시에 알람해줘"
           ]

def main():
    for text in test_word:
        print(text)
        try:
            response = alarm_reminder_action(text)
        except:
            print("except")

        print(response)
        time.sleep(5)  # 3초간 정지

if __name__ == "__main__":
    main()
