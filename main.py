import glob
import json
import os
import random
import shutil
import sys
import tempfile
from datetime import date, datetime

from google import genai
from PIL import Image, ImageDraw, ImageFont
import requests

HISTORY_FILE = "data/history.json"
MAX_HISTORY_ITEMS = 180
IMG_WIDTH = 1080
IMG_HEIGHT = 1920
FPS = 24

TOPICS = {
    "deret_angka": "Deret Angka",
    "aritmatika_aljabar": "Aritmatika & Aljabar",
    "peluang_statistika": "Peluang & Statistika",
    "geometri": "Geometri",
    "fungsi_grafik": "Fungsi & Grafik",
}

FONT_BOLD = "fonts/DejaVuSans-Bold.ttf"
FONT_REGULAR = "fonts/DejaVuSans.ttf"

BG_COLOR = "#F0FDFA"
HEADER_BG = "#0D9488"
HEADER_TEXT = "#FFFFFF"
TOPIC_BG = "#CCFBF1"
TOPIC_TEXT = "#0F766E"
SOAL_TEXT = "#1E293B"
PILIHAN_BG = "#FFFFFF"
PILIHAN_ACCENT = "#0D9488"
PILIHAN_TEXT = "#334155"
JAWABAN_BG = "#DCFCE7"
JAWABAN_ACCENT = "#16A34A"
JAWABAN_TEXT = "#166534"
PENJELASAN_TEXT = "#475569"
FOOTER_TEXT = "#94A3B8"


