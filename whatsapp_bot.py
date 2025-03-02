import threading
import time
import urllib.parse
import pandas as pd
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import logging
import configparser
import os
import queue
from datetime import datetime, timedelta
import sys
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException  # For driver check

# --- Driver management imports ---
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# ----------------------- Configuration Persistence -----------------------
CONFIG_FILE = "config.ini"

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        # Added persistent_session option
        config['DEFAULT'] = {
            'default_country_code': '+20',
            'delay_between': '2',
            'wait_timeout': '20',
            'browser': 'Chrome',
            'max_retries': '2',
            'persistent_session': 'False'
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
    return config['DEFAULT']

def save_config(new_config):
    config = configparser.ConfigParser()
    config['DEFAULT'] = new_config
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

# ----------------------- Global Variables -----------------------
config_defaults = load_config()

messages_sent = 0
messages_failed = 0
counter_lock = threading.Lock()
stop_requested = False
pause_event = threading.Event()
pause_event.set()  # Not paused initially
log_queue = queue.Queue()

# For tracking messaging progress (for estimated time remaining)
messaging_start_time = None

# ----------------------- Logging Setup -----------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("whatsapp_bot.log"),
        logging.StreamHandler()
    ]
)

# ----------------------- Helper Functions -----------------------
def update_labels(total):
    with counter_lock:
        sent_label.config(text=f"Messages Sent: {messages_sent}/{total}")
        failed_label.config(text=f"Messages Failed: {messages_failed}/{total}")
        progress_label.config(text=f"Processed: {messages_sent + messages_failed}/{total}")
        progress_value = int(100 * (messages_sent + messages_failed) / total) if total > 0 else 0
        progress_bar['value'] = progress_value

        # Update estimated time remaining if messaging has started
        if messaging_start_time:
            elapsed = time.time() - messaging_start_time
            processed = messages_sent + messages_failed
            if processed > 0:
                avg_time = elapsed / processed
                remaining = (total - processed) * avg_time
                estimated_time_label.config(text=f"Estimated Time Remaining: {int(remaining)} sec")
            else:
                estimated_time_label.config(text="Estimated Time Remaining: -- sec")

def process_log_queue():
    while not log_queue.empty():
        msg = log_queue.get()
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
    root.after(100, process_log_queue)

def log_message(msg):
    log_queue.put(msg)
    logging.info(msg)

def format_phone_number(num, default_code):
    num_str = str(num).strip()
    if not num_str.startswith('+'):
        if num_str.startswith('0'):
            num_str = num_str[1:]
        num_str = default_code + num_str
    return num_str

def wait_for_schedule(schedule_str):
    try:
        now = datetime.now()
        scheduled_time = datetime.strptime(schedule_str, "%H:%M:%S").replace(
            year=now.year, month=now.month, day=now.day)
        if scheduled_time < now:
            scheduled_time += timedelta(days=1)
        delay = (scheduled_time - now).total_seconds()
        log_message(f"Global schedule: waiting until {scheduled_time.strftime('%H:%M:%S')} (in {int(delay)} seconds)")
        time.sleep(delay)
    except Exception as e:
        logging.exception("Error parsing global scheduled time. Continuing immediately.")

def wait_until_row(schedule_str):
    try:
        if pd.isna(schedule_str) or str(schedule_str).strip() == "":
            return
        now = datetime.now()
        scheduled_time = datetime.strptime(schedule_str, "%H:%M:%S").replace(
            year=now.year, month=now.month, day=now.day)
        if scheduled_time < now:
            scheduled_time += timedelta(days=1)
        delay = (scheduled_time - now).total_seconds()
        log_message(f"Row schedule: waiting until {scheduled_time.strftime('%H:%M:%S')} (in {int(delay)} seconds)")
        while delay > 0:
            if stop_requested:
                break
            pause_event.wait()
            sleep_interval = min(0.5, delay)
            time.sleep(sleep_interval)
            delay -= sleep_interval
    except Exception as e:
        logging.exception("Error parsing row schedule. Continuing immediately.")

