import os
import re
import subprocess
import signal
from threading import Timer
from datetime import datetime, timedelta

timers = {}
running_processes = {}
timer_status = {}  # 전역

class Timers:
    def __init__(self, time, timer):
        self.time = time
        self.timer = timer

    def cancel(self):
        self.timer.cancel()

def parse_duration_to_seconds(time_expression):
    hour_match = re.search(r'(\d+)\s*시간', time_expression)
    minute_match = re.search(r'(\d+)\s*분', time_expression)

    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0

    return hours * 3600 + minutes * 60


def set_timer(command, minute, hour, day_of_month, month, day_of_week, comment):
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
        timer_status[unique_comment] = "running"
        
    delay = (alarm_time - now).total_seconds()
    timer = Timer(delay, run_command)  # pass the function itself, not the result of its call
    timer.start()

    timers[unique_comment] = Timers(alarm_time, timer)
    diff = alarm_time - now
    total_minutes = int(diff.total_seconds() // 60)
    diff_hours = total_minutes // 60
    diff_minutes = total_minutes % 60

    display_hour = hour - 12 if hour > 12 else hour

    if diff_hours > 0:
        if diff_minutes > 0:
            response = f"{diff_hours}시간 {diff_minutes}분 후인 {display_hour}시 {minute}분에 타이머를 울릴께요."
        else:
            response = f"{diff_hours}시간 후인 {display_hour}시 {minute}분에 타이머를 울릴께요."
    else:
        response = f"{diff_minutes}분 후인 {display_hour}시 {minute}분에 타이머를 울릴께요."

    return response

def delete_timer(comment):
    def to_12_hour_format(hour):
        return hour - 12 if hour > 12 else hour

    if comment in timers:
        alarm = timers[comment]
        alarm.cancel()
        hour_12 = to_12_hour_format(alarm.time.hour)
        time_str = f"{hour_12}시 {alarm.time.minute}분"
        del timers[comment]
        return f"{time_str} 알람을 삭제했어요."
    else:
        if timers:
            closest_comment = min(timers, key=lambda k: timers[k].time)
            alarm = timers[closest_comment]
            alarm.cancel()
            hour_12 = to_12_hour_format(alarm.time.hour)
            time_str = f"{hour_12}시 {alarm.time.minute}분"
            del timers[closest_comment]
            return f"{time_str} 알람을 삭제했어요."
        else:
            return "삭제할 알람이 없어요."

def stop_timer():
    if not running_processes:
        return "종료할 알람이 없어요."

    sorted_comments = sorted(running_processes.keys())
    oldest_comment = sorted_comments[0]
    proc = running_processes[oldest_comment]

    try:
        os.killpg(proc.pid, signal.SIGTERM)  # 프로세스 그룹 전체 종료
    except Exception as e:
        logger.error(f"종료 실패: {e}")
        return f"[{oldest_comment}] 알람 종료에 실패했어요."

    del running_processes[oldest_comment]
    return f"끔"

def timer_action(text):
    delete_match = re.search(
        r'(?:타이머)\s*(\w+)?\s*(?:삭제|제거|취소)\b'
        r'|(?:삭제|제거|취소)\s*(\w+)?\s*(?:타이머)\b',
        text,
        re.IGNORECASE
    )
    stop_match = re.search(
        r'(?:타이머)\s*(\w+)?\s*(?:꺼줘|꺼)\b'
        r'|(?:꺼줘|꺼)\s*(\w+)?\s*(?:타이머)\b',
        text,
        re.IGNORECASE
    )
    set_match = re.search(
        r'(?:'
            r'(?P<time1>'
                r'(?:\d+\s*시간\s*\d+\s*분|\d+\s*시간|\d+\s*분)'
            r')'
            r'(?:\s*(?:후에|뒤에|안에|동안))?'
            r'\s*(?:알람|타이머)'
            r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?'
        r')'
        r'|(?:'
            r'(?:알람|타이머)'
            r'\s*(?:설정|등록|추가|맞춰|켜줘|울려줘|줘)?\s*'
            r'(?P<time2>'
                r'(?:\d+\s*시간\s*\d+\s*분|\d+\s*시간|\d+\s*분)'
            r')'
            r'(?:\s*(?:후에|뒤에|안에|동안))?'
        r')',
        text,
        re.IGNORECASE
    )

    if delete_match:
        comment = delete_match.group(1) or delete_match.group(2)
        return delete_timer(comment)
    elif stop_match:
        return stop_timer()
    elif set_match:
        time_expression = set_match.group(1) or set_match.group(2)
        try:
            duration_seconds = parse_duration_to_seconds(time_expression)
            future = datetime.now() + timedelta(seconds=duration_seconds)

            hour = future.hour
            minute = future.minute
            dom = future.day
            month = future.month
            dow = '*'

            command = "play ../res/timer.wav vol 0.5"
            comment = "Timer"
            return set_timer(command, minute, hour, dom, month, dow, comment)
        except Exception as e:
            return f"(Timer) 시간 파싱 오류: {str(e)}"
    else:
        return False, "Timer", None
