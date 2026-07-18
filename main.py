import asyncio
import glob
import json
import os
import random
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta

import edge_tts
from google import genai
from PIL import Image, ImageDraw, ImageFont
import requests

HISTORY_FILE = "data/history.json"
ANALYTICS_FILE = "data/analytics.json"
GROWTH_FILE = "data/growth.json"
MODE_FILE = "data/mode.json"
PRODUCT_LINKS_FILE = "data/product_links.json"
PRODUCT_ASSETS_DIR = "assets/shopee"
HOOK_ASSETS_DIR = "assets/hooks"
PROCESSED_CSV_FILE = "data/processed_msg.json"
LEARNING_CONFIG_FILE = "self_learning/learning_config.json"
MAX_HISTORY_ITEMS = 180
IMG_WIDTH = 1080
IMG_HEIGHT = 1920
FPS = 24

# ── Account strategy (per rekomendasi pemisahan format/tema) ──
ACCOUNT_TYPE = "page"
CONTENT_FORMAT = "slide"
PAGE_MAJOR_THEMES = ["cpns", "ujian_sd", "ujian_smp", "ujian_sma", "olimpiade_sd", "olimpiade_smp", "olimpiade_sma"]
PAGE_MINOR_THEMES = ["cpns"]
PAGE_MAJOR_CT_WEIGHTS = {"quiz": 0.8, "fakta": 0.1, "tips": 0.1}  # 80% serious quiz
PAGE_MINOR_CT_WEIGHTS = {"quiz": 0.2, "fakta": 0.4, "tips": 0.4}  # 20% lighter
STAGGER_FILE = "data/last_stagger.json"
STAGGER_MIN_HOURS = 3  # minimum gap between personal & page posts

TTS_VOICE = "id-ID-ArdiNeural"
TTS_RATE = "-1%"
TTS_TIMEOUT = 30
TTS_MAX_CHARS = 2000
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"    # symbols & pictographs
    "\U0001F680-\U0001F6FF"    # transport & map
    "\U0001F1E0-\U0001F1FF"    # flags
    "\U00002702-\U000027B0"    # dingbats
    "\U000024C2-\U0001F251"    # enclosed
    "\U0001F900-\U0001F9FF"    # supplemental symbols
    "\U0001FA00-\U0001FA6F"    # chess symbols
    "\U0001FA70-\U0001FAFF"    # symbols extended-A
    "\U00002600-\U000026FF"    # misc symbols
    "\U0000FE00-\U0000FE0F"    # variation selectors
    "\U0000200D"               # zero width joiner
    "]+", re.UNICODE
)
MIN_SOAL_SECONDS = 6
MIN_PILIHAN_SECONDS = 6
MIN_PEMBAHASAN_SECONDS = 5

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

HOOK_BG_COLORS = ["#1A3A3A", "#3D1A3D", "#1A3D2A", "#3D2A1A", "#1A2A3D", "#3D1A1A"]
HOOK_BG_ROTATION_FILE = "data/hook_bg_rotation.json"

SUPERSCRIPT_MAP = {
    "0": "\u2070", "1": "\u00B9", "2": "\u00B2", "3": "\u00B3",
    "4": "\u2074", "5": "\u2075", "6": "\u2076", "7": "\u2077",
    "8": "\u2078", "9": "\u2079",
    "+": "\u207A", "-": "\u207B", "=": "\u207C",
    "(": "\u207D", ")": "\u207E",
    "a": "\u1D43", "b": "\u1D47", "c": "\u1D9C", "d": "\u1D48",
    "e": "\u1D49", "f": "\u1DA0", "g": "\u1D4D", "h": "\u02B0",
    "i": "\u2071", "j": "\u1DA8", "k": "\u1D4F", "l": "\u02E1",
    "m": "\u1D50", "n": "\u207F", "o": "\u1D52", "p": "\u1D56",
    "r": "\u02B3", "s": "\u02E2", "t": "\u1D57", "u": "\u1D58",
    "v": "\u1D5B", "w": "\u02B7", "x": "\u02E3", "y": "\u02B8",
    "z": "\u1DBB",
}

FRACTION_MAP = {
    "1/2": "\u00BD", "1/3": "\u2153", "2/3": "\u2154",
    "1/4": "\u00BC", "3/4": "\u00BE",
    "1/5": "\u2155", "2/5": "\u2156", "3/5": "\u2157", "4/5": "\u2158",
    "1/6": "\u2159", "5/6": "\u215A",
    "1/7": "\u2150",
    "1/8": "\u215B", "3/8": "\u215C", "5/8": "\u215D", "7/8": "\u215E",
    "1/9": "\u2151",
    "1/10": "\u2152",
}

SUBSCRIPT_MAP = {
    "0": "\u2080", "1": "\u2081", "2": "\u2082", "3": "\u2083",
    "4": "\u2084", "5": "\u2085", "6": "\u2086", "7": "\u2087",
    "8": "\u2088", "9": "\u2089",
    "+": "\u208A", "-": "\u208B", "=": "\u208C",
    "(": "\u208D", ")": "\u208E",
    "a": "\u2090", "e": "\u2091", "o": "\u2092", "x": "\u2093",
    "h": "\u2095", "k": "\u2096", "l": "\u2097", "m": "\u2098",
    "n": "\u2099", "p": "\u209A", "s": "\u209B", "t": "\u209C",
}

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
        "Menurutmu jawabannya apa? Coba pause dan tebak dulu! \U0001F914",
        "Cuma 1 dari 20 orang yang bisa jawab soal ini dalam 10 detik. Kamu termasuk? \U0001F3AF",
        "Temenmu pasti langsung jawab salah. Buktiin kamu beda \u2014 coba dulu! \U0001F447",
        "Jawabannya sesimpel ini, tapi kebanyakan orang overthinking. Tebak dulu, baru cek! \U0001F92F",
        "Tulis jawabanmu di komentar SEBELUM lihat reveal-nya. Yang bener, kasih tanda \U0001F525 di komentar!",
        "Kalau kamu anak matematika sejati, ini harusnya gampang. Buktiin di komentar! \U0001F4AA",
        "Ada 1 trik yang bikin soal ini kejawab dalam 5 detik. Coba dulu cara manual, terus cek triknya! \u26A1",
        "Ini soal yang bikin banyak orang salah karena buru-buru. Jangan sampai kamu juga! \U0001F9D0",
        "Gampang katanya? Coba jawab dulu sebelum lihat pembahasannya. Komentar jawabanmu! \U0001F4DD",
        "Di akhir video ada cara cepatnya \u2014 tapi coba jawab versi kamu dulu di komentar! \U0001F3AC",
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
    "Tulis A/B/C/D di komentar sebelum scroll ke jawaban! \U0001F447",
    "Follow @matematikacpns untuk soal baru setiap hari! \U0001F525",
    "Jawab dulu di komentar \u2014 reveal ada di akhir video! \U0001F4DD",
    "Follow akun ini biar makin jago matematika! \U0001F4DA",
    "Komen jawabanmu, kasih \U0001F525 kalau bener!"
]

