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
- Python 3.x
- Google Chrome installed
- ChromeDriver matching Chrome version
- GUI environment (required for browser automation)

### 📥 Linux Installation

#### 1. Install system dependencies
    sudo apt update && sudo apt install -y python3 python3-pip unzip
#### 2.clone the repsitrories

        sudo git clone https://github.com/Lamona1226/WhatsappAutomation.git


#### 3. Install Google Chrome
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install ./google-chrome-stable_current_amd64.deb

#### 4. Install ChromeDriver (automatic version matching)
    LATEST_CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$LATEST_CHROME_VERSION")
    wget -q https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
    unzip chromedriver_linux64.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver

#### 5. Install Python requirements
    pip3 install -r requirements.txt

## 🔧Configuration

Ensure Chrome and ChromeDriver versions match:

    google-chrome --version
    chromedriver --version



## 📖 Usage

1-Start the application:
 
     python3 whatsapp_bot.py


2-Scan WhatsApp Web QR code when prompted

3-Load your CSV contact list

4-Select attachments (optional)

5-Configure sending parameters

6-Start automation and monitor progress

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
        
### Consider using virtual environment for Python packages:
    
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

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