# ----------------------- WhatsAppBot Class (Modular & Enhanced) -----------------------
class WhatsAppBot:
    def __init__(self, browser_choice, wait_timeout, max_retries, persistent_session=False):
        self.browser_choice = browser_choice
        self.wait_timeout = wait_timeout
        self.max_retries = max_retries
        self.persistent_session = persistent_session
        self.driver = None
        self.init_driver()

    def init_driver(self):
        if self.browser_choice == "Chrome":
            from selenium.webdriver.chrome.options import Options
            options = Options()
            if self.persistent_session:
                options.add_argument("--user-data-dir=./chrome_profile")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(options=options, service=service)
        elif self.browser_choice == "Firefox":
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            options = FirefoxOptions()
            if self.persistent_session:
                profile_path = "./firefox_profile"
                if not os.path.exists(profile_path):
                    os.makedirs(profile_path)
                options.profile = webdriver.FirefoxProfile(profile_path)
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(options=options, service=service)
        else:
            raise ValueError(f"Unsupported browser: {self.browser_choice}")
        self.driver.implicitly_wait(self.wait_timeout)

    def is_driver_valid(self):
        if self.driver is None:
            return False
        try:
            _ = self.driver.title
            return True
        except WebDriverException:
            return False

    def ensure_driver(self):
        if not self.is_driver_valid():
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass
            self.init_driver()
            self.driver.get("https://web.whatsapp.com")
            messagebox.showinfo("WhatsApp Login", "The browser was closed. A new browser has been opened.\nPlease scan the QR code again.")
        return self.driver

    def open_whatsapp(self):
        self.driver.get("https://web.whatsapp.com")
        messagebox.showinfo("WhatsApp Login", "Please scan the QR code in the opened browser, then click OK to continue.")

    def quit_driver(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def send_text(self, wait, number, message):
        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={number}&text={encoded_message}"
        self.driver.get(url)
        time.sleep(2)
        success = False
        delay = 1
        for attempt in range(self.max_retries):
            try:
                send_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
                send_button.click()
                log_message(f"Text message sent to {number}")
                success = True
                break
            except Exception as e:
                log_message(f"Text attempt {attempt+1} failed for {number}")
                time.sleep(delay)
                delay *= 2
        return success

    def send_media(self, wait, number, file_path, media_type):
        log_message(f"Sending {media_type} '{file_path}' to {number}")
        success = False
        delay = 1
        for attempt in range(self.max_retries):
            try:
                attach_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@title="Attach"]')))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", attach_button)
                clickable_attach = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@title="Attach"]')))
                clickable_attach.click()
                time.sleep(1)
                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys(os.path.abspath(file_path))
                time.sleep(1)
                send_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
                time.sleep(2)
                send_button.click()
                time.sleep(5)
                log_message(f"{media_type} sent to {number}")
                success = True
                break
            except Exception as e:
                log_message(f"{media_type} attempt {attempt+1} failed for {number}")
                time.sleep(delay)
                delay *= 2
        return success

