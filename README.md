<img width="1470" height="827" alt="Ekran Resmi 2026-05-08 22 31 59" src="https://github.com/user-attachments/assets/458213d6-d7e3-4431-ac05-8e95f2e62540" />
<img width="1470" height="829" alt="Ekran Resmi 2026-05-08 22 39 48" src="https://github.com/user-attachments/assets/aba2434b-a3a9-4e8e-b3d6-a46579737474" />
<img width="1470" height="830" alt="Ekran Resmi 2026-05-08 22 39 40" src="https://github.com/user-attachments/assets/dd63d932-ee39-487d-ba2d-6816fe7e9f3a" />

# YouTube Viral Clipper

Paste a YouTube video, and AI finds the 3 most viral moments and cuts them as mp4 files.

## What does it do?

1. Paste a YouTube link into the web interface
2. Audio is downloaded and transcribed with Whisper
3. GPT-4o-mini identifies the 3 most viral moments
4. ffmpeg cuts those moments and saves them as mp4
5. Every step streams live to the browser via WebSocket

## Installation

```bash
git clone https://github.com/Yakps/Youtube-Viral-Clipper.git
cd Youtube-Viral-Clipper

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp Settings.example.py Settings.py
# Add your OpenAI and Telegram keys inside Settings.py
```

> ffmpeg must be installed on your system → https://ffmpeg.org/download.html

## Running

**Web interface:**
```bash
python server.py
```
Open `http://localhost:8000` in your browser and paste a YouTube link.

**Telegram bot:**
```bash
python bot.py
```
Send a YouTube link to the bot on Telegram — clips will be saved to your desktop.
The web interface works on its own; the Telegram bot is just an optional way to monitor progress remotely.

## Tech Stack

- FastAPI + WebSocket
- OpenAI Whisper + GPT-4o-mini
- yt-dlp + ffmpeg
- Telegram Bot

# YouTube Viral Clipper(Türkçe)

YouTube videosunu yapıştır, AI en viral 3 anı bulup mp4 olarak keser.

## Ne yapar?

1. YouTube linkini web arayüzüne yapıştır
2. Ses indirilir, Whisper ile transkribe edilir
3. GPT-4o-mini en viral 3 anı belirler
4. ffmpeg o anları mp4 olarak keser ve kaydeder
5. Her adım tarayıcıya canlı olarak yansır (WebSocket)

## Kurulum

```bash
git clone https://github.com/Yakps/Youtube-Viral-Clipper.git
cd Youtube-Viral-Clipper

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp Settings.example.py Settings.py
# Settings.py içine OpenAI ve Telegram keylerini yaz
```

> ffmpeg sisteminizde kurulu olmalı → https://ffmpeg.org/download.html

## Çalıştırma

**Web arayüzü:**
```bash
python server.py
```
Tarayıcıda `http://localhost:8000` aç, YouTube linki yapıştır.

**Telegram botu:**
```bash
python bot.py
```
Telegram'da bota YouTube linki gönder, klipler masaüstüne kaydedilir.
Göndermek zorunda değilsin sadece siteden de yapabilirsin bu bir seçenek ama telegramdan da takip edebilirsin.

## Teknolojiler

- FastAPI + WebSocket
- OpenAI Whisper + GPT-4o-mini
- yt-dlp + ffmpeg
- Telegram Bot
