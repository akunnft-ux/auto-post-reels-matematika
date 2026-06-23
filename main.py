import glob
import json
import os
import random
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta

from google import genai
from PIL import Image, ImageDraw, ImageFont
import requests

HISTORY_FILE = "data/history.json"
ANALYTICS_FILE = "data/analytics.json"
GROWTH_FILE = "data/growth.json"
MODE_FILE = "data/mode.json"
PROCESSED_CSV_FILE = "data/processed_msg.json"
MAX_HISTORY_ITEMS = 180
IMG_WIDTH = 1080
IMG_HEIGHT = 1920
FPS = 24

CONTENT_TYPES = ["quiz", "fakta", "tips"]
CONTENT_TYPE_WEIGHTS = {"quiz": 0.4, "fakta": 0.3, "tips": 0.3}

TOPICS = {
    "deret_angka": "Deret Angka",
    "aritmatika_aljabar": "Aritmatika & Aljabar",
    "peluang_statistika": "Peluang & Statistika",
    "geometri": "Geometri",
    "fungsi_grafik": "Fungsi & Grafik",
}

FONT_BOLD = "fonts/DejaVuSans-Bold.ttf"
FONT_REGULAR = "fonts/DejaVuSans.ttf"

BG_COLOR = "#FFF8E7"
HEADER_BG = "#1B2A4A"
HEADER_TEXT = "#FFFFFF"
TOPIC_BG = {"deret_angka": "#FF6B9D", "aritmatika_aljabar": "#FF8C42", "peluang_statistika": "#A8E6CF", "geometri": "#7EC8E3", "fungsi_grafik": "#DDA0DD"}
TOPIC_TEXT = "#FFFFFF"
SOAL_TEXT = "#2C3E50"
PILIHAN_BG = "#FFFFFF"
PILIHAN_ACCENT = "#FF8C42"
PILIHAN_TEXT = "#2C3E50"
JAWABAN_BG = "#FFE0EC"
JAWABAN_ACCENT = "#FF6B9D"
JAWABAN_TEXT = "#8B2252"
PENJELASAN_TEXT = "#475569"
FOOTER_TEXT = "#94A3B8"

DODDLE_ICONS = ["\u2726", "\u2605", "\u2727", "\u25C6", "\u2B1F", "\u27A1"]
FOOTER_POOL_SOAL = [
    "Semangat belajar! \U0001F680", "Terus berlatih! \U0001F4AA",
    "Kunci sukses adalah latihan! \U0001F4DA", "Satu soal hari ini, juara besok! \U0001F3C6",
    "Yakin bisa! \u26A1", "Pantang menyerah! \U0001F525",
    "Latihan dulu, baru ujian! \u2705", "Belajar itu menyenangkan! \U0001F60A",
    "Jangan lupa istirahat! \u2615", None,
]
FOOTER_POOL_PILIHAN = [
    "Coba tebak dulu sebelum lihat jawaban! \U0001F914", "Pilih jawabanmu! \u270F\uFE0F",
    "Yakin dengan pilihanmu? \U0001F9D0", None, None,
]
FOOTER_POOL_PEMBAHASAN = [
    "Paham penjelasannya? \U0001F50D", "Semoga membantu! \U0001F4D6",
    "Jangan sungkan bertanya! \U0001F4AC", "Share ke temanmu! \U0001F465",
    None, None,
]

HASHTAG_POOL = [
    "#SoalMatematika", "#CPNS2026", "#BelajarMatematika",
    "#MatematikaDasar", "#CPNS", "#TIUCPNS", "#SKDCPNS",
    "#TryoutCPNS", "#RuangBelajar", "#Matematika",
    "#LatihanCPNS", "#StudiCPNS",
]

EMOJI_POOL = ["\U0001F9EE", "\U0001F4D0", "\U0001F4DD", "\u270F\uFE0F", "\U0001F4CA", "\u2797", "\u2795", "\u274C"]

