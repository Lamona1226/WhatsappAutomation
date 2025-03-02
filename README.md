# WhatsApp Bulk Message Sender 🚀
![image](https://github.com/user-attachments/assets/35327681-aed7-4d8a-af1d-18cd569a5e6f)



A Python-based automation tool to send bulk WhatsApp messages through WhatsApp Web. Supports text, images, videos, documents, scheduling, and resume functionality.

## 🎯 Features
- ✅ Send bulk messages with text/media attachments
- 📅 Message scheduling with specific timing
- ▶️ Resume interrupted sending tasks
- 📊 Real-time progress tracking
- 🖥️ User-friendly Tkinter GUI
- 📁 CSV contact list management

## 🔧 Technologies
- **Python 3** - Core scripting
- **Selenium** - Browser automation
- **Tkinter** - GUI interface
- **Pandas** - CSV data handling
- **ChromeDriver** - Browser control

## 🚀 Getting Started

### Prerequisites

1. Python 3.x
Ensure you have Python 3 installed. You can verify by running:

        python3 --version
If not installed, use your package manager (e.g., apt, dnf, or yum) to install Python 3.
2. Pip and Virtual Environment

    sudo apt-get install python3-pip
    python3 -m pip install --upgrade pip
Virtual Environment

    python3 -m venv venv
to activate the Enviroment

    source venv/bin/activate
3. Google Chrome/Firefox Browser
Make sure you have either Google Chrome or Firefox installed (depending on your configuration).

### Installing Dependencies
Clone the repository from GitHub:

       git clone https://github.com/Lamona1226/WhatsappAutomation.git

CD repository

    cd whatsapp_bot.py

 Install the required Python packages:

    pip install -r requirements.txt

## 📖 Usage

1-Start the application:
 
     python3 whatsapp_bot.py

2-click on start messaging 

3-Select attachments (your excel contact list)

4-Scan WhatsApp Web QR code when prompted

5- wait untill screen loading then click ok 

## 📜 CSV Format Example

| **Phone Number**  | **Message**           | **Media Path**       |
|-------------------|----------------------|----------------------|
| +1234567890      | How are you?          | images/promo.jpg     |
| +9876543210      | Check this video!     | videos/demo.mp4      |


## ⚠️ Important Notes

  ❗ Not affiliated with WhatsApp - use at your own risk
        
  🚫 Avoid excessive message rates to prevent account restrictions
        
  💻 Requires active GUI session (won't work in headless servers)
        
  🔄 Keep ChromeDriver updated with Chrome browser
        
  📲 Maintain internet connection during operation
        

## 🛠 Future Improvements

- Multi-threaded message delivery

- AI-based message personalization

- Enhanced error recovery mechanisms
 
- Cross-platform packaging

## 🤝 Contributing

Contributions welcome! Please:

1-Fork the repository

2-Create feature branch

3-Submit pull request
