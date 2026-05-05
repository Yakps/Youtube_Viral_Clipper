import os
import re
import json
import asyncio
from datetime import date
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import uvicorn

from telegram_notify import send_telegram_notification

from bot_core import (
    is_youtube_url,
    get_video_info,
    download_audio,
    download_video,
    transcribe_with_whisper,
    analyze_with_openai,
    cut_clips,
    cleanup_temp,
    CIKTI_KLASOR,
)

app = FastAPI(title="ViralBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def private_network_access(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# ─────────────────────────────────────────────
# Statik dosyalar (index.html)
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent

@app.get("/")
async def root():
    return FileResponse(BASE_DIR / "index.html")


# ─────────────────────────────────────────────
# Yardımcı: WebSocket üzerinden mesaj gönder
# ─────────────────────────────────────────────

async def ws_send(ws: WebSocket, type_: str, **kwargs):
    """JSON mesaj gönderir. type_ = log | step | video_info | clips | done | error"""
    await ws.send_json({"type": type_, **kwargs})


def make_sync_log(ws: WebSocket, loop: asyncio.AbstractEventLoop):
    """
    Bot fonksiyonlarına geçirilecek senkron callback.
    asyncio.run_coroutine_threadsafe ile event loop'a gönderir.
    """
    def log(msg: str, level: str = "info"):
        future = asyncio.run_coroutine_threadsafe(
            ws_send(ws, "log", msg=msg, level=level),
            loop
        )
        future.result(timeout=5)
    return log


# ─────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────

@app.websocket("/ws/process")
async def process_video(ws: WebSocket):
    await ws.accept()

    # FIX: get_event_loop() deprecated Python 3.10+ — get_running_loop() kullan
    loop = asyncio.get_running_loop()

    try:
        # İstemciden URL al
        data = await ws.receive_json()
        url = data.get("url", "").strip()

        if not is_youtube_url(url):
            await ws_send(ws, "error", msg="Geçersiz URL — youtube.com veya youtu.be linki gönder")
            return

        # ── ADIM 1: Video bilgisi ──────────────────
        await ws_send(ws, "step", step=1, status="active")
        await ws_send(ws, "log", msg="Video bilgisi alınıyor...", level="info")

        info = await asyncio.to_thread(get_video_info, url)
        title = info.get("title", "video")
        duration = int(info.get("duration", 1800))
        safe_title = re.sub(r'[^\w\s-]', '', title)[:30].strip()

        await ws_send(ws, "step", step=1, status="done")
        await ws_send(ws, "log", msg=f"✓ Başlık: {title}", level="success")
        await ws_send(ws, "video_info", title=title, duration=duration, url=url)

        # ── ADIM 2: Ses indir ──────────────────────
        await ws_send(ws, "step", step=2, status="active")
        await ws_send(ws, "log", msg="Ses indiriliyor (bestaudio/mp3)...", level="info")

        audio_file = await asyncio.to_thread(download_audio, url)
        size_mb = os.path.getsize(audio_file) / (1024 * 1024)

        await ws_send(ws, "step", step=2, status="done")
        await ws_send(ws, "log", msg=f"✓ Ses indirildi — {size_mb:.1f} MB", level="success")

        # ── ADIM 3: Whisper ────────────────────────
        await ws_send(ws, "step", step=3, status="active")

        # FIX: loop referansı closure'a gerek yok, direkt get_running_loop kullanıldı
        def whisper_progress(msg: str):
            future = asyncio.run_coroutine_threadsafe(
                ws_send(ws, "log", msg=msg, level="info"),
                loop
            )
            future.result(timeout=10)

        segments = await asyncio.to_thread(
            transcribe_with_whisper, audio_file, whisper_progress
        )

        if not segments:
            await ws_send(ws, "error", msg="Transkripsiyon başarısız — segment bulunamadı")
            return

        await ws_send(ws, "step", step=3, status="done")
        await ws_send(ws, "log",
                      msg=f"✓ Transkripsiyon tamamlandı — {len(segments)} segment",
                      level="success",
                      extra={"segments": len(segments)})

        # ── ADIM 4: GPT analiz ─────────────────────
        await ws_send(ws, "step", step=4, status="active")
        await ws_send(ws, "log", msg="GPT-4o-mini analiz ediliyor...", level="info")

        clips = await asyncio.to_thread(
            analyze_with_openai, segments, duration, title
        )

        if not clips:
            await ws_send(ws, "error", msg="Uygun kesit bulunamadı!")
            return

        await ws_send(ws, "step", step=4, status="done")
        await ws_send(ws, "log",
                      msg=f"✓ {len(clips)} viral kesit belirlendi",
                      level="success")

        # Kesimleri önizleme olarak gönder
        await ws_send(ws, "clips_preview", clips=clips)

        # ── ADIM 5: Video indir + klip kes ────────
        await ws_send(ws, "step", step=5, status="active")
        await ws_send(ws, "log", msg="Video tam kalite indiriliyor...", level="info")

        video_file = await asyncio.to_thread(download_video, url)
        await ws_send(ws, "log", msg="✓ Video indirildi, klipler kesiliyor...", level="success")

        # FIX: loop referansı closure'a gerek yok
        def clip_progress(msg: str):
            future = asyncio.run_coroutine_threadsafe(
                ws_send(ws, "log", msg=msg, level="info"),
                loop
            )
            future.result(timeout=10)

        today = str(date.today())
        folder = f"{CIKTI_KLASOR}/{today}_{safe_title}"

        results = await asyncio.to_thread(
            cut_clips, video_file, clips, folder, clip_progress
        )

        await ws_send(ws, "step", step=5, status="done")
        await ws_send(ws, "log",
                      msg=f"✓ {len(results)} klip başarıyla kaydedildi → {folder}",
                      level="success")

        # ── TAMAMLANDI ─────────────────────────────
        await ws_send(ws, "done", results=results, folder=folder)

        # Telegram bildirimi (token yoksa sessizce geçer)
        await send_telegram_notification(results, folder, title)

    except WebSocketDisconnect:
        print("İstemci bağlantıyı kesti")

    except json.JSONDecodeError as e:
        await ws_send(ws, "error", msg=f"GPT yanıtı parse edilemedi: {e}")

    except Exception as e:
        await ws_send(ws, "error", msg=str(e))
        print(f"HATA: {e}")

    finally:
        await asyncio.to_thread(cleanup_temp)


# ─────────────────────────────────────────────
# Sunucu başlat
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 ViralBot WebSocket sunucusu başlatılıyor...")
    print("📡 http://localhost:8000")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # Geliştirme için — prodda False yap
        log_level="info"
    )