import os
import re
import subprocess
import signal
from threading import Timer
from datetime import datetime, timedelta

alarms = {}
running_processes = {}

class Alarm:
    def __init__(self, time, timer):
        self.time = time
        self.timer = timer

    def cancel(self):
        self.timer.cancel()

def parse_time_expression(time_expression):
    if re.match(r'\d+:\d+', time_expression):  # HH:MM 형식
        hour, minute = map(int, time_expression.split(':'))
        return hour, minute, '*', '*', '*'

    elif re.search(r'(\d+\s*시간|\d+\s*분)', time_expression):  # "1시간 10분", "30분"
        hour_match = re.search(r'(\d+)\s*시간', time_expression)
        minute_match = re.search(r'(\d+)\s*분', time_expression)

        if not hour_match and not minute_match:
            raise ValueError("올바르지 않은 시간 표현입니다.")

        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(minute_match.group(1)) if minute_match else 0

        now = datetime.now()
        future = now + timedelta(hours=hours, minutes=minutes)
        return future.hour, future.minute, future.day, future.month, '*'

    elif re.search(r'\d+\s*시', time_expression) and not re.search(r'\d+\s*분', time_expression):  # "9시" 단일 시각만 처리
        hour = int(re.search(r'\d+', time_expression).group())
        minute = 0
        return hour, minute, '*', '*', '*'

    raise ValueError("올바르지 않은 시간 표현입니다.")

