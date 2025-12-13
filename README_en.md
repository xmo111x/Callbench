# 📞 Callbench

This project creates professional **phone announcements** using a graphical user interface (Tkinter)  
and the **OpenAI Text-to-Speech API** (`gpt-4o-mini-tts`).  
Optionally, background music (e.g. `musik.mp3`) can be softly mixed in.

---

## ✨ Features

- Input of announcement text via GUI  
- Choose between multiple voices (`nova`, `alloy`, `shimmer`, `coral`, …)  
- Adjustable start delay (music fades in before voice starts)  
- Control music volume (in dB)  
- Speech rate (tempo factor)  
- Pitch control (in semitones)  
- Export as `ansage_final.wav` and `ansage_final.mp3`  
- Playback preview of the generated announcement  

---

## 🐍 Requirements

- **Python 3.12** (not 3.13 – `audioop` was removed)  
- **pip**  
- **git**  
- **ffmpeg**  
- **OpenAI API Key**  
- *(optional)* A background music file (`musik.mp3`) in the project folder  

---

## 🍏 Installation on macOS

```bash
# Repository klonen
git clone https://github.com/xmo111x/Callbench.git
cd Callbench

# Virtuelle Umgebung
python3.12 -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# ffmpeg installieren (z. B. via Homebrew)
brew install ffmpeg

# OpenAI API Key setzen (temporär)
export OPENAI_API_KEY="sk-...."

# Dauerhaft (in ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-...."' >> ~/.zshrc
source ~/.zshrc

# Starten
python ansage_gui.py
```

---

## 🪟 Installation on Windows

Git von https://git-scm.com/install/windows installieren

```powershell
git clone https://github.com/xmo111x/Callbench.git
cd Callbench
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install "httpx==0.27.2" --force-reinstall
choco install ffmpeg
$env:OPENAI_API_KEY="sk-...."
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-....', 'User')
python ansage_gui.py
```

---

## 🐧 Installation on Linux

```bash
git clone https://github.com/xmo111x/Callbench.git
cd Callbench
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-distutils -y
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
sudo apt install ffmpeg -y
export OPENAI_API_KEY="sk-...."
echo 'export OPENAI_API_KEY="sk-...."' >> ~/.bashrc
source ~/.bashrc
python ansage_gui.py
```

---

## 🎵 Royalty-Free Music

Background music was downloaded from **Pixabay Music**.  
It’s **royalty-free** and requires **no registration**:  
👉 [https://pixabay.com/music/](https://pixabay.com/music/)

---

## ▶️ Usage

1. Enter your announcement text in the text field  
2. Adjust voice, style, delay, music volume, tempo, and pitch  
3. Click **“Generate Announcement”**  
4. The files `ansage_final.wav` and `ansage_final.mp3` will be created in the project folder  

---

## ☕ Support Me
This project is open source and free to use.  
If you like my work, you can buy me a coffee:

👉 [paypal.me/mesutoe](https://paypal.me/mesutoe)


🛠 Built with ❤️ by **Mesut**

![Screenshot der GUI](images/preview.png)

Version 2.0

Changes:
Installation files for Mac (Callbench.dmg) and Windows (Callbench.exe) have been created under /dist/.
The OpenAI API key is requested when the announcement is generated for the first time and is stored in the system keychain.
The files ansage_xxx.wav, ansage_xxx.mp3, and voice_xxx.wav are created in the Download folder. A timestamp is added to the file names, and the folder is opened automatically.
The music file must be selected as musik.mp3. By default, no file is selected.
Installation instructions for Windows have been corrected.