def notify_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[WARN] TELEGRAM not configured. Would send: {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception as e:
        print(f"[WARN] Telegram notification failed: {e}")


def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(history):
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_used_topics_today(history):
    today = date.today().isoformat()
    return {h["topik"] for h in history if h.get("tanggal") == today}


def is_duplicate(soal_text, history):
    return any(h["soal"] == soal_text for h in history)


def pick_topic(history):
    used_today = get_used_topics_today(history)
    available = [t for t in TOPICS if t not in used_today]
    if not available:
        available = list(TOPICS.keys())
    return random.choice(available)


def generate_narasi(topic, history, max_retry=3):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    topic_label = TOPICS[topic]
    recent = history[-20:] if history else []

    prompt = f"""Buat 1 soal matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Soal harus berbentuk pilihan ganda dengan 4 opsi (A, B, C, D).

Format output JSON:
{{
  "soal": "teks soal lengkap",
  "pilihan": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "jawaban": "A. ...",
  "penjelasan": "pembahasan singkat jawaban yang benar"
}}

Aturan:
- Soal dalam Bahasa Indonesia
- Tingkat kesulitan sedang (CPNS/TKA/SNBT)
- Jawaban harus sesuai dengan salah satu pilihan (teks lengkap)
- Jangan buat soal yang sama dengan soal-soal sebelumnya
- Soal sebelumnya: {json.dumps(recent, ensure_ascii=False)}
- Jangan terlalu panjang, maksimal 3 kalimat untuk soal
- Penjelasan maksimal 4 kalimat"""

    for attempt in range(1, max_retry + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            narasi = json.loads(response.text)
            required = {"soal", "pilihan", "jawaban", "penjelasan"}
            if not all(k in narasi for k in required):
                print(f"[WARN] Missing fields, retry {attempt}")
                continue
            if len(narasi["pilihan"]) != 4:
                print(f"[WARN] Not 4 options, retry {attempt}")
                continue
            if narasi["jawaban"] not in narasi["pilihan"]:
                print(f"[WARN] Jawaban not in pilihan, retry {attempt}")
                continue
            if is_duplicate(narasi["soal"], history):
                print(f"[WARN] Duplicate soalan, retry {attempt}")
                continue
            return narasi
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[WARN] Gemini attempt {attempt} failed: {e}")
            if attempt == max_retry:
                raise
    raise RuntimeError(f"Failed to generate soalan after {max_retry} attempts")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_frame_soal(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 48)
    font_reg = ImageFont.truetype(FONT_REGULAR, 36)
    font_soal = ImageFont.truetype(FONT_REGULAR, 42)
    font_badge = ImageFont.truetype(FONT_BOLD, 28)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)

    header_h = 200
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.text((IMG_WIDTH // 2, 70), "SOAL MATEMATIKA", fill=HEADER_TEXT, font=font_bold, anchor="mt")
    draw.text((IMG_WIDTH // 2, 130), "CPNS  •  TKA  •  SNBT", fill=HEADER_TEXT, font=font_reg, anchor="mt")

    topic_label = TOPICS.get(topic, topic)
    badge_padding = 30
    bbox = draw.textbbox((0, 0), topic_label, font=font_badge)
    badge_w = bbox[2] - bbox[0] + badge_padding * 2
    badge_h = bbox[3] - bbox[1] + 16
    badge_x = (IMG_WIDTH - badge_w) // 2
    badge_y = header_h + 30
    draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 20, TOPIC_BG)
    draw.text((badge_x + badge_padding, badge_y + 8), topic_label, fill=TOPIC_TEXT, font=font_badge)

    soal_lines = wrap_text(narasi["soal"], font_soal, draw, IMG_WIDTH - 120)
    line_h = 60
    text_y = badge_y + badge_h + 60
    for line in soal_lines:
        draw.text((IMG_WIDTH // 2, text_y), line, fill=SOAL_TEXT, font=font_soal, anchor="mt")
        text_y += line_h

    footer_y = IMG_HEIGHT - 80
    draw.text((IMG_WIDTH // 2, footer_y), "Simak pilihan jawaban di video ini  ▶️", fill=FOOTER_TEXT, font=font_footer, anchor="mt")

    img.save(output_path)
    return output_path


def render_frame_pilihan(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 44)
    font_pil = ImageFont.truetype(FONT_REGULAR, 38)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.text((IMG_WIDTH // 2, header_h // 2), "PILIHAN JAWABAN", fill=HEADER_TEXT, font=font_bold, anchor="mt")

    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    start_y = header_h + 60
    spacing = 140

    for i, pil in enumerate(narasi["pilihan"]):
        box_y = start_y + i * spacing
        draw_rounded_rect(draw, [margin_x, box_y, margin_x + box_w, box_y + 100], 16, PILIHAN_BG)
        draw.rounded_rectangle([margin_x, box_y, margin_x + 12, box_y + 100], radius=16, fill=PILIHAN_ACCENT)
        draw.text((margin_x + 40, box_y + 50), pil, fill=PILIHAN_TEXT, font=font_pil, anchor="lm")

    footer_y = IMG_HEIGHT - 80
    draw.text((IMG_WIDTH // 2, footer_y), "Jawab di komentar! Jawaban benar ada di akhir video  ✅", fill=FOOTER_TEXT, font=font_footer, anchor="mt")

    img.save(output_path)
    return output_path


def render_frame_pembahasan(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 44)
    font_jawab = ImageFont.truetype(FONT_BOLD, 42)
    font_penjelasan = ImageFont.truetype(FONT_REGULAR, 36)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill="#16A34A")
    draw.text((IMG_WIDTH // 2, header_h // 2), "JAWABAN & PEMBAHASAN", fill="#FFFFFF", font=font_bold, anchor="mt")

    jawab_box_h = 100
    jawab_y = header_h + 60
    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    draw_rounded_rect(draw, [margin_x, jawab_y, margin_x + box_w, jawab_y + jawab_box_h], 16, JAWABAN_BG)
    draw.rounded_rectangle([margin_x, jawab_y, margin_x + 12, jawab_y + jawab_box_h], radius=16, fill=JAWABAN_ACCENT)
    draw.text((margin_x + 40, jawab_y + jawab_box_h // 2), f"✓  {narasi['jawaban']}", fill=JAWABAN_TEXT, font=font_jawab, anchor="lm")

    penjelasan_y = jawab_y + jawab_box_h + 50
    penjelasan_lines = wrap_text(narasi["penjelasan"], font_penjelasan, draw, IMG_WIDTH - 120)
    line_h = 50
    for line in penjelasan_lines:
        draw.text((IMG_WIDTH // 2, penjelasan_y), line, fill=PENJELASAN_TEXT, font=font_penjelasan, anchor="mt")
        penjelasan_y += line_h

    footer_y = IMG_HEIGHT - 80
    draw.text((IMG_WIDTH // 2, footer_y), "Ikuti terus untuk soal-soal CPNS/TKA/SNBT lainnya  📚", fill=FOOTER_TEXT, font=font_footer, anchor="mt")

    img.save(output_path)
    return output_path


def render_video(narasi, topic, filename):
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips

    tmpdir = tempfile.mkdtemp()
    try:
        frame1 = os.path.join(tmpdir, "frame1.png")
        frame2 = os.path.join(tmpdir, "frame2.png")
        frame3 = os.path.join(tmpdir, "frame3.png")

        render_frame_soal(narasi, topic, frame1)
        render_frame_pilihan(narasi, topic, frame2)
        render_frame_pembahasan(narasi, topic, frame3)

        clip1 = ImageClip(frame1, duration=8)
        clip2 = ImageClip(frame2, duration=8)
        clip3 = ImageClip(frame3, duration=10)

        video = concatenate_videoclips([clip1, clip2, clip3], method="compose")

        bgm_files = glob.glob("audio/*.mp3")
        if bgm_files:
            bgm_path = random.choice(bgm_files)
            print(f"[INFO] Using BGM: {bgm_path}")
            audio = AudioFileClip(bgm_path)
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            else:
                repeats = int(video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * repeats).subclipped(0, video.duration)
            video = video.with_audio(audio)
        else:
            print("[INFO] No BGM files found in audio/, rendering without audio")

        video.write_videofile(
            filename,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="ultrafast",
            logger=None,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def check_fb_token():
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        return False, "FB_ACCESS_TOKEN or FB_PAGE_ID not set"
    try:
        resp = requests.get(
            f"https://graph.facebook.com/v25.0/{page_id}",
            params={"access_token": token, "fields": "id,name"},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 401:
            return False, "BLOCKED_TOKEN_EXPIRED: Facebook token expired or invalid"
        else:
            return False, f"Token check failed: {resp.status_code} {resp.text}"
    except requests.RequestException as e:
        return False, f"Token check network error: {e}"


def compliance_check(caption):
    disallowed = [
        "comment", "tag", "share this", "subscri", "follow",
    ]
    caption_lower = caption.lower()
    for pattern in disallowed:
        if pattern in caption_lower:
            raise ValueError(f"Compliance: engagement bait pattern '{pattern}' detected in caption")
    return True


def post_to_facebook(video_path, caption):
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        raise ValueError("FB_ACCESS_TOKEN or FB_PAGE_ID not set")

    valid, err = check_fb_token()
    if not valid:
        notify_telegram(f"[BLOCKED] {err}")
        raise PermissionError(err)

    url = f"https://graph.facebook.com/v20.0/{page_id}/videos"
    with open(video_path, "rb") as f:
        files = {"source": (os.path.basename(video_path), f, "video/mp4")}
        data = {"description": caption, "access_token": token}
        resp = requests.post(url, files=files, data=data, timeout=120)

    if resp.status_code == 200:
        result = resp.json()
        print(f"[OK] Posted to Facebook Reels. Post ID: {result.get('id')}")
        return result
    elif resp.status_code == 401:
        notify_telegram(f"[BLOCKED_TOKEN_EXPIRED] Facebook token expired during upload")
        raise PermissionError("Token expired")
    elif resp.status_code == 429:
        notify_telegram(f"[RATE_LIMITED] Facebook rate limited. Response: {resp.text}")
        raise RuntimeError("Rate limited")
    else:
        body = resp.text[:500]
        notify_telegram(f"[ERROR] Facebook upload failed: {resp.status_code} {body}")
        raise RuntimeError(f"Facebook upload failed: {resp.status_code} - {body}")


def format_caption(narasi, topic):
    topic_label = TOPICS.get(topic, topic)
    op = ", ".join(narasi["pilihan"])
    template = random.choice([
        "🧮 SOAL MATEMATIKA — {topic}\n\n{soal}\n\n{pilihan}\n\nJawaban ada di akhir video.\n\n#SoalMatematika #CPNS2026 #BelajarMatematika #{tag}",
        "🖊️ Latihan soal {topic}\n\n{soal}\n\n{pilihan}\n\nSimak pembahasan lengkapnya di video.\n\n#SoalMatematika #CPNS #BelajarMatematika #{tag}",
        "📐 {topic}\n\n{soal}\n\n{pilihan}\n\nCocokkan jawabanmu dengan yang ada di video.\n\n#SoalMatematika #CPNS2026 #BelajarMatematika #{tag}",
    ])
    caption = template.format(
        topic=topic_label,
        soal=narasi["soal"],
        pilihan=op,
        tag=topic_label.replace(" & ", "").replace(" ", ""),
    )
    return caption


def main():
    print(f"[START] Auto Post Reels Matematika — {datetime.now().isoformat()}")

    history = load_history()
    print(f"[INFO] History loaded: {len(history)} entries")

    topic = pick_topic(history)
    print(f"[INFO] Selected topic: {topic} ({TOPICS.get(topic)})")

    narasi = generate_narasi(topic, history)
    print(f"[INFO] Narasi generated: {narasi['soal'][:60]}...")

    video_filename = f"reels_{topic}_{date.today().isoformat()}_{datetime.now().strftime('%H%M%S')}.mp4"

    print(f"[INFO] Rendering video...")
    render_video(narasi, topic, video_filename)
    print(f"[OK] Video rendered: {video_filename}")

    caption = format_caption(narasi, topic)
    compliance_check(caption)

    print(f"[INFO] Posting to Facebook Reels...")
    post_to_facebook(video_filename, caption)
    print(f"[OK] Posted successfully")

    history.append({
        "soal": narasi["soal"],
        "jawaban": narasi["jawaban"],
        "topik": topic,
        "tanggal": date.today().isoformat(),
    })
    save_history(history)
    print(f"[OK] History saved")

    if os.path.exists(video_filename):
        os.remove(video_filename)
    print(f"[DONE] Auto Post Reels Matematika completed")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"[ERROR] {datetime.now().isoformat()} - {e}"
        print(error_msg)
        notify_telegram(error_msg)
        sys.exit(1)
