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
        config['DEFAULT'] = {
            'default_country_code': '+20',
            'delay_between': '2',
            'wait_timeout': '20',
            'browser': 'Chrome',
            'max_retries': '2'
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
    """
    Ensures the phone number has a country code.
    If not, removes a leading '0' (if any) and prepends the default country code.
    """
    num_str = str(num).strip()
    if not num_str.startswith('+'):
        if num_str.startswith('0'):
            num_str = num_str[1:]
        num_str = default_code + num_str
    return num_str

def wait_for_schedule(schedule_str):
    """
    Global schedule: wait until the given time (HH:MM:SS) is reached.
    """
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
    """
    Per-row scheduling: if a schedule is provided in the row, wait until that time.
    """
    try:
        if pd.isna(schedule_str) or str(schedule_str).strip() == "":
            return  # No schedule; proceed immediately.
        now = datetime.now()
        # Assume schedule_str is in HH:MM:SS format.
        scheduled_time = datetime.strptime(schedule_str, "%H:%M:%S").replace(
            year=now.year, month=now.month, day=now.day)
        if scheduled_time < now:
            scheduled_time += timedelta(days=1)
        delay = (scheduled_time - now).total_seconds()
        log_message(f"Row schedule: waiting until {scheduled_time.strftime('%H:%M:%S')} (in {int(delay)} seconds) for this contact")
        # Instead of sleeping for the entire delay, sleep in short intervals to allow pause/stop checks.
        while delay > 0:
            if stop_requested:
                break
            pause_event.wait()  # Block if paused.
            sleep_interval = min(5, delay)
            time.sleep(sleep_interval)
            delay -= sleep_interval
    except Exception as e:
        logging.exception("Error parsing row schedule. Continuing immediately.")

# ----------------------- Messaging Functions -----------------------
def send_text(driver, wait, number, message, max_retries):
    """Sends a text message via WhatsApp Web for the given number."""
    encoded_message = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={number}&text={encoded_message}"
    driver.get(url)
    time.sleep(2)  # Let page load
    success = False
    for attempt in range(max_retries):
        try:
            send_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
            send_button.click()
            log_message(f"Text message sent to {number}")
            success = True
            break
        except Exception as e:
            log_message(f"Text attempt {attempt+1} failed for {number}: {e}")
            logging.exception(f"Error sending text to {number}")
            time.sleep(1)
    return success

def send_media(driver, wait, number, file_path, media_type, max_retries):
    """
    Sends media (image, video, or file) via WhatsApp Web.
    This is a simplified placeholder.
    media_type should be one of "Image", "Video", or "File".
    In a real implementation, this function would:
      - Click the attachment icon,
      - Select the correct option (e.g., image, video, or document),
      - Use send_keys() on the file input element with the file path,
      - And then click the send button.
    """
    # For simplicity, we assume that a URL-based method works (it usually doesn't for attachments)
    # In practice, you would interact with the attachment UI elements.
    log_message(f"Sending {media_type} '{file_path}' to {number}")
    # Pseudocode:
    success = False
    for attempt in range(max_retries):
        try:
            # For example, click the attachment icon:
            attach_icon = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@title="Attach"]')))
            attach_icon.click()
            time.sleep(1)
            # Then find the file input and send the file path:
            file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
            file_input.send_keys(os.path.abspath(file_path))
            time.sleep(1)
            # Finally, click the send button:
            send_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
            send_button.click()
            log_message(f"{media_type} sent to {number}")
            success = True
            break
        except Exception as e:
            log_message(f"{media_type} attempt {attempt+1} failed for {number}: {e}")
            logging.exception(f"Error sending {media_type} to {number}")
            time.sleep(1)
    return success