# ----------------------- Main Messaging Function -----------------------
def run_messaging(file_path, default_code, delay_between, wait_timeout, schedule_time, browser_choice, max_retries, persistent_session):
    global messages_sent, messages_failed, stop_requested, messaging_start_time
    messages_sent = 0
    messages_failed = 0
    stop_requested = False

    if schedule_time.strip():
        wait_for_schedule(schedule_time.strip())

    try:
        df = pd.read_excel(file_path)
        required_cols = ['Number', 'Message']
        if not all(col in df.columns for col in required_cols):
            messagebox.showerror("Error", f"Excel file must contain at least {required_cols} columns")
            return
    except Exception as e:
        messagebox.showerror("Error", f"Error reading Excel file")
        logging.exception("Error reading Excel file.")
        return

    df['Number'] = df['Number'].apply(lambda num: format_phone_number(num, default_code))
    total_contacts = len(df)

    # Populate Treeview with initial status
    for item in tree.get_children():
        tree.delete(item)
    tree["columns"] = ("Number", "Text", "Image", "Video", "File", "Schedule")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    for idx, row in df.iterrows():
        schedule_val = row.get("Schedule", "")
        tree.insert("", tk.END, iid=idx, values=(row["Number"], "Pending", "Pending", "Pending", "Pending", schedule_val))

    bot = WhatsAppBot(browser_choice, wait_timeout, max_retries, persistent_session)
    bot.open_whatsapp()
    wait = WebDriverWait(bot.driver, wait_timeout)

    messaging_start_time = time.time()

    start_index = 0
    progress_file = "progress.txt"
    if resume_var.get() and os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as pf:
                start_index = int(pf.read().strip())
            log_message(f"Resuming from contact index {start_index}")
        except Exception as e:
            log_message("Error reading progress file. Starting from beginning.")
            start_index = 0

    for index, row in df.iterrows():
        if index < start_index:
            continue
        if stop_requested:
            log_message("Stop requested by user. Halting process.")
            break

        bot.ensure_driver()
        wait = WebDriverWait(bot.driver, wait_timeout)

        if "Schedule" in row and pd.notna(row["Schedule"]) and str(row["Schedule"]).strip() != "":
            wait_until_row(str(row["Schedule"]).strip())

        number = row["Number"]
        text_success = True
        if pd.notna(row["Message"]) and str(row["Message"]).strip() != "":
            text_success = bot.send_text(wait, number, str(row["Message"]).strip())
            tree.set(index, column="Text", value="Sent" if text_success else "Failed")
        image_success = True
        if "Image" in row and pd.notna(row["Image"]) and str(row["Image"]).strip() != "":
            image_success = bot.send_media(wait, number, str(row["Image"]).strip(), "Image")
            tree.set(index, column="Image", value="Sent" if image_success else "Failed")
        video_success = True
        if "Video" in row and pd.notna(row["Video"]) and str(row["Video"]).strip() != "":
            video_success = bot.send_media(wait, number, str(row["Video"]).strip(), "Video")
            tree.set(index, column="Video", value="Sent" if video_success else "Failed")
        file_success = True
        if "File" in row and pd.notna(row["File"]) and str(row["File"]).strip() != "":
            file_success = bot.send_media(wait, number, str(row["File"]).strip(), "File")
            tree.set(index, column="File", value="Sent" if file_success else "Failed")

        with counter_lock:
            if text_success and image_success and video_success and file_success:
                messages_sent += 1
            else:
                messages_failed += 1

        with open(progress_file, "w") as pf:
            pf.write(str(index + 1))
        root.after(0, update_labels, total_contacts)
        
        # Use short sleep intervals to check for stop flag frequently
        sleep_time = 0
        while sleep_time < delay_between:
            if stop_requested:
                break
            time.sleep(0.5)
            sleep_time += 0.5

    bot.quit_driver()
    log_message("Bulk messaging complete!")
    messagebox.showinfo("Summary", f"Total Contacts: {total_contacts}\nMessages Sent: {messages_sent}\nMessages Failed: {messages_failed}")
    root.after(0, lambda: start_button.config(state=tk.NORMAL))

# ----------------------- Advanced Settings Dialog -----------------------
def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("Advanced Settings")
    settings_win.geometry("300x150")
    settings_win.configure(bg="#f0f2f5")

    persistent_var = tk.BooleanVar()
    persistent_var.set(config_defaults.get('persistent_session', 'False') == 'True')

    tk.Label(settings_win, text="Persistent Session:", bg="#f0f2f5", font=("Helvetica", 11)).pack(pady=10)
    tk.Checkbutton(settings_win, text="Keep session (avoid re-scan QR code)", variable=persistent_var, bg="#f0f2f5", font=("Helvetica", 10)).pack()

    def save_settings():
        config_defaults['persistent_session'] = str(persistent_var.get())
        save_config(config_defaults)
        messagebox.showinfo("Settings Saved", "Advanced settings have been updated.")
        settings_win.destroy()

    tk.Button(settings_win, text="Save", command=save_settings, font=("Helvetica", 11)).pack(pady=10)

