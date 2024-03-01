# Save as online_monitor.py in C:\OnlineMonitor\
# Run once manually to add to startup and start tracking

import time
import datetime
import json
import subprocess
import threading
import pystray
from PIL import Image, ImageDraw, ImageFont
import ctypes
import os
import sys
import winreg
import win32con
import win32gui
import win32ts
import win32api

# Configuration
LOG_FILE = "online_duration.json"
PING_HOST = "8.8.8.8"

# Check for system lock using session notifications
class LockMonitor(threading.Thread):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.running = True
        self.hwnd = None

    def run(self):
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "LockMonitorWindow"
        wc.lpfnWndProc = self.wnd_proc
        class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, "", 0, 0, 0, 0, 0, 0, 0, hinst, None)
        win32ts.WTSRegisterSessionNotification(self.hwnd, win32ts.NOTIFY_FOR_THIS_SESSION)
        while self.running:
            win32gui.PumpWaitingMessages()
        win32ts.WTSUnRegisterSessionNotification(self.hwnd)
        win32gui.DestroyWindow(self.hwnd)

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32ts.WM_WTSSESSION_CHANGE:
            if wparam == win32ts.WTS_SESSION_LOCK:
                self.callback(True)
            elif wparam == win32ts.WTS_SESSION_UNLOCK:
                self.callback(False)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def stop(self):
        self.running = False
        win32gui.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)

# Timer class
class OnlineDurationTimer:
    def __init__(self):
        self.start_time = None
        self.elapsed = datetime.timedelta()
        self.current_day = datetime.date.today()
        self.running = False

    def start(self):
        if not self.running:
            self.start_time = datetime.datetime.now()
            self.running = True

    def stop(self):
        if self.running:
            self.elapsed += datetime.datetime.now() - self.start_time
            self.running = False

    def reset_daily(self):
        today = datetime.date.today()
        if today != self.current_day:
            log_daily_duration(self.current_day, self.elapsed)
            self.elapsed = datetime.timedelta()
            self.current_day = today
            self.start_time = datetime.datetime.now() if self.running else None

    def get_duration(self):
        if self.running:
            return self.elapsed + (datetime.datetime.now() - self.start_time)
        return self.elapsed

# Logging helpers
def get_logged_data():
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def log_daily_duration(date, duration):
    data = get_logged_data()
    data[str(date)] = str(duration)
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def is_online():
    try:
        subprocess.check_output(["ping", "-n", "1", PING_HOST], timeout=1)
        return True
    except:
        return False

# App class
class OnlineMonitorApp:
    def __init__(self):
        self.timer = OnlineDurationTimer()
        self.is_locked = False
        self.is_online = False
        self.icon = None
        self.running = True
        self.base_icon = self.create_colorful_icon()
        self.lock_monitor = LockMonitor(self.on_lock_state_change)

    def on_lock_state_change(self, locked):
        self.is_locked = locked

    def create_colorful_icon(self):
        image = Image.new('RGB', (64, 64), 'white')
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill='deepskyblue')
        draw.ellipse((24, 24, 40, 40), fill='gold')
        draw.line((8, 8, 56, 56), fill="green", width=4)
        draw.line((8, 56, 56, 8), fill="red", width=4)
        return image

    def update_icon(self):
        if self.icon:
            image = self.base_icon.copy()
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            duration = format_timedelta(self.timer.get_duration())
            week = datetime.date.today().isocalendar()[1]
            draw.text((2, 2), f"{duration}\nW{week}", fill="black", font=font)
            self.icon.icon = image
            self.icon.title = f"Online: {duration} (Week {week})"

    def create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Show Report", self.show_report),
            pystray.MenuItem("Exit", self.exit_app),
        )

    def show_report(self, icon, item):
        data = get_logged_data()
        print("\n--- Online Duration Report ---")
        if not data:
            print("No data available.")
            return

        start = input("Start date (YYYY-MM-DD): ")
        end = input("End date (YYYY-MM-DD): ")
        for date_str, dur in data.items():
            if (not start or date_str >= start) and (not end or date_str <= end):
                print(f"{date_str}: {dur}")

    def exit_app(self, icon, item):
        self.running = False
        self.timer.stop()
        log_daily_duration(self.timer.current_day, self.timer.get_duration())
        self.lock_monitor.stop()
        self.icon.stop()

    def loop(self):
        while self.running:
            self.timer.reset_daily()
            self.is_online = is_online()

            if self.is_online and not self.is_locked:
                self.timer.start()
            else:
                self.timer.stop()

            self.update_icon()
            time.sleep(5)

    def start(self):
        self.icon = pystray.Icon("Online Monitor", self.base_icon, menu=self.create_menu())
        self.lock_monitor.start()
        threading.Thread(target=self.loop, daemon=True).start()
        self.icon.run()

# Add app to Windows startup
def add_to_startup():
    app_name = "OnlineDurationApp"
    path = f'"{