# ----------------------- Main Messaging Function -----------------------
def run_messaging(file_path, default_code, delay_between, wait_timeout, schedule_time, browser_choice, max_retries):
    global messages_sent, messages_failed, stop_requested
    messages_sent = 0
    messages_failed = 0
    stop_requested = False

    # Global scheduling (if provided)
    if schedule_time.strip():
        wait_for_schedule(schedule_time.strip())

    # Load contacts from Excel (expected columns: Number, Message, Image, Video, File, Schedule)
    try:
        df = pd.read_excel(file_path)
        required_cols = ['Number', 'Message']  # Media columns are optional
        if not all(col in df.columns for col in required_cols):
            messagebox.showerror("Error", f"Excel file must contain at least {required_cols} columns")
            return
    except Exception as e:
        messagebox.showerror("Error", f"Error reading Excel file: {e}")
        logging.exception("Error reading Excel file.")
        return

    # Format phone numbers
    df['Number'] = df['Number'].apply(lambda num: format_phone_number(num, default_code))
    total_contacts = len(df)

    # Populate Treeview with initial status (add columns for each media type)
    for item in tree.get_children():
        tree.delete(item)
    tree["columns"] = ("Number", "Text", "Image", "Video", "File", "Schedule")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    for idx, row in df.iterrows():
        schedule_val = row.get("Schedule", "")
        tree.insert("", tk.END, iid=idx, values=(row["Number"], "Pending", "Pending", "Pending", "Pending", schedule_val))

    # Initialize WebDriver based on browser selection
    try:
        if browser_choice == "Chrome":
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service)
        elif browser_choice == "Firefox":
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service)
        else:
            messagebox.showerror("Error", f"Unsupported browser: {browser_choice}")
            return
    except Exception as e:
        messagebox.showerror("Error", f"Error initializing WebDriver: {e}")
        logging.exception("Error initializing WebDriver.")
        return

    wait = WebDriverWait(driver, wait_timeout)

    # Open WhatsApp Web and wait for QR scan
    driver.get("https://web.whatsapp.com")
    messagebox.showinfo("WhatsApp Login", "Please scan the QR code in the opened browser window, then click OK to continue.")

    # Check for resume progress
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

    # Process each contact row
    for index, row in df.iterrows():
        if index < start_index:
            continue
        if stop_requested:
            log_message("Stop requested by user. Halting process.")
            break

        # Per-row scheduling: if the row has a "Schedule" value, wait until that time.
        if "Schedule" in row and pd.notna(row["Schedule"]) and str(row["Schedule"]).strip() != "":
            wait_until_row(str(row["Schedule"]).strip())

        number = row["Number"]
        # Send text if provided
        text_success = True
        if pd.notna(row["Message"]) and str(row["Message"]).strip() != "":
            text_success = send_text(driver, wait, number, str(row["Message"]).strip(), max_retries)
            tree.set(index, column="Text", value="Sent" if text_success else "Failed")
        # Send image if provided
        image_success = True
        if "Image" in row and pd.notna(row["Image"]) and str(row["Image"]).strip() != "":
            image_success = send_media(driver, wait, number, str(row["Image"]).strip(), "Image", max_retries)
            tree.set(index, column="Image", value="Sent" if image_success else "Failed")
        # Send video if provided
        video_success = True
        if "Video" in row and pd.notna(row["Video"]) and str(row["Video"]).strip() != "":
            video_success = send_media(driver, wait, number, str(row["Video"]).strip(), "Video", max_retries)
            tree.set(index, column="Video", value="Sent" if video_success else "Failed")
        # Send file if provided
        file_success = True
        if "File" in row and pd.notna(row["File"]) and str(row["File"]).strip() != "":
            file_success = send_media(driver, wait, number, str(row["File"]).strip(), "File", max_retries)
            tree.set(index, column="File", value="Sent" if file_success else "Failed")

        # Update global counters based on overall success
        with counter_lock:
            if text_success and image_success and video_success and file_success:
                messages_sent += 1
            else:
                messages_failed += 1

        # Save progress
        with open(progress_file, "w") as pf:
            pf.write(str(index + 1))
        root.after(0, update_labels, total_contacts)
        time.sleep(delay_between)

    driver.quit()
    log_message("Bulk messaging complete!")
    messagebox.showinfo("Summary", f"Total Contacts: {total_contacts}\nMessages Sent: {messages_sent}\nMessages Failed: {messages_failed}")
    root.after(0, lambda: start_button.config(state=tk.NORMAL))