HOOK_TEMPLATES = {
    "quiz": [
        "90% orang salah jawab soal ini. Coba kamu? \U0001F9D0",
        "Kebanyakan orang terkecoh. Pasti kamu bisa! \u26A1",
        "Hanya 1 dari 10 orang yang benar. Ayo coba! \U0001F3AF",
        "Jangan terkecoh dengan soalnya! \U0001F4A1",
        "Menurutmu jawabannya apa? Coba tebak dulu! \U0001F914",
    ],
    "fakta": [
        "Ternyata selama ini kamu salah! Cek videonya \u23EF\uFE0F",
        "Fakta mengejutkan yang jarang orang tahu! \U0001F92F",
        "Mind blowing! Matematika itu tidak seperti yang kamu kira \U0001F92F",
        "Kebanyakan guru juga salah menjelaskan ini! \U0001F631",
        "Baru tahu setelah lulus? Simak ini! \U0001FAE0",
    ],
    "tips": [
        "Hitung dalam 3 detik! Rahasianya di sini \u26A1",
        "Cara ini bikin kamu jago matematika dalam 1 menit! \U0001F525",
        "Trik cepat yang gak diajarin di sekolah! \U0001F4A1",
        "Anti panik! Begini cara cepatnya \u2705",
        "Save video ini! Pasti berguna nanti \U0001F4CC",
    ],
}

CTA_POOL = [
    "Follow @matematikacpns untuk soal baru setiap hari! \U0001F525",
    "Follow akun ini biar makin jago matematika! \U0001F4DA",
    "Jangan lupa follow buat latihan CPNS tiap hari! \u2705",
    "Follow for more daily soal + tips CPNS! \U0001F680",
    "Klik follow biar gak ketinggalan soal baru! \U0001F4DD",
]

def _load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
    return _load_json(HISTORY_FILE, [])

def save_history(history):
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    _save_json(HISTORY_FILE, history)

def load_analytics():
    return _load_json(ANALYTICS_FILE, [])

def save_analytics(records):
    _save_json(ANALYTICS_FILE, records)

def load_growth():
    return _load_json(GROWTH_FILE, [])

def save_growth(records):
    _save_json(GROWTH_FILE, records)

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

def pick_content_type():
    types = list(CONTENT_TYPE_WEIGHTS.keys())
    weights = [CONTENT_TYPE_WEIGHTS[t] for t in types]
    return random.choices(types, weights=weights, k=1)[0]

def get_hook(content_type):
    return random.choice(HOOK_TEMPLATES[content_type])

def get_cta():
    return random.choice(CTA_POOL)