CATEGORY_KEYS = [
    "cpns",
    "olimpiade_sd", "olimpiade_smp", "olimpiade_sma",
    "ujian_sd", "ujian_smp", "ujian_sma",
]
CATEGORY_WEIGHTS = {k: 1.0 / len(CATEGORY_KEYS) for k in CATEGORY_KEYS}

CATEGORIES = {
    "cpns": {
        "label": "CPNS",
        "sub_label": "CPNS \u2022 TKA \u2022 SNBT",
        "prompt_context": "persiapan CPNS/TKA/SNBT, tingkat kesulitan sedang-cukup sulit",
        "hashtag_pool": [
            "#SoalMatematika", "#CPNS2026", "#BelajarMatematika",
            "#MatematikaDasar", "#CPNS", "#TIUCPNS", "#SKDCPNS",
            "#TryoutCPNS", "#LatihanCPNS", "#StudiCPNS",
        ],
    },
    "olimpiade_sd": {
        "label": "Olimpiade SD",
        "sub_label": "Olimpiade Matematika SD",
        "prompt_context": "olimpiade matematika tingkat SD, soal berpola dan logis untuk siswa SD kelas 4-6",
        "hashtag_pool": [
            "#OlimpiadeSD", "#OlimpiadeMatematika", "#MatematikaSD",
            "#SoalOlimpiade", "#BelajarMatematika", "#MatematikaAsik",
            "#Olimpiade", "#LatihanOlimpiade",
        ],
    },
    "olimpiade_smp": {
        "label": "Olimpiade SMP",
        "sub_label": "Olimpiade Matematika SMP",
        "prompt_context": "olimpiade matematika tingkat SMP, soal berpola dan logis dengan tingkat kesulitan menantang",
        "hashtag_pool": [
            "#OlimpiadeSMP", "#OlimpiadeMatematika", "#MatematikaSMP",
            "#SoalOlimpiade", "#BelajarMatematika", "#MatematikaAsik",
            "#Olimpiade", "#LatihanOlimpiade",
        ],
    },
    "olimpiade_sma": {
        "label": "Olimpiade SMA",
        "sub_label": "Olimpiade Matematika SMA",
        "prompt_context": "olimpiade matematika tingkat SMA, soal berpola kompleks dan menantang",
        "hashtag_pool": [
            "#OlimpiadeSMA", "#OlimpiadeMatematika", "#MatematikaSMA",
            "#SoalOlimpiade", "#BelajarMatematika", "#MatematikaAsik",
            "#Olimpiade", "#LatihanOlimpiade",
        ],
    },
    "ujian_sd": {
        "label": "Ujian SD",
        "sub_label": "Ujian Sekolah SD",
        "prompt_context": "ujian sekolah (US/USBN) matematika tingkat SD, sesuai kurikulum SD",
        "hashtag_pool": [
            "#UjianSD", "#USSD", "#USBNSD", "#MatematikaSD",
            "#BelajarMatematika", "#UjianNasional", "#LatihanUjian",
            "#MatematikaDasar",
        ],
    },
    "ujian_smp": {
        "label": "Ujian SMP",
        "sub_label": "Ujian Sekolah SMP",
        "prompt_context": "ujian sekolah (US/USBN) matematika tingkat SMP, sesuai kurikulum SMP",
        "hashtag_pool": [
            "#UjianSMP", "#USSMP", "#USBNSMP", "#MatematikaSMP",
            "#BelajarMatematika", "#UjianNasional", "#LatihanUjian",
            "#MatematikaDasar",
        ],
    },
    "ujian_sma": {
        "label": "Ujian SMA",
        "sub_label": "Ujian Sekolah SMA",
        "prompt_context": "ujian sekolah (US/USBN) matematika tingkat SMA, sesuai kurikulum SMA",
        "hashtag_pool": [
            "#UjianSMA", "#USSMA", "#USBNSMA", "#MatematikaSMA",
            "#BelajarMatematika", "#UjianNasional", "#LatihanUjian",
            "#MatematikaDasar",
        ],
    },
}

_topic_image_cache = {}


def get_topic_image(topic, size=200, opacity=0.15):
    key = (topic, size)
    if key not in _topic_image_cache:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        h = TOPIC_BG.get(topic, "#FF8C42")
        h = h.lstrip("#")
        accent = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        accent_rgba = (*accent, 255)
        light_rgba = (*accent, 60)

        cx, cy = size // 2, size // 2
        r = size // 2 - 12

        if topic == "geometri":
            pts = [(cx - r, cy + r), (cx + r, cy + r), (cx - r, cy - r)]
            draw.polygon(pts, fill=light_rgba, outline=accent_rgba, width=3)
            draw.text((cx - r - 10, cy + r - 8), "a", fill=accent_rgba, anchor="rb")
            draw.text((cx + r + 10, cy + r - 8), "b", fill=accent_rgba, anchor="lb")
            draw.text((cx - r - 10, cy - r + 8), "c", fill=accent_rgba, anchor="rt")

        elif topic == "fungsi_grafik":
            draw.line([(12, cy), (size - 12, cy)], fill=accent_rgba, width=2)
            draw.line([(cx, 12), (cx, size - 12)], fill=accent_rgba, width=2)
            arr = [(cx + int(x / r * r * 0.85), cy - int((x / r) ** 2 * r * 0.75)) for x in range(-r, r + 1)]
            draw.line(arr, fill=accent_rgba, width=3)

        elif topic == "peluang_statistika":
            bw = r // 4
            gap = 8
            heights = [int(r * 0.75), int(r * 0.95), int(r * 0.55)]
            colors = [(*accent, 200), (*accent, 220), (*accent, 150)]
            for i in range(3):
                x1 = cx - r + i * (bw + gap)
                y1 = cy + r
                y2 = y1 - heights[i]
                draw.rectangle([x1, y2, x1 + bw, y1], fill=colors[i], outline=accent_rgba, width=2)

        elif topic == "deret_angka":
            draw.line([(15, cy), (size - 15, cy)], fill=accent_rgba, width=3)
            spacing = 2 * r // 5
            dot_rad = 5
            for i in range(5):
                px = cx - 2 * spacing + i * spacing
                dr = dot_rad + i
                draw.ellipse([px - dr, cy - dr, px + dr, cy + dr], fill=accent_rgba)

        elif topic == "aritmatika_aljabar":
            draw.line([(cx - r, cy + 10), (cx + r, cy + 10)], fill=accent_rgba, width=3)
            draw.line([(cx - r, cy + 10), (cx - r, cy - 30)], fill=accent_rgba, width=2)
            draw.line([(cx + r, cy + 10), (cx + r, cy - 30)], fill=accent_rgba, width=2)
            draw.polygon([(cx - 7, cy + 10), (cx + 7, cy + 10), (cx, cy + 22)], fill=accent_rgba)
            draw.text((cx - r, cy - 40), "x+5=10", fill=accent_rgba, anchor="mt", font=ImageFont.truetype(FONT_BOLD, 16))

        _topic_image_cache[key] = img
    else:
        img = _topic_image_cache[key].copy()

    if opacity < 1.0:
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        img.putalpha(alpha)
    return img


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