# ----------------------- GUI Functions -----------------------
def start_thread():
    file_path = filedialog.askopenfilename(title="Select Excel File",
                                           filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*")))
    if not file_path:
        return  # User cancelled
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

    new_config = {
        'default_country_code': default_code,
        'delay_between': str(delay_between),
        'wait_timeout': str(wait_timeout),
        'browser': browser_choice,
        'max_retries': str(max_retries)
    }
    save_config(new_config)

    start_button.config(state=tk.DISABLED)
    threading.Thread(target=run_messaging, args=(file_path, default_code, delay_between, wait_timeout, schedule_time, browser_choice, max_retries), daemon=True).start()

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

# ----------------------- GUI Setup -----------------------
root = tk.Tk()
root.title("WhatsApp Bulk Messaging Bot")

# Configuration frame
config_frame = tk.Frame(root)
config_frame.pack(pady=5)

tk.Label(config_frame, text="Default Country Code:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.E)
country_code_entry = tk.Entry(config_frame, width=5)
country_code_entry.insert(0, config_defaults.get('default_country_code', '+20'))
country_code_entry.grid(row=0, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Delay Between Messages (sec):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.E)
delay_entry = tk.Entry(config_frame, width=5)
delay_entry.insert(0, config_defaults.get('delay_between', '2'))
delay_entry.grid(row=1, column=1, padx=5, pady=2)

tk.Label(config_frame, text="WebDriver Timeout (sec):").grid(row=2, column=0, padx=5, pady=2, sticky=tk.E)
timeout_entry = tk.Entry(config_frame, width=5)
timeout_entry.insert(0, config_defaults.get('wait_timeout', '20'))
timeout_entry.grid(row=2, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Max Retries:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.E)
retry_entry = tk.Entry(config_frame, width=5)
retry_entry.insert(0, config_defaults.get('max_retries', '2'))
retry_entry.grid(row=3, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Browser:").grid(row=4, column=0, padx=5, pady=2, sticky=tk.E)
browser_var = tk.StringVar()
browser_choices = ["Chrome", "Firefox"]
browser_var.set(config_defaults.get('browser', "Chrome"))
browser_menu = tk.OptionMenu(config_frame, browser_var, *browser_choices)
browser_menu.grid(row=4, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Global Schedule Start (HH:MM:SS, optional):").grid(row=5, column=0, padx=5, pady=2, sticky=tk.E)
schedule_entry = tk.Entry(config_frame, width=10)
schedule_entry.insert(0, "")  # blank means start immediately
schedule_entry.grid(row=5, column=1, padx=5, pady=2)

# Resume checkbox
resume_var = tk.BooleanVar()
resume_check = tk.Checkbutton(config_frame, text="Resume from last progress", variable=resume_var)
resume_check.grid(row=6, column=0, columnspan=2, pady=2)

# Button frame
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

start_button = tk.Button(button_frame, text="Start Messaging", command=start_thread, font=("Helvetica", 12))
start_button.grid(row=0, column=0, padx=5)
pause_button = tk.Button(button_frame, text="Pause Messaging", command=toggle_pause, font=("Helvetica", 12))
pause_button.grid(row=0, column=1, padx=5)
stop_button = tk.Button(button_frame, text="Stop Messaging", command=request_stop, font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5)

# Counters and progress labels
sent_label = tk.Label(root, text="Messages Sent: 0/0", font=("Helvetica", 12))
sent_label.pack(pady=5)
failed_label = tk.Label(root, text="Messages Failed: 0/0", font=("Helvetica", 12))
failed_label.pack(pady=5)
progress_label = tk.Label(root, text="Processed: 0/0", font=("Helvetica", 12))
progress_label.pack(pady=5)

# Progress bar widget
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=5)

# Treeview to show contact status and media statuses
tree = ttk.Treeview(root, columns=("Number", "Text", "Image", "Video", "File", "Schedule"), show="headings", height=8)
for col in ("Number", "Text", "Image", "Video", "File", "Schedule"):
    tree.heading(col, text=col)
tree.pack(pady=5)

# Log text widget
log_text = tk.Text(root, height=10, width=70)
log_text.pack(pady=10)
log_text.insert(tk.END, "Logs will appear here...\n")

# Start processing log queue
root.after(100, process_log_queue)

root.mainloop()