def generate_narasi(topic, history, content_type, max_retry=3):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    topic_label = TOPICS[topic]
    recent = history[-20:] if history else []

    if content_type == "quiz":
        prompt = f"""Buat 1 soal matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Soal harus berbentuk pilihan ganda dengan 4 opsi (A, B, C, D). Buat soal yang agak menjebak dan banyak orang salah menjawabnya — ini penting untuk engagement.

Format output JSON:
{{
  "soal": "teks soal lengkap",
  "pilihan": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "jawaban": "A. ...",
  "penjelasan": "pembahasan singkat mengapa jawaban itu benar dan yang lain salah"
}}

Aturan:
- Soal dalam Bahasa Indonesia
- Tingkat kesulitan sedang-cukup sulit (CPNS/TKA/SNBT)
- Jawaban harus sesuai dengan salah satu pilihan (teks lengkap)
- Jangan buat soal yang sama dengan soal-soal sebelumnya
- Soal sebelumnya: {json.dumps(recent, ensure_ascii=False)}
- Maksimal 3 kalimat untuk soal
- Penjelasan maksimal 4 kalimat, fokus pada trik mengerjakannya"""
    elif content_type == "fakta":
        prompt = f"""Buat 1 konten fakta matematika yang mengejutkan dan jarang diketahui orang, terkait topik {topic_label}.

Konten harus informatif dan bikin orang berkata "wow, baru tahu!".

Format output JSON:
{{
  "soal": "fakta matematika yang mengejutkan (1-2 kalimat)",
  "pilihan": ["Penjelasan lanjutan 1", "Penjelasan lanjutan 2", "Penjelasan lanjutan 3", "Penjelasan lanjutan 4"],
  "jawaban": "fakta yang benar (sesuai pilihan yang paling tepat)",
  "penjelasan": "penjelasan ilmiah/detail dari fakta tersebut (2-3 kalimat)"
}}

Aturan:
- Fakta harus BENAR secara matematis, jangan menyesatkan
- Bahasa Indonesia
- Maksimal 2 kalimat untuk fakta
- Penjelasan 3-4 kalimat
- Contoh: "Ternyata 0.999... = 1", atau "Ada bilangan yang lebih besar dari tak terhingga"
- Pastikan faktanya bisa diverifikasi"""
    else:
        prompt = f"""Buat 1 tips/trik cepat matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Tips harus praktis, mudah diingat, dan langsung bisa dipakai.

Format output JSON:
{{
  "soal": "pertanyaan atau masalah yang sering muncul (1 kalimat)",
  "pilihan": ["A. Cara umum (lambat)", "B. Cara umum lainnya", "C. Cara cepat (trikinya)", "D. Cara salah yang umum"],
  "jawaban": "C. Cara cepat (trikinya)",
  "penjelasan": "penjelasan trik cepat langkah demi langkah (2-3 kalimat)"
}}

Aturan:
- Tips harus BENAR secara matematis
- Bahasa Indonesia
- Maksimal 2 kalimat untuk soal
- Penjelasan 3-4 kalimat
- Fokus pada trik yang bisa dipakai di ujian CPNS/TKA/SNBT
- Contoh: "Trik hitung persen dalam 3 detik" atau "Cara cepat deret aritmatika"""

    for attempt in range(1, max_retry + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
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
    raise RuntimeError(f"Failed to generate content after {max_retry} attempts")

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
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def render_frame_soal(narasi, topic, output_path, content_type="quiz"):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 48)
    font_reg = ImageFont.truetype(FONT_REGULAR, 36)
    font_soal = ImageFont.truetype(FONT_REGULAR, 42)
    font_badge = ImageFont.truetype(FONT_BOLD, 28)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)
    font_icon = ImageFont.truetype(FONT_BOLD, 36)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")
    topic_bg = hex_to_rgb(topic_accent)

    content_labels = {"quiz": "QUIZ CHALLENGE", "fakta": "FAKTA MATEMATIKA", "tips": "TIPS CEPAT"}
    content_label = content_labels.get(content_type, "SOAL MATEMATIKA")
    sub_labels = {"quiz": "Coba tebak! \U0001F9D0", "fakta": "Mind blowing! \U0001F92F", "tips": "Catat baik-baik! \U0001F4DD"}
    sub_label = sub_labels.get(content_type, "CPNS \u2022 TKA \u2022 SNBT")

    header_h = 180
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.rounded_rectangle([0, header_h - 6, IMG_WIDTH, header_h + 6], radius=0, fill="#FF8C42")
    draw.text((IMG_WIDTH // 2, 65), content_label, fill=HEADER_TEXT, font=font_bold, anchor="mt")
    draw.text((IMG_WIDTH // 2, 120), sub_label, fill="#FFC896", font=font_reg, anchor="mt")

    type_icons = {"quiz": "\u270F\uFE0F", "fakta": "\U0001F92F", "tips": "\u26A1"}
    draw.text((IMG_WIDTH - 80, 30), type_icons.get(content_type, "\u270F\uFE0F"), fill="#FFE0B2", anchor="mm", font=font_icon)
    draw.text((60, 140), "\u2605", fill="#FFC896", anchor="mm", font=font_icon)

    topic_label = TOPICS.get(topic, topic)
    badge_padding = 30
    bbox = draw.textbbox((0, 0), f"\u2605 {topic_label}", font=font_badge)
    badge_w = bbox[2] - bbox[0] + badge_padding * 2
    badge_h = bbox[3] - bbox[1] + 16
    badge_x = (IMG_WIDTH - badge_w) // 2
    badge_y = header_h + 35
    draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 22, topic_bg)
    draw.text((badge_x + badge_padding, badge_y + 8), f"\u2605 {topic_label}", fill="#FFFFFF", font=font_badge)

    soal_lines = wrap_text(narasi["soal"], font_soal, draw, IMG_WIDTH - 120)
    line_h = 60
    text_y = badge_y + badge_h + 55
    for line in soal_lines:
        draw.text((IMG_WIDTH // 2, text_y), line, fill=SOAL_TEXT, font=font_soal, anchor="mt")
        text_y += line_h

    footer_y = IMG_HEIGHT - 80
    draw.line([(80, footer_y), (IMG_WIDTH - 80, footer_y)], fill=topic_bg, width=3)
    deco = random.choice(DODDLE_ICONS)
    footer = random.choice(FOOTER_POOL_SOAL)
    if footer:
        draw.text((IMG_WIDTH // 2 - 20, footer_y + 30), footer, fill=FOOTER_TEXT, font=font_footer, anchor="mt")
        fw = draw.textlength(footer, font=font_footer)
        draw.text((IMG_WIDTH // 2 + fw / 2 + 10, footer_y + 30), f" {deco}", fill="#FF8C42", font=font_footer, anchor="mt")
    else:
        draw.text((IMG_WIDTH // 2, footer_y + 30), deco, fill="#FF8C42", font=font_icon, anchor="mt")

    img.save(output_path)
    return output_path

def render_frame_pilihan(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 44)
    font_pil = ImageFont.truetype(FONT_REGULAR, 38)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)
    font_icon = ImageFont.truetype(FONT_BOLD, 32)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")
    topic_bg = hex_to_rgb(topic_accent)

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.rounded_rectangle([0, header_h - 6, IMG_WIDTH, header_h + 6], radius=0, fill="#FF8C42")
    draw.text((IMG_WIDTH // 2, header_h // 2), "PILIHAN JAWABAN", fill=HEADER_TEXT, font=font_bold, anchor="mt")

    draw.text((IMG_WIDTH - 70, 35), "\u270F\uFE0F", fill="#FFE0B2", anchor="mm", font=font_icon)

    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    start_y = header_h + 60
    spacing = 140

    for i, pil in enumerate(narasi["pilihan"]):
        letter = chr(65 + i)
        box_y = start_y + i * spacing
        draw_rounded_rect(draw, [margin_x, box_y, margin_x + box_w, box_y + 100], 16, PILIHAN_BG)
        draw.rounded_rectangle([margin_x + 2, box_y + 2, margin_x + box_w - 2, box_y + 98], radius=14, fill=None, outline=topic_bg, width=2)
        draw.rounded_rectangle([margin_x, box_y, margin_x + 14, box_y + 100], radius=16, fill=topic_bg)
        draw.text((margin_x + 40, box_y + 50), f"{letter}.  {pil}", fill=PILIHAN_TEXT, font=font_pil, anchor="lm")

    footer_y = IMG_HEIGHT - 80
    draw.line([(80, footer_y), (IMG_WIDTH - 80, footer_y)], fill=topic_bg, width=3)
    deco = random.choice(DODDLE_ICONS)
    footer_text = random.choice(FOOTER_POOL_PILIHAN)
    if footer_text:
        draw.text((IMG_WIDTH // 2 - 20, footer_y + 30), footer_text, fill=FOOTER_TEXT, font=font_footer, anchor="mt")
        fw = draw.textlength(footer_text, font=font_footer)
        draw.text((IMG_WIDTH // 2 + fw / 2 + 10, footer_y + 30), f" {deco}", fill="#FF8C42", font=font_footer, anchor="mt")
    else:
        draw.text((IMG_WIDTH // 2, footer_y + 30), deco, fill="#FF8C42", font=font_icon, anchor="mt")

    img.save(output_path)
    return output_path

def render_frame_pembahasan(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 44)
    font_jawab = ImageFont.truetype(FONT_BOLD, 42)
    font_penjelasan = ImageFont.truetype(FONT_REGULAR, 36)
    font_footer = ImageFont.truetype(FONT_REGULAR, 24)
    font_icon = ImageFont.truetype(FONT_BOLD, 32)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.rounded_rectangle([0, header_h - 6, IMG_WIDTH, header_h + 6], radius=0, fill="#FF8C42")
    draw.text((IMG_WIDTH // 2, header_h // 2), "JAWABAN & PEMBAHASAN", fill=HEADER_TEXT, font=font_bold, anchor="mt")

    draw.text((IMG_WIDTH - 70, 35), "\U0001F4A1", fill="#FFE0B2", anchor="mm", font=font_icon)

    jawab_box_h = 100
    jawab_y = header_h + 60
    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    draw_rounded_rect(draw, [margin_x, jawab_y, margin_x + box_w, jawab_y + jawab_box_h], 16, JAWABAN_BG)
    draw.rounded_rectangle([margin_x + 2, jawab_y + 2, margin_x + box_w - 2, jawab_y + jawab_box_h - 2], radius=14, fill=None, outline=JAWABAN_ACCENT, width=2)
    draw.rounded_rectangle([margin_x, jawab_y, margin_x + 14, jawab_y + jawab_box_h], radius=16, fill=JAWABAN_ACCENT)
    draw.text((margin_x + 40, jawab_y + jawab_box_h // 2), f"\u2713  {narasi['jawaban']}", fill=JAWABAN_TEXT, font=font_jawab, anchor="lm")

    penjelasan_y = jawab_y + jawab_box_h + 50
    penjelasan_lines = wrap_text(narasi["penjelasan"], font_penjelasan, draw, IMG_WIDTH - 120)
    line_h = 50
    for line in penjelasan_lines:
        draw.text((IMG_WIDTH // 2, penjelasan_y), line, fill=PENJELASAN_TEXT, font=font_penjelasan, anchor="mt")
        penjelasan_y += line_h

    footer_y = IMG_HEIGHT - 80
    draw.line([(80, footer_y), (IMG_WIDTH - 80, footer_y)], fill=hex_to_rgb(topic_accent), width=3)
    deco = random.choice(DODDLE_ICONS)
    footer_text = random.choice(FOOTER_POOL_PEMBAHASAN)
    if footer_text:
        draw.text((IMG_WIDTH // 2 - 20, footer_y + 30), footer_text, fill=FOOTER_TEXT, font=font_footer, anchor="mt")
        fw = draw.textlength(footer_text, font=font_footer)
        draw.text((IMG_WIDTH // 2 + fw / 2 + 10, footer_y + 30), f" {deco}", fill="#FF8C42", font=font_footer, anchor="mt")
    else:
        draw.text((IMG_WIDTH // 2, footer_y + 30), deco, fill="#FF8C42", font=font_icon, anchor="mt")

    img.save(output_path)
    return output_path

def render_video(narasi, topic, filename, content_type="quiz"):
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips

    tmpdir = tempfile.mkdtemp()
    try:
        frame1 = os.path.join(tmpdir, "frame1.png")
        frame2 = os.path.join(tmpdir, "frame2.png")
        frame3 = os.path.join(tmpdir, "frame3.png")

        render_frame_soal(narasi, topic, frame1, content_type)
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
        return False, "FB_ACCESS_TOKEN or FB_PAGE_ID not set — safe skip (Telegram mode)"
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
    disallowed_bait_patterns = [
        "comment.*if you", "comment.*if agree", "tag.*friends",
        "tag 5", "share this.*see", "share.*to win",
    ]
    caption_lower = caption.lower()
    for pattern in disallowed_bait_patterns:
        if re.search(pattern, caption_lower):
            raise ValueError(f"Compliance: engagement bait pattern '{pattern}' detected in caption")
    return True

def build_caption(narasi, topic, content_type, hook):
    topic_label = TOPICS.get(topic, topic)
    cta = get_cta()
    tags = " ".join(random.sample(HASHTAG_POOL, k=min(6, len(HASHTAG_POOL))))

    content_labels = {"quiz": "Soal", "fakta": "Fakta", "tips": "Tips"}
    label = content_labels.get(content_type, "Soal")

    body_templates = {
        "quiz": f"{narasi['soal']}\n\n{', '.join(narasi['pilihan'])}",
        "fakta": f"{narasi['soal']}\n\n{', '.join(narasi['pilihan'])}",
        "tips": f"{narasi['soal']}\n\n{', '.join(narasi['pilihan'])}",
    }
    body = body_templates.get(content_type, narasi["soal"])

    caption = f"{hook}\n\n{body}\n\n{cta}\n\n{tags}"
    return caption

def post_to_facebook(video_path, caption):
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        raise ValueError("FB_ACCESS_TOKEN or FB_PAGE_ID not set")

    valid, err = check_fb_token()
    if not valid:
        notify_telegram(f"[BLOCKED] {err}")
        raise PermissionError(err)

    compliance_check(caption)

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

def check_telegram_mode():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return "telegram"

    current_mode = "telegram"
    last_id = 0
    if os.path.exists(MODE_FILE):
        with open(MODE_FILE) as f:
            d = json.load(f)
            current_mode = d.get("mode", "telegram")
            last_id = d.get("last_update_id", 0)

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 5},
        )
        if resp.ok:
            for upd in resp.json().get("result", []):
                uid = upd["update_id"]
                if uid > last_id:
                    last_id = uid
                    text = (upd.get("message") or {}).get("text", "").strip().lower()
                    if text == "/mode facebook":
                        current_mode = "facebook"
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": "\u2705 Mode berubah ke FACEBOOK"},
                            timeout=10,
                        )
                    elif text == "/mode telegram":
                        current_mode = "telegram"
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": "\u2705 Mode berubah ke TELEGRAM"},
                            timeout=10,
                        )
    except Exception as e:
        print(f"[WARN] Telegram mode check failed: {e}")

    os.makedirs("data", exist_ok=True)
    with open(MODE_FILE, "w") as f:
        json.dump({"mode": current_mode, "last_update_id": last_id}, f)
    return current_mode

def post_to_telegram(video_path, caption):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required")
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {"chat_id": chat_id, "caption": caption[:1024], "supports_streaming": True}
        resp = requests.post(url, files=files, data=data, timeout=120)
    if not resp.ok:
        raise RuntimeError(f"Telegram sendVideo failed: {resp.status_code} {resp.text}")
    msg_id = resp.json()["result"]["message_id"]
    print(f"[OK] Sent to Telegram. Message ID: {msg_id}")

def load_processed_csv():
    if not os.path.exists(PROCESSED_CSV_FILE):
        return []
    with open(PROCESSED_CSV_FILE) as f:
        return json.load(f)

def save_processed_csv(processed):
    os.makedirs("data", exist_ok=True)
    with open(PROCESSED_CSV_FILE, "w") as f:
        json.dump(processed, f, indent=2)

def download_telegram_file(file_id, dest_path):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[WARN] TELEGRAM_BOT_TOKEN not set, cannot download CSV")
        return False
    file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
    resp = requests.get(file_url, timeout=15)
    if not resp.ok:
        print(f"[WARN] getFile failed: {resp.text[:200]}")
        return False
    file_path = resp.json()["result"]["file_path"]
    dl_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    dl = requests.get(dl_url, timeout=30)
    if not dl.ok:
        print(f"[WARN] File download failed: {dl.status_code}")
        return False
    with open(dest_path, "wb") as f:
        f.write(dl.content)
    print(f"[OK] CSV downloaded to {dest_path} ({len(dl.content)} bytes)")
    return True

def parse_csv_with_gemini(csv_path):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] GEMINI_API_KEY not set, skipping CSV parse")
        return []
    client = genai.Client(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    with open(csv_path) as f:
        raw = f.read()
    prompt = (
        "Berikut adalah CSV export Facebook Page Insights. "
        "Parse CSV ini dan ekstrak data setiap post: post_id, post_date, views (impressions), likes (reactions), comments, shares. "
        "Kembalikan JSON array of objects, contoh: [{\"post_id\":\"123\",\"post_date\":\"2026-06-01\",\"views\":100,\"likes\":5,\"comments\":1,\"shares\":0}]. "
        "Jika tidak bisa parse, kembalikan JSON array kosong [].\n\n"
        f"CSV:\n{raw[:50000]}"
    )
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        if isinstance(parsed, list):
            print(f"[OK] Gemini parsed {len(parsed)} records from CSV")
            return parsed
        print("[WARN] Gemini returned non-list, skipping")
        return []
    except Exception as e:
        print(f"[WARN] Gemini CSV parse failed: {e}")
        return []

def fetch_follower_count():
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        return None

    try:
        resp = requests.get(
            f"https://graph.facebook.com/v25.0/{page_id}",
            params={"access_token": token, "fields": "followers_count"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("followers_count", 0)
        return None
    except requests.RequestException as e:
        print(f"[WARN] Follower count fetch failed: {e}")
        return None

def record_growth():
    follower_count = fetch_follower_count()
    if follower_count is None:
        print("[WARN] Could not fetch follower count")
        return

    growth = load_growth()
    prev_count = growth[-1]["follower_count"] if growth else 0
    daily_growth = follower_count - prev_count

    record = {
        "date": date.today().isoformat(),
        "follower_count": follower_count,
        "source": "api",
        "daily_growth": daily_growth,
        "fetched_at": datetime.now().isoformat(),
    }

    existing = [r for r in growth if r["date"] == record["date"]]
    if existing:
        growth[growth.index(existing[0])] = record
    else:
        growth.append(record)

    save_growth(growth)
    print(f"[OK] Growth recorded: {follower_count} followers (+{daily_growth})")

    total_growth = sum(r["daily_growth"] for r in growth if r["daily_growth"] > 0)
    remaining = 5000 - follower_count
    days_left = max(1, (date(2026, 7, 23) - date.today()).days)
    needed_daily = max(0, remaining / days_left)

    if total_growth > 0:
        notify_telegram(
            f"\U0001F4CA Growth Update\n"
            f"Followers: {follower_count}\n"
            f"Hari ini: +{daily_growth}\n"
            f"Total growth: +{total_growth}\n"
            f"Sisa target: {remaining} followers\n"
            f"Butuh ~{needed_daily:.0f}/hari untuk 5000"
        )

def run_analytics_batch():
    print(f"[INFO] Running analytics batch...")
    history = load_history()
    analytics = load_analytics()
    existing_ids = {a.get("post_id") for a in analytics}

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[WARN] TELEGRAM env vars not set, skipping CSV analytics")
        return

    processed = load_processed_csv()
    processed_msg_ids = set(p.get("message_id") for p in processed)

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"timeout": 10},
        )
        if not resp.ok:
            print(f"[WARN] getUpdates failed: {resp.status_code} {resp.text[:200]}")
            return

        updates = resp.json().get("result", [])
        csv_count = 0
        for upd in updates:
            msg = upd.get("message") or upd.get("channel_post") or {}
            msg_id = msg.get("message_id")
            if not msg_id or msg_id in processed_msg_ids:
                continue

            document = msg.get("document")
            if not document:
                continue

            file_name = (document.get("file_name") or "").lower()
            if not file_name.endswith(".csv"):
                continue

            file_id = document["file_id"]
            dest_path = f"/tmp/analytics_csv_{msg_id}.csv"
            ok = download_telegram_file(file_id, dest_path)
            if not ok:
                continue

            records = parse_csv_with_gemini(dest_path)
            if os.path.exists(dest_path):
                os.remove(dest_path)

            for rec in records:
                pid = rec.get("post_id")
                if not pid or pid in existing_ids:
                    continue
                matched_entry = next((h for h in history if h.get("post_id") == pid), {})
                analytics.append({
                    "post_id": pid,
                    "post_date": rec.get("post_date", "")[:10],
                    "views": rec.get("views", 0),
                    "likes": rec.get("likes", 0),
                    "comments": rec.get("comments", 0),
                    "shares": rec.get("shares", 0),
                    "source": "csv_export",
                    "content_type": matched_entry.get("content_type", "unknown"),
                    "fetched_at": datetime.now().isoformat(),
                })
                existing_ids.add(pid)

            csv_count += 1
            processed.append({"message_id": msg_id, "file_name": file_name, "processed_at": datetime.now().isoformat()})

        save_processed_csv(processed)
        save_analytics(analytics)
        print(f"[OK] Analytics saved: {csv_count} CSV files processed, {len(analytics)} total records")

    except requests.RequestException as e:
        print(f"[WARN] Analytics batch failed: {e}")

    record_growth()

def classify_performance(analytics_records, growth_records):
    follower_count = growth_records[-1]["follower_count"] if growth_records else 0

    classifications = []
    for record in analytics_records:
        views = record.get("views", 0)
        likes = record.get("likes", 0)
        comments = record.get("comments", 0)
        shares = record.get("shares", 0)

        if follower_count < 100:
            is_viral = views > 1000
        else:
            is_viral = views > 10 * follower_count

        engagement = likes + comments + shares
        engagement_rate = engagement / max(views, 1)

        if is_viral:
            classification = "viral"
            metric_triggered = f"views={views}"
        elif views < 50:
            classification = "bad"
            metric_triggered = f"views={views}"
        elif engagement_rate < 0.01:
            classification = "bad"
            metric_triggered = f"engagement_rate={engagement_rate:.4f}"
        else:
            classification = "good"
            metric_triggered = f"engagement_rate={engagement_rate:.4f}"

        classifications.append({
            "post_id": record.get("post_id"),
            "classification": classification,
            "metric_triggered": metric_triggered,
            "follower_count_at_post": follower_count,
            "computed_at": datetime.now().isoformat(),
        })

    return classifications

def run_self_learning_review():
    print(f"[INFO] Running weekly self-learning review...")

    analytics = load_analytics()
    growth = load_growth()

    if len(analytics) < 3:
        print("[INFO] Not enough analytics data (<3 records), skipping self-learning")
        notify_telegram("\u26A0 Self-learning: Data analytics belum cukup (min 3 records). Skip minggu ini.")
        return

    tracked = [a for a in analytics if a.get("source") in ("api", "csv_export")]
    if not tracked:
        print("[INFO] No analytics records (api/csv_export), skipping self-learning")
        return

    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent = [a for a in tracked if a.get("fetched_at", "") >= seven_days_ago]
    if not recent:
        recent = tracked[-10:]

    classifications = classify_performance(recent, growth)

    viral = [c for c in classifications if c["classification"] == "viral"]
    good = [c for c in classifications if c["classification"] == "good"]
    bad = [c for c in classifications if c["classification"] == "bad"]

    follower_count = growth[-1]["follower_count"] if growth else 0
    week1_growth = sum(r["daily_growth"] for r in growth[:7]) if len(growth) >= 7 else 0

    msg_lines = [
        f"\U0001F4CA Weekly Review (7 hari)",
        f"Followers: {follower_count}",
        f"Week growth: +{week1_growth}",
        f"",
        f"Viral: {len(viral)} post",
        f"Good: {len(good)} post",
        f"Bad: {len(bad)} post",
    ]

    if viral:
        msg_lines.append(f"")
        msg_lines.append(f"\u2705 Best format: tiru format post viral ini")
        msg_lines.append(f"  - {viral[0]['post_id']} ({viral[0]['metric_triggered']})")

    if bad:
        msg_lines.append(f"")
        msg_lines.append(f"\u274C Worst: {bad[0]['post_id']} ({bad[0]['metric_triggered']})")

    remaining = 5000 - follower_count
    days_left = max(1, 30 - len(growth))
    needed = max(0, remaining / days_left)
    msg_lines.append(f"")
    msg_lines.append(f"Sisa: {remaining} followers / {days_left} hari")
    msg_lines.append(f"Butuh ~{needed:.0f} follower/hari")

    msg = "\n".join(msg_lines)
    print(f"[SELF-LEARNING] {msg}")
    notify_telegram(msg)

def main():
    today_str = date.today().isoformat()
    print(f"[START] Auto Post Reels Matematika (Growth Mode) — {datetime.now().isoformat()}")

    history = load_history()
    print(f"[INFO] History loaded: {len(history)} entries")

    topic = pick_topic(history)
    print(f"[INFO] Selected topic: {topic} ({TOPICS.get(topic)})")

    content_type = pick_content_type()
    print(f"[INFO] Content type: {content_type}")

    hook = get_hook(content_type)
    print(f"[INFO] Hook: {hook}")

    narasi = generate_narasi(topic, history, content_type)
    print(f"[INFO] Content generated: {narasi['soal'][:60]}...")

    video_filename = f"reels_{topic}_{today_str}_{datetime.now().strftime('%H%M%S')}.mp4"
    print(f"[INFO] Rendering video...")
    render_video(narasi, topic, video_filename, content_type)
    print(f"[OK] Video rendered: {video_filename}")

    caption = build_caption(narasi, topic, content_type, hook)
    compliance_check(caption)

    post_mode = check_telegram_mode()
    print(f"[INFO] Post mode: {post_mode.upper()}")

    post_id = None
    if post_mode == "telegram":
        post_to_telegram(video_filename, caption)
    else:
        result = post_to_facebook(video_filename, caption)
        post_id = result.get("id") if result else None

    print(f"[OK] Posted successfully")

    entry = {
        "soal": narasi["soal"],
        "jawaban": narasi["jawaban"],
        "topik": topic,
        "tanggal": today_str,
        "content_type": content_type,
    }
    if post_id:
        entry["post_id"] = post_id
    history.append(entry)
    save_history(history)
    print(f"[OK] History saved")

    if os.path.exists(video_filename):
        os.remove(video_filename)

    print(f"[DONE] Auto Post Reels Matematika completed")

def main_analytics():
    print(f"[START] Analytics Batch — {datetime.now().isoformat()}")
    run_analytics_batch()

    growth = load_growth()
    if len(growth) > 0 and len(growth) % 7 == 0:
        run_self_learning_review()
    else:
        print(f"[INFO] Not a review day yet ({len(growth)} days of data)")

    print(f"[DONE] Analytics Batch completed")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    try:
        if mode == "analytics":
            main_analytics()
        elif mode == "review":
            run_self_learning_review()
        else:
            main()
    except Exception as e:
        error_msg = f"[ERROR] {datetime.now().isoformat()} - {e}"
        print(error_msg)
        notify_telegram(error_msg)
        sys.exit(1)
