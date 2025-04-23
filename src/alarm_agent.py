import os
import re
import subprocess
import signal
from threading import Timer
from datetime import datetime, timedelta
from logger import logger

alarms = {}
running_processes = {}
alarm_status = {}  # 전역

class Alarm:
    def __init__(self, time, timer):
        self.time = time
        self.timer = timer

    def cancel(self):
        self.timer.cancel()

def parse_time_expression(text, time_expression):
    # 오전/오후 처리
    is_pm = False
    is_am = False

    if '오후' in time_expression:
        is_pm = True
        time_expression = time_expression.replace('오후', '')
    elif '오전' in time_expression:
        is_am = True
        time_expression = time_expression.replace('오전', '')

    time_expression = time_expression.strip()
    now = datetime.now()

    if re.search(r'(\d+\s*시간|\d+\s*분)', time_expression) and ( re.search(r'(후|뒤)', text) or re.search(r'(타이머)', text)):
        hour_match = re.search(r'(\d+)\s*시간', time_expression)
        minute_match = re.search(r'(\d+)\s*분', time_expression)

        if not hour_match and not minute_match:
            raise ValueError("올바르지 않은 시간 표현입니다.")

        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0

        alarm_time = now + timedelta(hours=hours, minutes=minutes)
        return alarm_time, hours, minutes

    elif re.search(r'(\d+\s*시|\d+\s*분)', time_expression):
        hour_match = re.search(r'(\d+)\s*시', time_expression)
        minute_match = re.search(r'(\d+)\s*분', time_expression)

        if not hour_match and not minute_match:
            raise ValueError("올바르지 않은 시간 표현입니다.")

        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0
 
        # 오전/오후 반영
        if is_pm and hours < 12:
            hours += 12
        elif is_am and hours == 12:
            hours = 0
        else:
            if now.hour>12 and hours <12:
                hours += 12

        alarm_time = now.replace(hour=hours, minute=minutes)
        if alarm_time < now:
            alarm_time += timedelta(days=1)
        else:
            alarm_time = now.replace(minute=minutes, hour=hours, second=0, microsecond=0)
            
        return alarm_time, 0, 0

    else:
        raise ValueError("올바르지 않은 시간 표현입니다.")

def set_alarm(command, alarm_time, hour, minute, comment):
    now = datetime.now()
    unique_comment = f"{comment}_{alarm_time.strftime('%H%M')}"

    def run_command():
        proc = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)  # 새로운 세션 id로 실행
        running_processes[unique_comment] = proc
        alarm_status[unique_comment] = "running"
        
    delay = (alarm_time - now).total_seconds()
    timer = Timer(delay, run_command)  # pass the function itself, not the result of its call
    timer.start()

    alarms[unique_comment] = Alarm(alarm_time, timer)

    if alarm_time.hour > 12:
        diff_hour = alarm_time.hour - 12
    else:
        diff_hour = alarm_time.hour

    if alarm_time.day - now.day > 0:
        diff_hour = f"내일 {diff_hour}"
    else:
        diff_hour = f"{diff_hour}"

    if hour > 0 and minute > 0:
        response = f"{hour}시간 {minute}분 후인 {diff_hour}시 {alarm_time.minute}분에 알람을 울릴께요."
    elif hour > 0 and minute==0:
        response = f"{hour}시간 후인 {diff_hour}시 {alarm_time.minute}분에 알람을 울릴께요."
    elif hour == 0 and minute>0:
        response = f"{minute}분 후인 {diff_hour}시 {alarm_time.minute}분에 알람을 울릴께요."
    else:
        response = f"{diff_hour}시 {alarm_time.minute}분에 알람을 울릴께요."

    return True, "alarm", response

def delete_alarm(comment):
    def to_12_hour_format(hour):
        return hour - 12 if hour > 12 else hour

    if comment in alarms:
        alarm = alarms[comment]
        alarm.cancel()
        hour_12 = to_12_hour_format(alarm.time.hour)
        time_str = f"{hour_12}시 {alarm.time.minute}분"
        del alarms[comment]
        return True, "alarm", f"{time_str} 알람을 삭제했어요."
    else:
        if alarms:
            closest_comment = min(alarms, key=lambda k: alarms[k].time)
            alarm = alarms[closest_comment]
            alarm.cancel()
            hour_12 = to_12_hour_format(alarm.time.hour)
            time_str = f"{hour_12}시 {alarm.time.minute}분"
            del alarms[closest_comment]
            return True, "alarm", f"{time_str} 알람을 삭제했어요."
        else:
            return True, "alarm", "삭제할 알람이 없어요."

def stop_alarm():
    if not running_processes:
        return True, "alarm", "종료할 알람이 없어요."

    sorted_comments = sorted(running_processes.keys())
    oldest_comment = sorted_comments[0]
    proc = running_processes[oldest_comment]

    try:
        os.killpg(proc.pid, signal.SIGTERM)  # 프로세스 그룹 전체 종료
    except Exception as e:
        return True, "alarm", f"[{oldest_comment}] 알람 종료에 실패했어요."

    del running_processes[oldest_comment]
    return True, "alarm", f"끔"

def alarm_action(text):
    set_match = re.search(
        r'(?:'  # 시간 먼저 오는 패턴
            r'(?:(?P<meridiem1>오전|오후)?\s*)?'
            r'(?P<time1>'
                r'(?:\d+\s*시간\s*\d+\s*분|\d+\s*시간|\d+\s*분)'
                r'|\d{1,2}\s*시\s*\d+\s*분'
                r'|\d{1,2}\s*시'
                r'|\d{1,2}:\d{2}'
            r')'
            r'(?:\s*(?:에|에서|후에|뒤에|안에|있다))?'
            r'\s*(?:알람|타이머|일정|깨워줘|깨워|일어나게)?'
            r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?'
        r')'
        r'|(?:'
            r'(?:알람|타이머|일정|깨워줘|깨워|일어나게)'
            r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?\s*'
            r'(?:(?P<meridiem2>오전|오후)?\s*)?'
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

    delete_match = re.search(
        r'(?:알람|타이머)\s*(\w+)?\s*(?:삭제|제거|취소)\b'
        r'|(?:삭제|제거|취소)\s*(\w+)?\s*(?:알람|타이머)\b',
        text,
        re.IGNORECASE
    )
    stop_match = re.search(
        r'(?:알람|타이머)\s*(\w+)?\s*(?:꺼줘|꺼)\b'
        r'|(?:꺼줘|꺼)\s*(\w+)?\s*(?:알람|타이머)\b',
        text,
        re.IGNORECASE
    )
    if delete_match:
        comment = delete_match.group(1) or delete_match.group(2)
        return delete_alarm(comment)
    elif stop_match:
        return stop_alarm()
    elif set_match:
        time_expression = set_match.group("time1") or set_match.group("time2")
        meridiem = set_match.group("meridiem1") or set_match.group("meridiem2")

        if meridiem:
            time_expression = meridiem + " " + time_expression

        if time_expression:
            try:
                alarm_time, hour, minute = parse_time_expression(text, time_expression)
                command = "play ../res/alarm.wav vol 0.5"
                comment = "Alarm"
                return set_alarm(command, alarm_time, hour, minute, comment)
            except Exception as e:
                return True, "alarm", f" 시간 파싱 오류: {str(e)}"
    else:
        return True, "alarm", "시간 표현을 이해하지 못했어요."

def is_alarm_running(comment):
    return alarm_status.get(comment) == "running"

def is_any_alarm_running():
    return bool(running_processes)