import os
import glob
import json
import subprocess
import openai

# Settings.py'den al
try:
    from Settings import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

openai.api_key = OPENAI_API_KEY

CIKTI_KLASOR = os.path.expanduser("~/Desktop/youtube_clips")
WHISPER_MAX_MB = 24
WHISPER_MAX_BYTES = WHISPER_MAX_MB * 1024 * 1024


# ─────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────

def is_youtube_url(text: str) -> bool:
    return "youtube.com/watch" in text or "youtu.be/" in text


def get_video_info(url: str) -> dict:
    result = subprocess.run(
        ["yt-dlp", "--cookies-from-browser", "edge", "--dump-json", url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise Exception(f"Video bilgisi alınamadı: {result.stderr[:300]}")
    return json.loads(result.stdout)


# ─────────────────────────────────────────────
# SES İNDİRME
# ─────────────────────────────────────────────

def download_audio(url: str) -> str:
    for old in glob.glob("/tmp/yt_audio.*"):
        os.remove(old)

    result = subprocess.run([
        "yt-dlp",
        "--cookies-from-browser", "edge",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", "/tmp/yt_audio.%(ext)s",
        url
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Ses indirilemedi: {result.stderr[:300]}")

    files = glob.glob("/tmp/yt_audio.*")
    if not files:
        raise Exception("Ses dosyası bulunamadı")
    return files[0]


# ─────────────────────────────────────────────
# VİDEO İNDİRME
# ─────────────────────────────────────────────

def download_video(url: str) -> str:
    for old in glob.glob("/tmp/yt_full.*"):
        os.remove(old)

    result = subprocess.run([
        "yt-dlp",
        "--cookies-from-browser", "edge",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-part",
        "-o", "/tmp/yt_full.%(ext)s",
        url
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Video indirilemedi: {result.stderr[:300]}")

    files = glob.glob("/tmp/yt_full.*")
    if not files:
        raise Exception("Video dosyası bulunamadı")
    return files[0]


# ─────────────────────────────────────────────
# WHİSPER
# ─────────────────────────────────────────────

def split_audio_if_needed(audio_file: str) -> list:
    file_size = os.path.getsize(audio_file)
    if file_size <= WHISPER_MAX_BYTES:
        return [(audio_file, 0.0)]

    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", audio_file
    ], capture_output=True, text=True)

    info = json.loads(probe.stdout)
    total_duration = float(info["format"]["duration"])
    part_count = int(file_size / WHISPER_MAX_BYTES) + 1
    part_duration = total_duration / part_count

    parts = []
    for i in range(part_count):
        start = i * part_duration
        output = f"/tmp/yt_audio_part_{i}.mp3"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", audio_file,
            "-t", str(part_duration),
            "-acodec", "libmp3lame",
            output
        ], capture_output=True, text=True)
        if os.path.exists(output):
            parts.append((output, start))
    return parts


def transcribe_with_whisper(audio_file: str, on_progress=None) -> list:
    """
    on_progress(msg: str) callback — her parça tamamlandığında çağrılır.
    """
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    file_size = os.path.getsize(audio_file)
    all_segments = []

    if file_size <= WHISPER_MAX_BYTES:
        if on_progress:
            on_progress("Whisper API'ye gönderiliyor (tek parça)...")
        with open(audio_file, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        for seg in response.segments:
            all_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })
    else:
        parts = split_audio_if_needed(audio_file)
        if on_progress:
            on_progress(f"Büyük dosya — {len(parts)} parçaya bölündü")

        for idx, (part_file, time_offset) in enumerate(parts):
            if on_progress:
                on_progress(f"Parça {idx+1}/{len(parts)} transkribe ediliyor...")
            with open(part_file, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            for seg in response.segments:
                all_segments.append({
                    "start": seg.start + time_offset,
                    "end": seg.end + time_offset,
                    "text": seg.text.strip()
                })
            os.remove(part_file)

    return all_segments


def segments_to_text(segments: list) -> str:
    lines = []
    for seg in segments:
        start = int(seg["start"])
        text = seg["text"]
        if text:
            lines.append(f"[{start}s] {text}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# OPENAI ANALİZ
# ─────────────────────────────────────────────

def analyze_with_openai(segments: list, duration: int, title: str) -> list:
    transcript = segments_to_text(segments)

    prompt = f"""Sen bir YouTube içerik uzmanısın. Aşağıdaki video transkriptini analiz et ve en viral olabilecek 3 kesiti belirle.

Video başlığı: {title}
Video süresi: {duration} saniye

Transkript (her satır [saniye] metin formatında):
{transcript[:10000]}

KURALLAR:
- Tam olarak 3 kesit seç
- Her kesit 120-150 saniye arası olsun (kesinlikle 120 saniyenin altında olmaz)
- Tüm kesitler {duration} saniyeden önce bitmeli
- Kesitler videonun farklı bölümlerinden olsun
- Duygusal, şaşırtıcı, komik veya çok bilgilendirici anları tercih et
- Timestamps'leri dikkate alarak tam olarak o anları işaret et

Sadece geçerli JSON döndür, başka hiçbir şey yazma:
{{"clips": [{{"start_seconds": 10, "end_seconds": 130, "title": "Kesit başlığı", "reason": "Neden viral olur"}}]}}"""

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    text = response.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    data = json.loads(text)

    clips = [
        c for c in data["clips"]
        if c["end_seconds"] <= duration
        and (c["end_seconds"] - c["start_seconds"]) >= 120
    ]
    return clips


# ─────────────────────────────────────────────
# KLİP KESME
# ─────────────────────────────────────────────

def cut_clips(video_file: str, clips: list, folder: str, on_progress=None) -> list:
    os.makedirs(folder, exist_ok=True)
    results = []

    for i, clip in enumerate(clips):
        start = clip["start_seconds"]
        clip_duration = clip["end_seconds"] - clip["start_seconds"]
        output = f"{folder}/clip_{i+1}.mp4"

        if on_progress:
            on_progress(f"Clip {i+1} kesiliyor: {start}s – {clip['end_seconds']}s ({clip_duration}s)")

        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_file,
            "-t", str(clip_duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output
        ], capture_output=True, text=True)

        if os.path.exists(output) and os.path.getsize(output) > 0:
            results.append({
                "clip": i + 1,
                "file": output,
                "title": clip.get("title", f"Clip {i+1}"),
                "reason": clip.get("reason", ""),
                "start": start,
                "end": clip["end_seconds"],
                "duration": clip_duration
            })

    return results


# ─────────────────────────────────────────────
# TEMIZLIK
# ─────────────────────────────────────────────

def cleanup_temp():
    for pattern in ["/tmp/yt_full.*", "/tmp/yt_audio.*", "/tmp/yt_audio_part_*"]:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except Exception:
                pass