# ----------------------- GUI Functions -----------------------
def start_thread():
    file_path = filedialog.askopenfilename(title="Select Excel File",
                                           filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*")))
    if not file_path:
        return
    default_code = country_code_entry.get().strip()
    if not default_code.startswith('+'):
        default_code = '+' + default_code
    try:
        delay_between = float(delay_entry.get().strip())
    except:
        delay_between = 2.0
    try:
        wait_timeout = float(timeout_entry.get().strip())
    except:
        wait_timeout = 20.0
    schedule_time = schedule_entry.get().strip()
    browser_choice = browser_var.get()
    try:
        max_retries = int(retry_entry.get().strip())
    except:
        max_retries = 2
    persistent_session = config_defaults.get('persistent_session', 'False') == 'True'

    new_config = {
        'default_country_code': default_code,
        'delay_between': str(delay_between),
        'wait_timeout': str(wait_timeout),
        'browser': browser_choice,
        'max_retries': str(max_retries),
        'persistent_session': str(persistent_session)
    }
    save_config(new_config)

    start_button.config(state=tk.DISABLED)
    threading.Thread(
        target=run_messaging,
        args=(file_path, default_code, delay_between, wait_timeout, schedule_time, browser_choice, max_retries, persistent_session),
        daemon=True
    ).start()

def toggle_pause():
    if pause_event.is_set():
        pause_event.clear()
        pause_button.config(text="Resume Messaging")
        log_message("Messaging paused.")
    else:
        pause_event.set()
        pause_button.config(text="Pause Messaging")
        log_message("Messaging resumed.")

def request_stop():
    global stop_requested
    stop_requested = True
    log_message("Stop button clicked. Requesting stop...")
    start_button.config(state=tk.NORMAL)

# ----------------------- Splash Screen Function -----------------------
def show_splash_screen():
    splash = tk.Toplevel()
    splash.overrideredirect(True)
    splash_width = 400
    splash_height = 200
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width/2) - (splash_width/2))
    y = int((screen_height/2) - (splash_height/2))
    splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")

    # Optionally, set a background image for the splash screen
    try:
        splash_bg = tk.PhotoImage(file="background.png")
        bg_label = tk.Label(splash, image=splash_bg)
        bg_label.image = splash_bg  # keep a reference
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    except Exception:
        splash.configure(bg="#f0f2f5")

    tk.Label(splash, text="Loading WhatsApp Bot...", font=("Helvetica", 16), bg="white").pack(pady=20)
    splash_progress = ttk.Progressbar(splash, orient="horizontal", length=300, mode="determinate")
    splash_progress.pack(pady=20)
    splash_progress['maximum'] = 100

    def update_progress(progress=0):
        splash_progress['value'] = progress
        if progress < 100:
            splash.after(30, update_progress, progress+1)
        else:
            splash.destroy()
            root.deiconify()  # Show main window

    update_progress()

# ----------------------- GUI Setup -----------------------
root = tk.Tk()
root.title("WhatsApp Bulk Messaging Bot")
# Initially hide the main window
root.withdraw()

# Set up a background image replacing the grey color
try:
    background_image = tk.PhotoImage(file="background.png")
    bg_label = tk.Label(root, image=background_image)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception as e:
    print("Background image not found. Continuing with default background.")

# Note: If you want the splash screen background to show through, adjust widget backgrounds accordingly.

style = ttk.Style()
style.theme_use("clam")
# These widget styles have explicit backgrounds. Adjust them if you want more transparency.
style.configure("TFrame", background="white")
style.configure("TLabel", background="white", foreground="#333", font=("Helvetica", 11))
style.configure("Header.TLabel", background="#f0f2f5", foreground="#333", font=("Helvetica", 14, "bold"))
style.configure("TButton", background="#ffffff", foreground="#333", font=("Helvetica", 11), padding=6)
style.configure("green.Horizontal.TProgressbar", troughcolor="#ccc", background="#4caf50", darkcolor="#4caf50", lightcolor="#4caf50")

# Top Logo Frame
logo_frame = tk.Frame(root, bg="#f0f2f5")
logo_frame.pack(pady=10)
try:
    logo_img = tk.PhotoImage(file="logo.png")
    logo_label = tk.Label(logo_frame, image=logo_img, bg="#f0f2f5")
    logo_label.pack()
except Exception:
    pass

# Configuration Frame
config_container = tk.Frame(root, bg="#f0f2f5")
config_container.pack(pady=5)
config_frame = ttk.Frame(config_container, style="TFrame")
config_frame.pack(padx=10, pady=10)

ttk.Label(config_frame, text="Default Country Code:", style="TLabel").grid(row=0, column=0, padx=5, pady=3, sticky=tk.E)
country_code_entry = ttk.Entry(config_frame, width=10)
country_code_entry.insert(0, config_defaults.get('default_country_code', '+20'))
country_code_entry.grid(row=0, column=1, padx=5, pady=3)

ttk.Label(config_frame, text="Delay Between Messages (sec):", style="TLabel").grid(row=1, column=0, padx=5, pady=3, sticky=tk.E)
delay_entry = ttk.Entry(config_frame, width=10)
delay_entry.insert(0, config_defaults.get('delay_between', '2'))
delay_entry.grid(row=1, column=1, padx=5, pady=3)

ttk.Label(config_frame, text="WebDriver Timeout (sec):", style="TLabel").grid(row=2, column=0, padx=5, pady=3, sticky=tk.E)
timeout_entry = ttk.Entry(config_frame, width=10)
timeout_entry.insert(0, config_defaults.get('wait_timeout', '20'))
timeout_entry.grid(row=2, column=1, padx=5, pady=3)