def set_alarm(command, minute, hour, day_of_month, month, day_of_week, comment):
    now = datetime.now()
    now = now.replace(second=0, microsecond=0)

    if day_of_month == '*' or month == '*':
        alarm_time = now.replace(hour=hour, minute=minute)
        if alarm_time < now:
            alarm_time += timedelta(days=1)
    else:
        alarm_time = now.replace(minute=minute, hour=hour, day=day_of_month, month=month, second=0, microsecond=0)
        if alarm_time < now:
            alarm_time += timedelta(days=1)

    unique_comment = f"{comment}_{alarm_time.strftime('%H%M')}"

    def run_command():
        proc = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)  # 새로운 세션 id로 실행
        running_processes[unique_comment] = proc
        
    delay = (alarm_time - now).total_seconds()
    timer = Timer(delay, run_command)  # pass the function itself, not the result of its call
    timer.start()

    alarms[unique_comment] = Alarm(alarm_time, timer)
    diff = alarm_time - now
    total_minutes = int(diff.total_seconds() // 60)
    diff_hours = total_minutes // 60
    diff_minutes = total_minutes % 60

    display_hour = hour - 12 if hour > 12 else hour

    if diff_hours > 0:
        if diff_minutes > 0:
            response = f"{diff_hours}시간 {diff_minutes}분 후인 {display_hour}시 {minute}분에 알람을 울릴께요."
        else:
            response = f"{diff_hours}시간 후인 {display_hour}시 {minute}분에 알람을 울릴께요."
    else:
        response = f"{diff_minutes}분 후인 {display_hour}시 {minute}분에 알람을 울릴께요."

    return response

def delete_alarm(comment):
    def to_12_hour_format(hour):
        return hour - 12 if hour > 12 else hour

    if comment in alarms:
        alarm = alarms[comment]
        alarm.cancel()
        hour_12 = to_12_hour_format(alarm.time.hour)
        time_str = f"{hour_12}시 {alarm.time.minute}분"
        del alarms[comment]
        return f"{time_str} 알람을 삭제했어요."
    else:
        if alarms:
            closest_comment = min(alarms, key=lambda k: alarms[k].time)
            alarm = alarms[closest_comment]
            alarm.cancel()
            hour_12 = to_12_hour_format(alarm.time.hour)
            time_str = f"{hour_12}시 {alarm.time.minute}분"
            del alarms[closest_comment]
            return f"{time_str} 알람을 삭제했어요."
        else:
            return "삭제할 알람이 없어요."

def snooze_alarm(comment, snooze_minutes):
    if comment in alarms:
        alarm = alarms[comment]
        alarm.cancel()
        del alarms[comment]

        now = datetime.now()
        snooze_time = now + timedelta(minutes=snooze_minutes)
        delay = (snooze_time - now).total_seconds()
        command = "aplay /usr/share/sounds/alarm.wav"
        timer = Timer(delay, lambda: subprocess.Popen(command, shell=True))
        timer.start()
        alarms[comment] = Alarm(snooze_time, timer)
        return f"[{comment}] {snooze_time.hour}시 {snooze_time.minute}분으로 스누즈 알람 설정했어요."
    else:
        return "해당 알람을 찾을 수 없어요."

def stop_alarm():
    if not running_processes:
        return "종료할 알람이 없어요."

    sorted_comments = sorted(running_processes.keys())
    oldest_comment = sorted_comments[0]
    proc = running_processes[oldest_comment]

    try:
        os.killpg(proc.pid, signal.SIGTERM)  # 프로세스 그룹 전체 종료
    except Exception as e:
        print(f"종료 실패: {e}")
        return f"[{oldest_comment}] 알람 종료에 실패했어요."

    del running_processes[oldest_comment]
    return f" "

def set_reminder(command, minute, hour, day_of_month, month, day_of_week, comment):
    now = datetime.now()
    reminder_time = now.replace(minute=minute, hour=hour, day=day_of_month, month=month, second=0, microsecond=0)
    
    if reminder_time < now:
        reminder_time += timedelta(days=1)
    
    delay = (reminder_time - now).total_seconds()
    Timer(delay, lambda: subprocess.Popen(command, shell=True)).start()
    return "Reminder set successfully."

def alarm_reminder_action(text):
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
    snooze_match = re.search(
        r'\b(?:스누즈|연기|지연|미루기)\s*(?:알람|타이머)\b.*?\b(?:동안|동안에)\s*(\d+\s*(?:분|시간))\b', 
        text, 
        re.IGNORECASE
    )

    remind_match = re.search(
        r'\b(?:알림|리마인드|기억)\s*(?:설정|추가|등록|해줘)\s*(?:나에게|저에게)?\s*(\d+\s*(?:분|시간))\s*(?:후에|안에|뒤에)\s*(.+)', 
        text, 
        re.IGNORECASE
    )

     # ✅ 명령 우선순위 정리: 삭제 → 중지 → 스누즈 → 리마인더 → 설정
    if delete_match:
        comment = delete_match.group(1) or delete_match.group(2)
        return delete_alarm(comment)
    elif stop_match:
        return stop_alarm()
    elif snooze_match:
        snooze_time = snooze_match.group(1)
        snooze_minutes = int(re.search(r'\d+', snooze_time).group())
        comment = "Alarm"
        return snooze_alarm(comment, snooze_minutes)
    elif remind_match:
        time_expression = remind_match.group(1)
        reminder_text = remind_match.group(2)
        if time_expression is None:
            return "No time specified for the reminder."
        hour, minute, dom, month, dow = parse_time_expression(time_expression)
        command = f"""
bash -c 'source /gpt/bin/activate && python -c "import pyttsx3; 
engine = pyttsx3.init(); 
engine.setProperty(\\"rate\\", 145); 
engine.say(\\"Reminder: {reminder_text}\\"); 
engine.runAndWait()"'
        """
        comment = "Reminder"
        return set_reminder(command, minute, hour, dom, month, dow, comment)
    elif set_match:
        time_expression = set_match.group(1) or set_match.group(2)
        if time_expression:
            try:
                hour, minute, dom, month, dow = parse_time_expression(time_expression)
                command = "aplay ../res/alarm.wav"
                comment = "Alarm"
                return set_alarm(command, minute, hour, dom, month, dow, comment)
            except Exception as e:
                return f"(Alarm) 시간 파싱 오류: {str(e)}"
    else:
        return "(Alarm) 시간 표현을 이해하지 못했어요."

