import os
import sys
import time
import re
from actions import *

test_word=["8시 알람",
           "9시에 알람해줘",
           "6시 30분에 알람",
           "1분 후에 알람 해 줘",
           "알람 취소",
           "3분 있다 알람 해 줘",
           "알람 삭제",
           "1시간 10분 후에 알람 해 줘",
           "50분 후에 알람 해줘",
           "1시간 2분 후에 알람 해 줘",
           "알람 삭제"
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

def reg_test():
    for text in test_word:
        set_match = re.search(
            r'(?:'  # 시간 먼저 오는 패턴
                r'(?P<time1>'
                    r'(?:\d+\s*시간\s*\d+\s*분|\d+\s*시간|\d+\s*분)'  # '1시간 10분' or '1시간' or '10분'
                    r'|\d{1,2}\s*시\s*\d+\s*분'                     # '6시 30분'
                    r'|\d{1,2}\s*시'                               # '8시'
                    r'|\d{1,2}:\d{2}'                              # '6:30'
                r')'
                r'(?:\s*(?:에|에서|후에|뒤에|안에|있다))?'            # 조사
                r'\s*'
                r'(?:알람|타이머|일정|깨워줘|깨워|일어나게)?'
                r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?'
            r')'
            r'|(?:'  # 알람 먼저 오는 패턴
                r'(?:알람|타이머|일정|깨워줘|깨워|일어나게)'
                r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?\s*'
                r'(?P<time2>'
                    r'(?:\d+\s*시간\s*\d+\s*분|\d+\s*시간|\d+\s*분)'
                    r'|\d{1,2}\s*시\s*\d+\s*분'
                    r'|\d{1,2}\s*시'
                    r'|\d{1,2}:\d{2}'
                r')'
                r'(?:\s*(?:에|에서|후에|뒤에|안에|있다))?'
            r')',
            text,
            re.IGNORECASE
            )
        print(text)
        if set_match:
            if set_match.group(1) is not None:
                print(f"group1:{set_match.group(1)}")
            if set_match.group(2) is not None:
                print(f"group2:{set_match.group(2)}")
            time_expression = set_match.group(1) or set_match.group(2)
            print(f"time_expression: {time_expression}")
        else:
            print("not set match")

if __name__ == "__main__":
    main()
    # reg_test()