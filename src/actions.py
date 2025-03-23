from common import *
from datetime import datetime, timedelta
from litellm import completion, check_valid_key
import re
from threading import Timer
import subprocess
import signal

def llm_action(text, retries=3):
    # Load settings from settings.json
    settings = load_settings()
    max_tokens = settings.get("max_tokens")
    temperature = settings.get("temperature")
    model = settings.get("model")

    for i in range(retries):
        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant. {settings.get('custom_instructions')}"},
                    {"role": "user", "content": f"Human: {text}\nAI:"}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            response_content = response.choices[0].message.content.strip()
            if response_content:  # Check if the response is not empty
                return response_content
            else:
                logger.warning(f"Retry {i+1}: Received empty response from LLM.")
        except litellm.exceptions.BadRequestError as e:
            logger.error(traceback.format_exc())
            return f"The API key you provided for `{model}` is not valid. Double check the API key corresponds to the model/provider you are trying to call."
        except Exception as e:
            logger.error(f"Error on try {i+1}: {e}")
            if i == retries - 1:  # If this was the last retry
                return f"Something went wrong after {retries} retries: {e}\n{traceback.format_exc()}"
       # await asyncio.sleep(0.5)  # Wait before retrying

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
    return f"네"

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


async def caldav_action(text: str):
    url = os.getenv('CALDAV_URL')
    username = os.getenv('CALDAV_USERNAME')
    password = os.getenv('CALDAV_PASSWORD')

    if not url or not username or not password:
        return "CalDAV server credentials are not properly set in environment variables."

    try:
        client = caldav.DAVClient(url, username=username, password=password)
        principal = client.principal()
        calendars = principal.calendars()
        if not calendars:
            return "No calendars found."

        calendar = calendars[0]  # Use the first found calendar

        task_create_match = re.search(r'\b(?:add|create)\s+a?\s+task\s+called\s+(.+)', text, re.IGNORECASE)
        task_delete_match = re.search(r'\b(?:delete|remove)\s+(a )?task\s+called\s+(\w+)', text, re.IGNORECASE)
        task_update_match = re.search(r'\b(?:update|change|modify)\s+(a )?task\s+called\s+(\w+)\s+to\s+(\w+)', text, re.IGNORECASE)
        tasks_query_match = re.search(r'\b(left|to do|to-do|what else)\b', text, re.IGNORECASE)
        completed_tasks_query_match = re.search(r'\bcompleted\s+tasks\b', text, re.IGNORECASE)

        if task_create_match:
            task_name = task_create_match.group(1).strip()
            task = calendar.add_todo(f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VTODO
SUMMARY:{task_name}
STATUS:NEEDS-ACTION
END:VTODO
END:VCALENDAR
""")
            return f"Task '{task_name}' created successfully."

        elif task_update_match:
            task_name = task_update_match.group(2)
            new_task_name = task_update_match.group(3)
            tasks = calendar.todos()
            for task in tasks:
                if task_name.lower() in task.instance.vtodo.summary.value.lower():
                    task.instance.vtodo.summary.value = new_task_name
                    task.save()
                    return f"Task '{task_name}' updated to '{new_task_name}' successfully."

        elif task_delete_match:
            task_name = task_delete_match.group(1)
            tasks = calendar.todos()
            for task in tasks:
                if task_name.lower() in task.instance.vtodo.summary.value.lower():
                    task.delete()
                    return f"Task '{task_name}' deleted successfully."

        if tasks_query_match:
            tasks = calendar.todos()
            pending_task_details = []
            for task in tasks:
                if task.vobject_instance.vtodo.status.value != "COMPLETED":
                    summary = task.vobject_instance.vtodo.summary.value
                    status = task.vobject_instance.vtodo.status.value
                    pending_task_details.append(f"'{summary}' (Status: {status})")
            if pending_task_details:
                return "Your pending tasks are: " + ", ".join(pending_task_details)
            else:
                return "You have no pending tasks."

        elif completed_tasks_query_match:
            tasks = calendar.todos()
            completed_task_details = []
            for task in tasks:
                if task.vobject_instance.vtodo.status.value == "COMPLETED":
                    summary = task.vobject_instance.vtodo.summary.value
                    completed_task_details.append(f"'{summary}'")
            if completed_task_details:
                return "Your completed tasks are: " + ", ".join(completed_task_details)
            else:
                return "You have no completed tasks."

        create_match = re.search(r'\b(?:add|create|schedule)\s+an?\s+(event|appointment)\s+called\s+(\w+)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})', text, re.IGNORECASE)
        update_match = re.search(r'\b(?:update|change|modify)\s+the\s+(event|appointment)\s+called\s+(\w+)\s+to\s+(\w+)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})', text, re.IGNORECASE)
        delete_match = re.search(r'\b(?:delete|remove|cancel)\s+the\s+(event|appointment)\s+called\s+(\w+)', text, re.IGNORECASE)
        next_event_match = re.search(r"\bwhat'? ?i?s\s+my\s+next\s+(event|appointment)\b", text, re.IGNORECASE)
        calendar_query_match = re.search(r"\bwhat'? ?i?s\s+on\s+my\s+calendar\b", text, re.IGNORECASE)

        if create_match:
            event_name = create_match.group(1)
            event_time = datetime.strptime(f"{create_match.group(2)} {create_match.group(3)}", "%Y-%m-%d %H:%M")
            event_start = event_time.strftime("%Y%m%dT%H%M%S")
            event_end = (event_time + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")  # Assuming 1 hour duration

            event = calendar.add_event(f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:{event_name}
DTSTART:{event_start}
DTEND:{event_end}
END:VEVENT
END:VCALENDAR
""")
            return f"Event '{event_name}' created successfully."

        elif update_match:
            event_name = update_match.group(2)
            new_event_name = update_match.group(3)
            event_time = datetime.strptime(f"{update_match.group(4)} {update_match.group(5)}", "%Y-%m-%d %H:%M")
            event_start = event_time.strftime("%Y%m%dT%H%M%S")
            event_end = (event_time + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")  # Assuming 1 hour duration

            events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=365), event=True, expand=True)  # Search within the next year
            for event in events:
                if event_name.lower() in event.instance.vevent.summary.value.lower():
                    event.instance.vevent.summary.value = new_event_name
                    event.instance.vevent.dtstart.value = event_start
                    event.instance.vevent.dtend.value = event_end
                    event.save()
                    return f"Event '{event_name}' updated to '{new_event_name}' successfully."

        elif delete_match:
            event_name = delete_match.group(1)
            events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=365), event=True, expand=True)  # Search within the next year
            for event in events:
                if event_name.lower() in event.instance.vevent.summary.value.lower():
                    event.delete()
                    return f"Event '{event_name}' deleted successfully."

        elif next_event_match:
            events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=30), event=True, expand=True)  # Next 30 days
            if events:
                next_event = events[0]
                summary = next_event.vobject_instance.vevent.summary.value
                start_time = next_event.vobject_instance.vevent.dtstart.value
                return f"Your next event is '{summary}' on {start_time.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' ')}"
            else:
                return "No upcoming events found."

        elif calendar_query_match:
            events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=30), event=True, expand=True)  # Next 30 days
            if events:
                event_details = []
                for event in events:
                    summary = event.vobject_instance.vevent.summary.value
                    start_time = event.vobject_instance.vevent.dtstart.value
                    formatted_start_time = start_time.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' ')
                    event_details.append(f"'{summary}' on {formatted_start_time}")
                return "Your upcoming events are: " + ", ".join(event_details)
            else:
                return "No events on your calendar for the next 30 days."
    except caldav.lib.error.AuthorizationError:
        return "Authorization failure: Please check your username and password."
    except caldav.lib.error.NotFoundError:
        return "Resource not found: Check the specified CalDAV URL."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

    return "No valid CalDAV command found."
