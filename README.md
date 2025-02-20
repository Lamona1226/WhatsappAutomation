# WhatsApp Bulk Message Sender 🚀
📌 Overview

This is a Python-based automation tool designed to send bulk WhatsApp messages, including text, images, videos, and documents. It utilizes Selenium WebDriver to interact with WhatsApp Web and features a Tkinter-based GUI for easy usage. The bot also supports message scheduling, resuming interrupted tasks, and real-time progress tracking.
🎯 Features

✅ Send Bulk Messages – Send text, images, videos, and documents to multiple contacts.
✅ Selenium Web Automation – Automates WhatsApp Web interactions.
✅ Tkinter GUI – User-friendly interface for easy operation.
✅ Message Scheduling – Schedule messages to be sent at specific times.
✅ Resume Tasks – Continue sending messages if interrupted.
✅ Progress Tracking – Displays real-time status updates.
🔧 Technologies Used

    Python – Main programming language
    Selenium WebDriver – Automates interactions with WhatsApp Web
    Tkinter – GUI for easy user interaction
    Pandas – Manages contact lists in CSV format
    time & threading – For scheduling and automation

🚀 Getting Started
🔹 Prerequisites

    Install Python 3.x
    Install the required libraries using:

    pip install selenium pandas tk

    Download the Chrome WebDriver compatible with your browser version.

🔹 Usage

    Run the script

    python whatsapp_bot.py

    Login to WhatsApp Web by scanning the QR code.
    Upload a contact list (CSV format) with phone numbers and messages.
    Choose media files (optional) for sending images, videos, or documents.
    Start the bot to automate message sending.
    Track progress in real-time within the GUI.

📜 CSV Format Example

| **Phone Number**  | **Message**           | **Media Path**       |
|-------------------|----------------------|----------------------|
| +1234567890      | How are you?          | images/promo.jpg     |
| +9876543210      | Check this video!     | videos/demo.mp4      |



📌 Screenshots
![image](https://github.com/user-attachments/assets/080a43f6-9c46-4600-a880-e1689dc62954)

⚠️ Important Notes

    This bot is not affiliated with WhatsApp and should be used responsibly.
    Excessive bulk messaging may result in temporary or permanent bans.
    Ensure Chrome WebDriver matches your browser version to avoid errors.

🎨 Future Improvements

    Multi-threading support to improve performance.
    AI-powered message personalization for better engagement.
    Error handling enhancements to manage failed message deliveries.

🤝 Contributing

Contributions are welcome! Feel free to fork this repository, submit issues, or send a pull request.