ttk.Label(config_frame, text="Max Retries:", style="TLabel").grid(row=3, column=0, padx=5, pady=3, sticky=tk.E)
retry_entry = ttk.Entry(config_frame, width=10)
retry_entry.insert(0, config_defaults.get('max_retries', '2'))
retry_entry.grid(row=3, column=1, padx=5, pady=3)

ttk.Label(config_frame, text="Browser:", style="TLabel").grid(row=4, column=0, padx=5, pady=3, sticky=tk.E)
browser_var = tk.StringVar()
browser_choices = ["Chrome", "Firefox"]
browser_var.set(config_defaults.get('browser', "Chrome"))
browser_menu = ttk.OptionMenu(config_frame, browser_var, browser_var.get(), *browser_choices)
browser_menu.grid(row=4, column=1, padx=5, pady=3)

ttk.Label(config_frame, text="Global Schedule Start (HH:MM:SS):", style="TLabel").grid(row=5, column=0, padx=5, pady=3, sticky=tk.E)
schedule_entry = ttk.Entry(config_frame, width=10)
schedule_entry.insert(0, "")
schedule_entry.grid(row=5, column=1, padx=5, pady=3)

resume_var = tk.BooleanVar()
resume_check = ttk.Checkbutton(config_frame, text="Resume from last progress", variable=resume_var)
resume_check.grid(row=6, column=0, columnspan=2, pady=3)

# Settings Button for Advanced Settings
settings_button = ttk.Button(config_container, text="Settings", command=open_settings)
settings_button.pack(pady=5)

# Button Frame
button_container = tk.Frame(root, bg="#f0f2f5")
button_container.pack(pady=5)
button_frame = ttk.Frame(button_container, style="TFrame")
button_frame.pack(padx=10, pady=10)
try:
    start_img = tk.PhotoImage(file="start.png")
except Exception:
    start_img = None
try:
    pause_img = tk.PhotoImage(file="pause.png")
except Exception:
    pause_img = None
try:
    stop_img = tk.PhotoImage(file="stop.png")
except Exception:
    stop_img = None

start_button = ttk.Button(button_frame, text="Start Messaging", command=start_thread, image=start_img,
                          compound=tk.LEFT, style="TButton")
start_button.grid(row=0, column=0, padx=10)
pause_button = ttk.Button(button_frame, text="Pause Messaging", command=toggle_pause, image=pause_img,
                          compound=tk.LEFT, style="TButton")
pause_button.grid(row=0, column=1, padx=10)
stop_button = ttk.Button(button_frame, text="Stop Messaging", command=request_stop, image=stop_img,
                         compound=tk.LEFT, style="TButton")
stop_button.grid(row=0, column=2, padx=10)

# Counters, Progress, and Estimated Time
status_frame = tk.Frame(root, bg="#f0f2f5")
status_frame.pack(pady=10)
sent_label = tk.Label(status_frame, text="Messages Sent: 0/0", font=("Helvetica", 12), bg="#f0f2f5")
sent_label.pack(pady=2)
failed_label = tk.Label(status_frame, text="Messages Failed: 0/0", font=("Helvetica", 12), bg="#f0f2f5")
failed_label.pack(pady=2)
progress_label = tk.Label(status_frame, text="Processed: 0/0", font=("Helvetica", 12), bg="#f0f2f5")
progress_label.pack(pady=2)
progress_bar = ttk.Progressbar(status_frame, orient="horizontal", length=300, mode="determinate",
                               style="green.Horizontal.TProgressbar")
progress_bar.pack(pady=5)
estimated_time_label = tk.Label(status_frame, text="Estimated Time Remaining: -- sec", font=("Helvetica", 12), bg="#f0f2f5")
estimated_time_label.pack(pady=2)

# Treeview for Contact Status
tree_frame = ttk.Frame(root, style="TFrame")
tree_frame.pack(pady=5, fill=tk.BOTH, expand=True)
tree = ttk.Treeview(tree_frame, columns=("Number", "Text", "Image", "Video", "File", "Schedule"),
                    show="headings", height=8)
for col in ("Number", "Text", "Image", "Video", "File", "Schedule"):
    tree.heading(col, text=col)
tree.pack(pady=5, fill=tk.BOTH, expand=True)

# Log Text Widget
log_frame = ttk.Frame(root, style="TFrame")
log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
log_text = tk.Text(log_frame, height=10, width=70, bg="white", fg="#333", font=("Helvetica", 10))
log_text.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
log_text.insert(tk.END, "Logs will appear here...\n")

# Start the splash screen, then launch the main window
root.after(0, show_splash_screen)
root.after(100, process_log_queue)
root.mainloop()