def pick_category():
    keys = list(CATEGORY_WEIGHTS.keys())
    weights = [CATEGORY_WEIGHTS[k] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]

HOOK_HISTORY_FILE = "data/hook_history.json"

def get_hook(content_type):
    hooks = HOOK_TEMPLATES[content_type]
    history = _load_json(HOOK_HISTORY_FILE, [])
    recent_ids = {h["id"] for h in history[-5:]}
    available = [(i, h) for i, h in enumerate(hooks) if i not in recent_ids]
    if not available:
        available = list(enumerate(hooks))
    idx, chosen = random.choice(available)
    history.append({"id": idx, "hook": chosen, "used_at": datetime.now().isoformat()})
    _save_json(HOOK_HISTORY_FILE, history[-50:])
    return chosen

def get_cta():
    return random.choice(CTA_POOL)

def fix_exponents(text):
    if not text:
        return text
    text = re.sub(
        r"\^\{([^}]*)\}",
        lambda m: "".join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r"\^(\d+)",
        lambda m: "".join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r"\^\(([^)]*)\)",
        lambda m: "".join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r"\^([a-z])",
        lambda m: SUPERSCRIPT_MAP.get(m.group(1), m.group(1)),
        text,
    )
    return text

def fix_fractions(text):
    if not text:
        return text
    def _replace_frac(m):
        frac = m.group(0)
        if frac in FRACTION_MAP:
            return FRACTION_MAP[frac]
        num, den = frac.split("/")
        sup = "".join(SUPERSCRIPT_MAP.get(c, c) for c in num)
        sub = "".join(SUBSCRIPT_MAP.get(c, c) for c in den)
        return sup + "\u2044" + sub
    text = re.sub(r"(?<!\d)(\d+)/(\d+)(?!\d)", _replace_frac, text)
    return text

def generate_narasi(topic, history, content_type, category=None, max_retry=3):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    topic_label = TOPICS[topic]
    recent = history[-20:] if history else []

    if category is None:
        category = "cpns"
    cat = CATEGORIES.get(category, CATEGORIES["cpns"])

    if content_type == "quiz":
        prompt = f"""Buat 1 soal matematika untuk {cat['prompt_context']} dengan topik {topic_label}.

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
- {cat['prompt_context']}
- Jawaban harus sesuai dengan salah satu pilihan (teks lengkap)
- Setiap pilihan jawaban harus berupa nilai EKSAK, bukan pembulatan atau pendekatan — jawaban yang benar harus persis sama dengan salah satu pilihan
- JANGAN membuat pilihan jawaban yang hanya mendekati nilai sebenarnya; semua pilihan harus nilai eksak
- Jangan buat soal yang sama dengan soal-soal sebelumnya
- Soal sebelumnya: {json.dumps(recent, ensure_ascii=False)}
- Maksimal 3 kalimat untuk soal
- Penjelasan maksimal 4 kalimat, fokus pada trik mengerjakannya"""
    elif content_type == "fakta":
        prompt = f"""Buat 1 konten fakta matematika yang mengejutkan dan jarang diketahui orang, terkait topik {topic_label}. Konten ini ditujukan untuk {cat['prompt_context']}.

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
        prompt = f"""Buat 1 tips/trik cepat matematika untuk {cat['prompt_context']} dengan topik {topic_label}.

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
- Fokus pada trik yang bisa dipakai di {cat['prompt_context']}
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
            narasi["soal"] = fix_exponents(fix_fractions(narasi["soal"]))
            narasi["pilihan"] = [fix_exponents(fix_fractions(p)) for p in narasi["pilihan"]]
            narasi["jawaban"] = fix_exponents(fix_fractions(narasi["jawaban"]))
            narasi["penjelasan"] = fix_exponents(fix_fractions(narasi["penjelasan"]))
            if is_duplicate(narasi["soal"], history):
                print(f"[WARN] Duplicate soalan, retry {attempt}")
                continue
            if narasi["jawaban"] not in narasi["pilihan"]:
                print(f"[WARN] Jawaban not in pilihan after formatting, retry {attempt}")
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

