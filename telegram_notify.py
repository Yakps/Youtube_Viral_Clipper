import httpx
import os

try:
    from Settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


async def send_telegram_notification(results: list, folder: str, title: str):
    """
    Klipler hazır olduğunda Telegram'a bildirim gönderir.
    TELEGRAM_TOKEN veya TELEGRAM_CHAT_ID boşsa sessizce geçer.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    lines = [f"✅ *ViralBot tamamlandı!*", f"📹 *{title}*", f"📁 `{folder}`", ""]
    for r in results:
        duration = r.get("duration", 0)
        lines.append(f"🎬 *Clip {r['clip']}* — {int(duration)}s")
        lines.append(f"   _{r.get('title', '')}_ ")
        lines.append(f"   {r.get('reason', '')}")
        lines.append("")

    message = "\n".join(lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Telegram bildirim hatası (önemsiz): {e}")
