<img width="1438" height="767" alt="Ekran Resmi 2026-05-04 14 59 11" src="https://github.com/user-attachments/assets/24422375-1240-4a48-85d6-e28b1002350b" />

<img width="1440" height="760" alt="Ekran Resmi 2026-05-04 14 59 22" src="https://github.com/user-attachments/assets/2dd95f66-699e-41bb-a78f-ca3c55829638" />


# YouTube Viral Clipper

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