def render_frame_soal(narasi, topic, output_path, content_type="quiz", category=None):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)

    topic_img = get_topic_image(topic, size=250, opacity=0.15)
    wx = IMG_WIDTH - 250 - 40
    wy = 700
    img.paste(topic_img, (wx, wy), topic_img)

    font_bold = ImageFont.truetype(FONT_BOLD, 72)
    font_reg = ImageFont.truetype(FONT_REGULAR, 54)
    font_soal = ImageFont.truetype(FONT_REGULAR, 75)
    font_badge = ImageFont.truetype(FONT_BOLD, 42)
    font_footer = ImageFont.truetype(FONT_REGULAR, 36)
    font_icon = ImageFont.truetype(FONT_BOLD, 54)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")
    topic_bg = hex_to_rgb(topic_accent)

    content_labels = {"quiz": "QUIZ CHALLENGE", "fakta": "FAKTA MATEMATIKA", "tips": "TIPS CEPAT"}
    content_label = content_labels.get(content_type, "SOAL MATEMATIKA")
    sub_labels = {"quiz": "Coba tebak! \U0001F9D0", "fakta": "Mind blowing! \U0001F92F", "tips": "Catat baik-baik! \U0001F4DD"}
    if category is None:
        category = "cpns"
    cat_sub = CATEGORIES.get(category, CATEGORIES["cpns"])["sub_label"]
    sub_label = sub_labels.get(content_type, cat_sub)

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

    soal_lines = wrap_text(narasi["soal"], font_soal, draw, IMG_WIDTH - 120)
    line_h = 108

    hint_top = IMG_HEIGHT - 180
    content_h = badge_h + 55 + len(soal_lines) * line_h
    available = hint_top - header_h
    y_offset = header_h + max(30, (available - content_h) // 2)

    badge_x = (IMG_WIDTH - badge_w) // 2
    badge_y = y_offset
    draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 22, topic_bg)
    draw.text((badge_x + badge_padding, badge_y + 8), f"\u2605 {topic_label}", fill="#FFFFFF", font=font_badge)

    text_y = badge_y + badge_h + 55
    for line in soal_lines:
        draw.text((IMG_WIDTH // 2, text_y), line, fill=SOAL_TEXT, font=font_soal, anchor="mt")
        text_y += line_h

    hint_y = IMG_HEIGHT - 180
    draw.text((IMG_WIDTH // 2, hint_y), "Jawaban di akhir video 👇", fill=FOOTER_TEXT, font=font_soal, anchor="mt")

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

def is_fraction(text):
    return bool(re.search(r'\d+/\d+', text))

def render_frame_pilihan(narasi, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)
    font_bold = ImageFont.truetype(FONT_BOLD, 66)
    font_pil = ImageFont.truetype(FONT_REGULAR, 57)
    font_pil_large = ImageFont.truetype(FONT_REGULAR, 74)
    font_footer = ImageFont.truetype(FONT_REGULAR, 36)
    font_icon = ImageFont.truetype(FONT_BOLD, 48)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")
    topic_bg = hex_to_rgb(topic_accent)

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.rounded_rectangle([0, header_h - 6, IMG_WIDTH, header_h + 6], radius=0, fill="#FF8C42")
    draw.text((IMG_WIDTH // 2, header_h // 2), "PILIHAN JAWABAN", fill=HEADER_TEXT, font=font_bold, anchor="mt")

    draw.text((IMG_WIDTH - 70, 35), "\u270F\uFE0F", fill="#FFE0B2", anchor="mm", font=font_icon)

    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    line_h = 75
    gap = 40

    boxes = []
    for i, pil in enumerate(narasi["pilihan"]):
        letter = chr(65 + i)
        if not pil.startswith(f"{letter}."):
            pil = f"{letter}.  {pil}"
        current_font = font_pil_large if is_fraction(pil) else font_pil
        lines = wrap_text(pil, current_font, draw, box_w - 80)
        box_h = max(120, len(lines) * line_h + 40)
        boxes.append((pil, lines, current_font, box_h))

    total_content_h = sum(b[3] for b in boxes) + (len(boxes) - 1) * gap
    footer_y = IMG_HEIGHT - 80
    available = footer_y - header_h - 60
    y_offset = header_h + 60 + max(20, (available - total_content_h) // 2)

    for i, (pil, lines, current_font, box_h) in enumerate(boxes):
        box_y = y_offset + i * (box_h + gap)
        draw_rounded_rect(draw, [margin_x, box_y, margin_x + box_w, box_y + box_h], 16, PILIHAN_BG)
        draw.rounded_rectangle([margin_x + 2, box_y + 2, margin_x + box_w - 2, box_y + box_h - 2], radius=14, fill=None, outline=topic_bg, width=2)
        draw.rounded_rectangle([margin_x, box_y, margin_x + 14, box_y + box_h], radius=16, fill=topic_bg)
        text_y_start = box_y + (box_h - len(lines) * line_h) // 2
        for j, line in enumerate(lines):
            draw.text((margin_x + 40, text_y_start + j * line_h), line, fill=PILIHAN_TEXT, font=current_font, anchor="lt")

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
    font_bold = ImageFont.truetype(FONT_BOLD, 66)
    font_jawab = ImageFont.truetype(FONT_BOLD, 75)
    font_penjelasan = ImageFont.truetype(FONT_REGULAR, 60)
    font_footer = ImageFont.truetype(FONT_REGULAR, 36)
    font_icon = ImageFont.truetype(FONT_BOLD, 48)

    topic_accent = TOPIC_BG.get(topic, "#FF8C42")

    header_h = 160
    draw.rounded_rectangle([0, 0, IMG_WIDTH, header_h], radius=0, fill=HEADER_BG)
    draw.rounded_rectangle([0, header_h - 6, IMG_WIDTH, header_h + 6], radius=0, fill="#FF8C42")
    draw.text((IMG_WIDTH // 2, header_h // 2), "JAWABAN & PEMBAHASAN", fill=HEADER_TEXT, font=font_bold, anchor="mt")

    draw.text((IMG_WIDTH - 70, 35), "\U0001F4A1", fill="#FFE0B2", anchor="mm", font=font_icon)

    margin_x = 100
    box_w = IMG_WIDTH - margin_x * 2
    jawab_text = f"\u2713  {narasi['jawaban']}"
    jawab_lines = wrap_text(jawab_text, font_jawab, draw, box_w - 80)
    line_h_jawab = 90
    jawab_box_h = max(120, len(jawab_lines) * line_h_jawab + 40)

    penjelasan_gap = 50
    penjelasan_lines = wrap_text(narasi["penjelasan"], font_penjelasan, draw, IMG_WIDTH - 120)
    line_h_penjelasan = 90

    content_h = jawab_box_h + penjelasan_gap + len(penjelasan_lines) * line_h_penjelasan
    footer_y = IMG_HEIGHT - 80
    available = footer_y - header_h - 60
    y_offset = header_h + 60 + max(20, (available - content_h) // 2)

    jawab_y = y_offset
    draw_rounded_rect(draw, [margin_x, jawab_y, margin_x + box_w, jawab_y + jawab_box_h], 16, JAWABAN_BG)
    draw.rounded_rectangle([margin_x + 2, jawab_y + 2, margin_x + box_w - 2, jawab_y + jawab_box_h - 2], radius=14, fill=None, outline=JAWABAN_ACCENT, width=2)
    draw.rounded_rectangle([margin_x, jawab_y, margin_x + 14, jawab_y + jawab_box_h], radius=16, fill=JAWABAN_ACCENT)
    jawab_text_y_start = jawab_y + (jawab_box_h - len(jawab_lines) * line_h_jawab) // 2
    for j, line in enumerate(jawab_lines):
        draw.text((margin_x + 40, jawab_text_y_start + j * line_h_jawab), line, fill=JAWABAN_TEXT, font=font_jawab, anchor="lt")

    penjelasan_y = jawab_y + jawab_box_h + penjelasan_gap
    for line in penjelasan_lines:
        draw.text((IMG_WIDTH // 2, penjelasan_y), line, fill=PENJELASAN_TEXT, font=font_penjelasan, anchor="mt")
        penjelasan_y += line_h_penjelasan

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

def render_frame_hook(hook_text, topic, output_path, hook_image_path=None):
    rotation = load_hook_bg_rotation()
    bg_color = HOOK_BG_COLORS[rotation["current_index"] % len(HOOK_BG_COLORS)]
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype(FONT_BOLD, 72)
    font_sub = ImageFont.truetype(FONT_REGULAR, 32)
    font_badge = ImageFont.truetype(FONT_BOLD, 28)

    accent = TOPIC_BG.get(topic, "#FF8C42")
    accent_rgb = hex_to_rgb(accent)

    overlay = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (*accent_rgb, 30))
    img.paste(overlay, (0, 0), overlay)

    # Load and scale hook image (70% width), render after text
    hook_img = None
    if hook_image_path:
        try:
            h_img = Image.open(hook_image_path).convert("RGBA")
            hw, hh = h_img.size
            target_w = int(IMG_WIDTH * 0.7)
            scale = target_w / hw
            hook_img = h_img.resize((target_w, int(hh * scale)), getattr(Image, 'Resampling', Image).LANCZOS)
        except Exception as e:
            print(f"[WARN] Hook image render failed: {e}")

    topic_label = TOPICS.get(topic, topic)
    bbox = draw.textbbox((0, 0), f"\u2728 {topic_label}", font=font_badge)
    badge_w = bbox[2] - bbox[0] + 30
    badge_h = bbox[3] - bbox[1] + 14
    badge_y = 60
    badge_x = (IMG_WIDTH - badge_w) // 2
    draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 20, accent_rgb)
    draw.text((badge_x + 15, badge_y + 7), f"\u2728 {topic_label}", fill="#FFFFFF", font=font_badge)

    hook_lines = wrap_text(hook_text, font_big, draw, IMG_WIDTH - 120)
    line_h = 90
    if hook_img:
        text_y = badge_y + badge_h + 60
        for line in hook_lines:
            draw.text((IMG_WIDTH // 2, text_y), line, fill="#FFFFFF", font=font_big, anchor="mt")
            text_y += line_h
        img_y = text_y + 50
        img_x = (IMG_WIDTH - hook_img.width) // 2
        img.paste(hook_img, (img_x, img_y), hook_img)
    else:
        total_h = len(hook_lines) * line_h
        start_y = (IMG_HEIGHT - total_h) // 2
        for line in hook_lines:
            draw.text((IMG_WIDTH // 2, start_y), line, fill="#FFFFFF", font=font_big, anchor="mt")
            start_y += line_h

    draw.text((IMG_WIDTH // 2, IMG_HEIGHT - 80), "Geser untuk jawaban \u25BC", fill="#94A3B8", font=font_sub, anchor="mt")

    next_index = (rotation["current_index"] + 1) % len(HOOK_BG_COLORS)
    save_hook_bg_rotation(next_index)
    img.save(output_path)
    return output_path


def load_hook_bg_rotation():
    default = {"current_index": 0, "updated_at": datetime.now().isoformat()}
    try:
        if os.path.exists(HOOK_BG_ROTATION_FILE):
            with open(HOOK_BG_ROTATION_FILE) as f:
                data = json.load(f)
            if "current_index" in data and isinstance(data["current_index"], int):
                return data
        return default
    except (json.JSONDecodeError, ValueError):
        return default


def save_hook_bg_rotation(index):
    data = {"current_index": index, "updated_at": datetime.now().isoformat()}
    os.makedirs("data", exist_ok=True)
    with open(HOOK_BG_ROTATION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def pick_product():
    """Deterministic product rotation by date + run hour.
    No file state needed — every CI run computes the same schedule."""
    product_dirs = sorted([
        d for d in os.listdir(PRODUCT_ASSETS_DIR)
        if os.path.isdir(os.path.join(PRODUCT_ASSETS_DIR, d))
    ]) if os.path.isdir(PRODUCT_ASSETS_DIR) else []

    if not product_dirs:
        print("[WARN] No product directories found in assets/shopee/")
        return None

    n_products = len(product_dirs)
    run_slots = {1: 0, 5: 1, 10: 2, 13: 3}
    current_hour = datetime.now().hour
    slot = run_slots.get(current_hour, 0)
    day_offset = date.today().toordinal() % n_products
    product_index = (slot + day_offset) % n_products

    product_name = product_dirs[product_index]
    product_path = os.path.join(PRODUCT_ASSETS_DIR, product_name)
    images = sorted([
        os.path.join(product_path, f)
        for f in os.listdir(product_path)
        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg"))
    ])

    if len(images) < 3:
        print(f"[WARN] Product '{product_name}' has only {len(images)} images (need 3)")
        return None

    print(f"[INFO] Selected product: {product_name} (slot {slot}, day_offset {day_offset})")
    return {"name": product_name, "images": images[:3]}


def pick_hook_image():
    hook_images = sorted([
        os.path.join(HOOK_ASSETS_DIR, f)
        for f in os.listdir(HOOK_ASSETS_DIR)
        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg"))
    ]) if os.path.isdir(HOOK_ASSETS_DIR) else []

    if not hook_images:
        print("[WARN] No hook images found in assets/hooks/")
        return None

    chosen = random.choice(hook_images)
    print(f"[INFO] Selected hook image: {chosen}")
    return chosen


def load_product_links():
    if not os.path.exists(PRODUCT_LINKS_FILE):
        print(f"[WARN] Product links file not found: {PRODUCT_LINKS_FILE}")
        return {}
    with open(PRODUCT_LINKS_FILE, "r") as f:
        links = json.load(f)
    return {entry["id_produk"]: entry for entry in links}


def get_link_for_product(product):
    links = load_product_links()
    if product is None:
        return None
    name = product.get("name")
    if not name or name not in links:
        print(f"[WARN] No link found for product: {name}")
        return None
    entry = links[name]
    return entry.get("link_komisi_ekstra", entry["link_produk"])


def render_product_slides(product, tmpdir):
    from moviepy import ImageClip

    slides = []
    for i, img_path in enumerate(product["images"]):
        try:
            frame_path = os.path.join(tmpdir, f"product_{i}.png")
            img = Image.open(img_path).convert("RGBA")
            img_w, img_h = img.size
            scale = IMG_WIDTH / img_w
            new_h = int(img_h * scale)
            img = img.resize((IMG_WIDTH, new_h), getattr(Image, 'Resampling', Image).LANCZOS)

            canvas = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0))
            y_offset = (IMG_HEIGHT - new_h) // 2
            canvas.paste(img, (0, y_offset), img if img.mode == "RGBA" else None)
            canvas.save(frame_path)

            slide = ImageClip(frame_path, duration=2)
            slides.append(slide)
        except Exception as e:
            print(f"[WARN] Failed to load product image {img_path}: {e}")
            continue
    return slides


def _generate_tts_sync(text, output_path, voice=TTS_VOICE, rate=TTS_RATE):
    """Synchronous helper for edge-tts generation."""
    try:
        if len(text) > TTS_MAX_CHARS:
            print(f"[WARN] TTS input truncated from {len(text)} to {TTS_MAX_CHARS} chars")
            text = text[:TTS_MAX_CHARS]
        tts_text = text.replace("+", " plus ")
        tts_text = tts_text.replace("\u00B2", " kuadrat ")
        tts_text = tts_text.replace("^2", " kuadrat ")
        async def _generate():
            communicate = edge_tts.Communicate(tts_text, voice, rate=rate)
            await asyncio.wait_for(communicate.save(output_path), timeout=TTS_TIMEOUT)
        asyncio.run(_generate())
        return output_path
    except asyncio.TimeoutError:
        print(f"[WARN] TTS generation timed out after {TTS_TIMEOUT}s for '{text[:50]}...'")
        return None
    except Exception as e:
        print(f"[WARN] TTS generation failed for '{text[:50]}...': {e}")
        return None


def _generate_voiceover_segments(narasi, hook_text, tmpdir):
    """Generate TTS audio for each video segment. Returns dict of {segment: AudioFileClip}."""
    from moviepy import AudioFileClip

    segments = {}
    audio_items = []

    if hook_text and hook_text.strip():
        path = os.path.join(tmpdir, "voice_hook.mp3")
        tts_hook = _EMOJI_RE.sub('', hook_text.strip()).rstrip('.,!?;: ')
        if tts_hook:
            result = _generate_tts_sync(tts_hook, path)
            if result:
                audio_items.append(("hook", path))

    soal_text = narasi.get("soal", "").strip()
    if soal_text:
        path = os.path.join(tmpdir, "voice_soal.mp3")
        result = _generate_tts_sync(soal_text, path)
        if result:
            audio_items.append(("soal", path))

    jawaban = narasi.get("jawaban", "").strip()
    penjelasan = narasi.get("penjelasan", "").strip()
    if jawaban:
        pembahasan_text = f"Jawaban yang benar adalah {jawaban}. {penjelasan}"
    else:
        pembahasan_text = penjelasan
    if pembahasan_text.strip():
        path = os.path.join(tmpdir, "voice_pembahasan.mp3")
        result = _generate_tts_sync(pembahasan_text.strip(), path)
        if result:
            audio_items.append(("pembahasan", path))

    for key, path in audio_items:
        try:
            clip = AudioFileClip(path)
            segments[key] = clip
        except Exception as e:
            print(f"[WARN] Failed to load voiceover audio for '{key}': {e}")

    return segments


def render_video(narasi, topic, filename, content_type="quiz", hook_text=None, product=None, category=None, hook_image_path=None):
    from moviepy import (
        ImageClip, AudioFileClip, CompositeAudioClip,
        concatenate_videoclips, concatenate_audioclips,
    )

    tmpdir = tempfile.mkdtemp()
    try:
        print("[TTS] Generating voiceover segments...")
        voice_segments = _generate_voiceover_segments(narasi, hook_text, tmpdir)

        hook_frame = os.path.join(tmpdir, "hook.png")
        frame1 = os.path.join(tmpdir, "frame1.png")
        frame2 = os.path.join(tmpdir, "frame2.png")
        frame3 = os.path.join(tmpdir, "frame3.png")

        clips = []
        audio_parts = []
        current_time = 0.0

        if hook_text:
            try:
                display_hook = _EMOJI_RE.sub('', hook_text).strip()
                render_frame_hook(display_hook, topic, hook_frame, hook_image_path)
                hook_dur = voice_segments["hook"].duration if "hook" in voice_segments else 2
                hook_clip = ImageClip(hook_frame, duration=hook_dur)
                clips.append(hook_clip)
                if "hook" in voice_segments:
                    audio_parts.append(voice_segments["hook"].with_start(current_time))
                current_time += hook_dur
                print(f"[INFO] Hook frame rendered ({hook_dur:.1f}s)")
            except Exception as e:
                print(f"[WARN] Hook render failed, skipping: {e}")

        render_frame_soal(narasi, topic, frame1, content_type, category)
        render_frame_pilihan(narasi, topic, frame2)
        render_frame_pembahasan(narasi, topic, frame3)

        soal_dur = voice_segments["soal"].duration if "soal" in voice_segments else MIN_SOAL_SECONDS
        clip1 = ImageClip(frame1, duration=max(soal_dur, MIN_SOAL_SECONDS))

        clip2 = ImageClip(frame2, duration=MIN_PILIHAN_SECONDS)

        pembahasan_dur = voice_segments["pembahasan"].duration if "pembahasan" in voice_segments else MIN_PEMBAHASAN_SECONDS
        clip3 = ImageClip(frame3, duration=max(pembahasan_dur, MIN_PEMBAHASAN_SECONDS))

        if "soal" in voice_segments:
            audio_parts.append(voice_segments["soal"].with_start(current_time))
        current_time += clip1.duration + clip2.duration
        if "pembahasan" in voice_segments:
            audio_parts.append(voice_segments["pembahasan"].with_start(current_time))

        clips.extend([clip1, clip2, clip3])

        if product is not None:
            try:
                product_slides = render_product_slides(product, tmpdir)
                if product_slides:
                    clips.extend(product_slides)
                    print(f"[INFO] Added {len(product_slides)} product slides from {product['name']}")
            except Exception as e:
                print(f"[WARN] Product slide render failed, skipping: {e}")
        else:
            print("[INFO] No product slides added (assets not available or insufficient)")

        video = concatenate_videoclips(clips, method="compose")

        bgm_files = glob.glob("audio/*.mp3")
        if bgm_files or audio_parts:
            audio_sources = []
            total_duration = video.duration

            if bgm_files:
                bgm_path = random.choice(bgm_files)
                print(f"[INFO] Using BGM: {bgm_path}")
                bgm = AudioFileClip(bgm_path)
                if bgm.duration > total_duration:
                    bgm = bgm.subclipped(0, total_duration)
                else:
                    repeats = int(total_duration / bgm.duration) + 1
                    bgm = concatenate_audioclips([bgm] * repeats).subclipped(0, total_duration)
                bgm = bgm.with_volume_scaled(0.15)
                audio_sources.append(bgm)

            if audio_parts:
                audio_sources.extend(audio_parts)

            if len(audio_sources) == 1:
                final_audio = audio_sources[0]
            else:
                final_audio = CompositeAudioClip(audio_sources)
                final_audio = final_audio.with_duration(total_duration)

            video = video.with_audio(final_audio)
        else:
            print("[INFO] No audio sources, rendering without audio")

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

def build_caption(narasi, topic, content_type, hook, category=None, cta=None):
    topic_label = TOPICS.get(topic, topic)
    if cta is None:
        cta = get_cta()
    if category is None:
        category = "cpns"
    cat_pool = CATEGORIES.get(category, CATEGORIES["cpns"])["hashtag_pool"]
    merged_pool = list(HASHTAG_POOL) + [h for h in cat_pool if h not in HASHTAG_POOL]
    tags = " ".join(random.sample(merged_pool, k=min(6, len(merged_pool))))

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

POSTING_SCHEDULE = {"paused_hours": [], "preferred_hours": list(range(24))}


# NOTE: post_to_facebook_profile() — disabled until FB_USER_TOKEN/FB_USER_ID are ready


def check_stagger():
    """Skip post if last post to the other account was less than STAGGER_MIN_HOURS ago."""
    if not os.path.exists(STAGGER_FILE):
        return True
    try:
        with open(STAGGER_FILE) as f:
            data = json.load(f)
        last_time = datetime.fromisoformat(data.get("last_post_time", ""))
        hours_since = (datetime.now() - last_time).total_seconds() / 3600
        if hours_since < STAGGER_MIN_HOURS:
            print(f"[STAGGER] Only {hours_since:.1f}h since last post to other account — skipping (min {STAGGER_MIN_HOURS}h)")
            return False
        return True
    except (ValueError, KeyError, FileNotFoundError):
        return True


def record_stagger():
    """Record this post time for staggering."""
    os.makedirs("data", exist_ok=True)
    with open(STAGGER_FILE, "w") as f:
        json.dump({"last_post_time": datetime.now().isoformat()}, f)


def pick_content_type_for_account():
    """80/20 content type selection per account strategy."""
    roll = random.random()
    if roll < 0.8:
        weights = PAGE_MAJOR_CT_WEIGHTS
    else:
        weights = PAGE_MINOR_CT_WEIGHTS
    types = list(weights.keys())
    w = [weights[t] for t in types]
    return random.choices(types, weights=w, k=1)[0]


def pick_category_for_account():
    """80/20 category selection: serious exam themes vs lighter."""
    roll = random.random()
    if roll < 0.8:
        pool = PAGE_MAJOR_THEMES
    else:
        pool = PAGE_MINOR_THEMES
    keys = list(CATEGORY_WEIGHTS.keys())
    available = [k for k in pool if k in keys]
    if not available:
        available = keys
    return random.choice(available)


def load_and_apply_learning_config():
    """Load learning_config.json and override global constants."""
    if not os.path.exists(LEARNING_CONFIG_FILE):
        return None
    try:
        with open(LEARNING_CONFIG_FILE) as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load learning config: {e}")
        return None

    global CONTENT_TYPE_WEIGHTS, HOOK_TEMPLATES, CTA_POOL, HASHTAG_POOL, CATEGORY_WEIGHTS, POSTING_SCHEDULE
    changed = []
    if "content_type_weights" in cfg and cfg["content_type_weights"]:
        CONTENT_TYPE_WEIGHTS = cfg["content_type_weights"]
        changed.append("weights")
    if "hook_templates" in cfg and cfg["hook_templates"]:
        HOOK_TEMPLATES = cfg["hook_templates"]
        changed.append("hooks")
    if "cta_pool" in cfg and cfg["cta_pool"]:
        CTA_POOL = cfg["cta_pool"]
        changed.append("CTA")
    if "hashtag_pool" in cfg and cfg["hashtag_pool"]:
        HASHTAG_POOL = cfg["hashtag_pool"]
        changed.append("hashtags")
    if "category_weights" in cfg and cfg["category_weights"]:
        CATEGORY_WEIGHTS = cfg["category_weights"]
        changed.append("category weights")
    if "posting_schedule" in cfg and cfg["posting_schedule"]:
        ps = cfg["posting_schedule"]
        POSTING_SCHEDULE["paused_hours"] = ps.get("paused_hours", [])
        POSTING_SCHEDULE["preferred_hours"] = ps.get("preferred_hours", list(range(24)))
        changed.append("posting schedule")
        current_hour = datetime.now().hour
        if current_hour in POSTING_SCHEDULE["paused_hours"]:
            print(f"[SL][WARN] Current hour ({current_hour}:00) is in paused range — consider if this run is intentional")
    if "content_pillar_weights" in cfg and cfg["content_pillar_weights"]:
        print(f"[SL] Content pillar weights: {cfg['content_pillar_weights']}")
        changed.append("content pillars")
    if changed:
        print(f"[SL] Applied learning config: {', '.join(changed)}")
    return cfg


def process_telegram_csv():
    """Check Telegram for CSV file uploads and run self-learning."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    last_id = 0
    mode_data = {}
    if os.path.exists(MODE_FILE):
        with open(MODE_FILE) as f:
            mode_data = json.load(f)
            last_id = mode_data.get("last_update_id", 0)

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 5},
        )
        if not resp.ok:
            return

        for upd in resp.json().get("result", []):
            uid = upd["update_id"]
            if uid <= last_id:
                continue
            msg = upd.get("message") or {}
            doc = msg.get("document")
            if doc and doc.get("file_name", "").lower().endswith(".csv"):
                print(f"[SL] CSV detected: {doc['file_name']}")
                tmp_path = f"/tmp/sl_csv_{doc['file_id']}.csv"
                if download_telegram_file(doc["file_id"], tmp_path):
                    try:
                        from self_learning import run_self_learning
                        result = run_self_learning(tmp_path)
                        summary = _format_learning_summary(result)
                        notify_telegram(summary)
                    except Exception as e:
                        notify_telegram(f"[SL] Self-learning FAILED: {e}")
                        print(f"[SL] Error: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
            elif msg.get("text"):
                text = msg["text"]
                if any(kw in text.lower() for kw in ["laporan", "analisis performa", "ringkasan eksekutif", "total views"]):
                    print(f"[SL] Report text detected, parsing...")
                    try:
                        from self_learning import run_self_learning_from_report
                        result = run_self_learning_from_report(text[:10000])
                        summary = _format_learning_summary(result)
                        notify_telegram(f"[SL] Report processed:\n{summary}")
                    except Exception as e:
                        notify_telegram(f"[SL] Report processing FAILED: {e}")
                        print(f"[SL] Error: {e}")

    except Exception as e:
        print(f"[WARN] process_telegram_csv failed: {e}")


def _format_learning_summary(result: dict) -> str:
    if result.get("status") == "skipped":
        reason = result.get("reason", "unknown")
        return f"[SL] Self-learning skipped: {reason}"
    lines = ["[SL] Self-learning selesai!"]
    lines.append(f"Records diproses: {result.get('records_parsed', 0)}")
    cls = result.get("classifications", {})
    if cls:
        lines.append(f"Viral: {cls.get('viral', 0)} | Good: {cls.get('good', 0)} | Bad: {cls.get('bad', 0)}")
    changes = result.get("changes_made", [])
    if changes:
        lines.append(f"Perubahan: {', '.join(changes)}")
    return "\n".join(lines)


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

            from self_learning.csv_parser import _parse_csv_via_gemini as _gemini_parse
            records = _gemini_parse(open(dest_path).read())
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

def run_self_learning_review():
    print(f"[INFO] Running weekly self-learning review...")

    growth = load_growth()
    analytics = load_analytics()

    tracked = [a for a in analytics if a.get("source") in ("api", "csv_export")]

    if len(tracked) >= 3:
        from self_learning.classifier import classify_records
        from self_learning.learning_engine import compute_learning_config, load_learning_config, save_learning_config

        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent = [a for a in tracked if a.get("fetched_at", "") >= seven_days_ago]
        if not recent:
            recent = tracked[-10:]

        classifications = classify_records(recent)

        viral_count = sum(1 for c in classifications if c["classification"] == "viral")
        good_count = sum(1 for c in classifications if c["classification"] == "good")
        bad_count = sum(1 for c in classifications if c["classification"] == "bad")

        if len(classifications) >= 3:
            current_config = load_learning_config("self_learning/learning_config.json")
            new_config, iteration = compute_learning_config(current_config, classifications, recent)
            if iteration:
                save_learning_config("self_learning/learning_config.json", new_config)
                from self_learning import _load_json, _save_json
                all_iters = _load_json("data/learning_iteration.json", [])
                all_iters.append(iteration)
                _save_json("data/learning_iteration.json", all_iters)
                print(f"[SL] Review updated config: {iteration['variable_changed']}")

        classification_msg = f"Viral: {viral_count} | Good: {good_count} | Bad: {bad_count}"
    else:
        classification_msg = f"Data analytics <3 records ({len(tracked)}), skip learning"
        print(f"[SL] {classification_msg}")

    follower_count = growth[-1]["follower_count"] if growth else 0
    week1_growth = sum(r["daily_growth"] for r in growth[:7]) if len(growth) >= 7 else 0

    msg_lines = [
        f"\U0001F4CA Weekly Review (7 hari)",
        f"Followers: {follower_count}",
        f"Week growth: +{week1_growth}",
        f"Analytics: {len(tracked)} records",
        f"{classification_msg}",
    ]

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

    load_and_apply_learning_config()
    process_telegram_csv()

    current_hour = datetime.now().hour
    if current_hour in POSTING_SCHEDULE["paused_hours"]:
        print(f"[SKIP] Current hour ({current_hour}:00) is in paused range {POSTING_SCHEDULE['paused_hours']}. Skipping post.")
        notify_telegram(f"\u23F0 Post skipped: jam {current_hour}:00 dalam paused_hours {POSTING_SCHEDULE['paused_hours']}")
        return

    history = load_history()
    print(f"[INFO] History loaded: {len(history)} entries")

    if not check_stagger():
        return

    category = pick_category_for_account()
    cat_label = CATEGORIES.get(category, CATEGORIES["cpns"])["label"]
    print(f"[INFO] Selected category: {category} ({cat_label})")

    topic = pick_topic(history)
    print(f"[INFO] Selected topic: {topic} ({TOPICS.get(topic)})")

    content_type = pick_content_type_for_account()
    print(f"[INFO] Content type: {content_type}")

    hook = get_hook(content_type)
    cta = get_cta()
    hook_image = pick_hook_image()
    print(f"[INFO] Hook: {hook}")
    if hook_image:
        print(f"[INFO] Hook Image: {hook_image}")

    narasi = generate_narasi(topic, history, content_type, category)
    print(f"[INFO] Content generated: {narasi['soal'][:60]}...")

    video_filename = f"reels_{category}_{topic}_{today_str}_{datetime.now().strftime('%H%M%S')}.mp4"
    print(f"[INFO] Rendering video...")
    product = pick_product()
    render_video(narasi, topic, video_filename, content_type, hook_text=hook, product=product, category=category, hook_image_path=hook_image)
    print(f"[OK] Video rendered: {video_filename}")

    caption = build_caption(narasi, topic, content_type, hook, category, cta=cta)
    compliance_check(caption)

    product_link_msg = get_link_for_product(product)
    if product_link_msg:
        print(f"[INFO] Product link found: {product_link_msg[:60]}...")
    else:
        print("[INFO] No product link available")

    post_mode = check_telegram_mode()
    print(f"[INFO] Post mode: {post_mode.upper()}")

    post_id = None
    if post_mode == "telegram":
        if product_link_msg:
            caption = caption + f"\n\n🔗 {product_link_msg}"
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
        "category": category,
        "account_type": ACCOUNT_TYPE,
        "format": CONTENT_FORMAT,
        "theme": category,
        "hook_used": hook,
        "cta_used": cta,
        "hashtags_used": caption.split("\n\n")[-1] if "\n\n" in caption else "",
    }
    if post_id:
        entry["post_id"] = post_id
    history.append(entry)
    save_history(history)
    record_stagger()
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
