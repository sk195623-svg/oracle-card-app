import os
import json
import random
import base64
import re
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# =========================
# 基本設定
# =========================
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"
IMAGE_DIR.mkdir(exist_ok=True)

CARDS_JSON = BASE_DIR / "cards.json"

st.set_page_config(
    page_title="Oracle Card Reader",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY) if API_KEY else None


# =========================
# CSS
# =========================
def apply_custom_css():
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(180deg, #fffafc 0%, #f8fbff 100%);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    h1, h2, h3 {
        color: #44334d;
        letter-spacing: 0.02em;
    }

    .soft-card {
        background: rgba(255,255,255,0.88);
        border: 1px solid #eee4f3;
        border-radius: 20px;
        padding: 1.2rem;
        box-shadow: 0 8px 24px rgba(95, 70, 120, 0.08);
        margin-bottom: 1rem;
    }

    .result-card {
        background: linear-gradient(180deg, #ffffff 0%, #fcf8ff 100%);
        border: 1px solid #eadcf3;
        border-radius: 22px;
        padding: 1.2rem;
        box-shadow: 0 10px 28px rgba(110, 82, 138, 0.10);
        margin-bottom: 1.2rem;
    }

    .card-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #50325f;
        margin-bottom: 0.5rem;
    }

    .card-message {
        font-size: 1rem;
        line-height: 1.8;
        color: #4e4654;
        background: #fff;
        padding: 0.9rem 1rem;
        border-radius: 14px;
        border: 1px solid #f0e8f6;
    }

    .section-label {
        font-size: 0.95rem;
        font-weight: 700;
        color: #7e5f94;
        margin-bottom: 0.4rem;
    }

    .history-box {
        background: #ffffff;
        border: 1px solid #ebe6f0;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid #d9c6e6;
        padding: 0.65rem 1rem;
        background: linear-gradient(180deg, #ffffff 0%, #f8efff 100%);
        color: #4a2f59;
    }

    .stButton > button:hover {
        border: 1px solid #c7abd9;
        color: #3d234d;
    }

    .stDownloadButton > button {
        border-radius: 12px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fbf7ff 0%, #f5f9ff 100%);
        border-right: 1px solid #eee7f5;
    }
    </style>
    """, unsafe_allow_html=True)


apply_custom_css()


# =========================
# 補助
# =========================
def new_card_id() -> str:
    return f"card_{uuid.uuid4().hex[:12]}"


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def make_safe_filename(name: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]+', "_", name)
    safe = re.sub(r"\s+", "_", safe).strip("._ ")
    return safe or "card"


def ensure_card_id(card: Dict) -> Dict:
    if not str(card.get("id", "")).strip():
        card["id"] = new_card_id()
    return card


def ensure_cards_have_ids(cards: List[Dict]) -> List[Dict]:
    changed = False
    for card in cards:
        if not str(card.get("id", "")).strip():
            card["id"] = new_card_id()
            changed = True
    if changed:
        save_cards(cards)
    return cards


# =========================
# 画像パス安全処理
# =========================
def resolve_image_path(image_path: str) -> str:
    if not image_path:
        return ""

    try:
        p = Path(str(image_path))

        if p.is_absolute():
            return str(p) if p.exists() else ""

        abs_path = (BASE_DIR / p).resolve()
        return str(abs_path) if abs_path.exists() else ""
    except Exception:
        return ""


def get_display_image_path(card: dict) -> str:
    candidates = [
        card.get("card_image", ""),
        card.get("image", ""),
    ]

    for path in candidates:
        resolved = resolve_image_path(path)
        if resolved:
            return resolved

    return ""


# =========================
# セッション
# =========================
def init_session_state():
    if "history" not in st.session_state:
        st.session_state["history"] = []

    if "last_result_type" not in st.session_state:
        st.session_state["last_result_type"] = ""

    if "last_result_cards" not in st.session_state:
        st.session_state["last_result_cards"] = []

    if "last_ai_text" not in st.session_state:
        st.session_state["last_ai_text"] = ""

    if "ai_card_theme" not in st.session_state:
        st.session_state["ai_card_theme"] = "やさしい癒し"

    if "show_sequence_done" not in st.session_state:
        st.session_state["show_sequence_done"] = False

    if "is_mobile" not in st.session_state:
        st.session_state["is_mobile"] = False


# =========================
# データ入出力
# =========================
def load_cards() -> List[Dict]:
    if not CARDS_JSON.exists():
        return []

    try:
        with open(CARDS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return ensure_cards_have_ids(data)
    except Exception:
        return []


def save_cards(cards: List[Dict]) -> None:
    normalized_cards = [ensure_card_id(dict(card)) for card in cards]
    with open(CARDS_JSON, "w", encoding="utf-8") as f:
        json.dump(normalized_cards, f, ensure_ascii=False, indent=2)


def ensure_sample_cards() -> None:
    if CARDS_JSON.exists():
        cards = load_cards()
        if cards:
            save_cards(cards)
            return

    sample_cards = [
        {"id": new_card_id(), "name": "月のしずく", "type": "heal",  "message": "静かな時間の中に、あなたへの答えがやさしく落ちてきます。急がず、心の声を聞いてください。", "image": ""},
        {"id": new_card_id(), "name": "光の扉",  "type": "heal", "message": "新しい流れが始まろうとしています。少しの勇気が、未来の扉を開きます。", "image": ""},
        {"id": new_card_id(), "name": "風の導き",  "type": "heal", "message": "変化は恐れるものではなく、あなたを新しい場所へ運ぶ追い風です。", "image": ""},
        {"id": new_card_id(), "name": "星の約束", "type": "heal",  "message": "願いはすでに宇宙へ届いています。信じる気持ちを持ち続けてください。", "image": ""},
        {"id": new_card_id(), "name": "花ひらく心", "type": "heal",  "message": "優しさを自分にも向けるとき、心は自然にひらいていきます。", "image": ""},
        {"id": new_card_id(), "name": "朝の祝福", "type": "heal",  "message": "今日という一日は、あなたに新しい祝福を届けるために始まっています。", "image": ""},
        {"id": new_card_id(), "name": "水鏡",  "type": "heal", "message": "感情を否定せず映してみましょう。そこに大切な本音があります。", "image": ""},
        {"id": new_card_id(), "name": "虹の橋",  "type": "heal", "message": "今の迷いは、次の希望へ渡るための途中にあります。安心して進んでください。", "image": ""},
        {"id": new_card_id(), "name": "大地の抱擁", "type": "heal",  "message": "足元を整えれば、運は自然と安定します。まずは日常を大切に。", "image": ""},
        {"id": new_card_id(), "name": "天使のささやき",  "type": "heal", "message": "見えない助けはすぐそばにあります。ひとりで抱え込まなくて大丈夫です。", "image": ""}
    ]
    save_cards(sample_cards)


# =========================
# 共通処理
# =========================
def save_history(title: str):
    st.session_state["history"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title": title
    })


def display_history(history_list):
    if not history_list:
        st.info("まだ履歴はありません。")
        return

    for item in reversed(history_list):
        st.markdown(
            f"""
            <div class="history-box">
                <b>{item.get("time", "")}</b><br>
                {item.get("title", "")}
            </div>
            """,
            unsafe_allow_html=True
        )


def find_card_index(cards: List[Dict], target: Dict) -> int:
    target_id = str(target.get("id", "")).strip()
    if target_id:
        for i, card in enumerate(cards):
            if str(card.get("id", "")).strip() == target_id:
                return i

    target_name = normalize_text(target.get("name", ""))
    target_message = normalize_text(target.get("message", ""))

    for i, card in enumerate(cards):
        if (
            normalize_text(card.get("name", "")) == target_name
            and normalize_text(card.get("message", "")) == target_message
        ):
            return i
    return -1


def normalize_card_paths():
    cards = load_cards()
    changed = 0

    for card in cards:
        for key in ["image", "card_image"]:
            p = str(card.get(key, "")).strip()
            if not p:
                continue

            p2 = p.replace("\\", "/")

            if "/images/" in p2:
                p2 = "images/" + p2.split("/images/", 1)[1]
            elif p2.startswith("images/"):
                pass
            else:
                continue

            if card.get(key) != p2:
                card[key] = p2
                changed += 1

    save_cards(cards)
    return changed


def clean_missing_image_paths():
    cards = load_cards()
    changed = 0

    for card in cards:
        for key in ["image", "card_image"]:
            path = str(card.get(key, "")).strip()
            if not path:
                continue

            resolved = resolve_image_path(path)
            if not resolved:
                card[key] = ""
                changed += 1

    save_cards(cards)
    return changed


def optimize_all_images():
    count = 0

    for p in IMAGE_DIR.glob("*"):
        if p.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
            continue

        try:
            optimize_image_file(str(p))
            count += 1
        except Exception:
            pass

    return count


def delete_unused_images():
    cards = load_cards()
    used_files = set()

    for card in cards:
        for key in ["image", "card_image"]:
            path = str(card.get(key, "")).strip()
            if not path:
                continue

            resolved = resolve_image_path(path)
            if resolved:
                used_files.add(str(Path(resolved).resolve()))

    deleted = 0

    for p in IMAGE_DIR.glob("*"):
        if p.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
            continue

        abs_p = str(p.resolve())
        if abs_p not in used_files:
            try:
                p.unlink()
                deleted += 1
            except Exception:
                pass

    return deleted
    return changed


# =========================
# 画像カード作成
# =========================
def get_japanese_font(size: int):
    font_candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


def create_card_design(
    image_path: str,
    card_name: str,
    output_path: Optional[str] = None
) -> str:
    base_img = Image.open(image_path).convert("RGB")

    card_width = 900
    card_height = 1500
    margin = 36
    title_area_h = 180
    image_area_h = card_height - margin * 2 - title_area_h

    card = Image.new("RGB", (card_width, card_height), "white")
    draw = ImageDraw.Draw(card)

    target_w = card_width - margin * 2
    target_h = image_area_h

    img = base_img.copy()
    img.thumbnail((target_w, target_h))

    paste_x = (card_width - img.width) // 2
    paste_y = margin + (target_h - img.height) // 2
    card.paste(img, (paste_x, paste_y))

    draw.rounded_rectangle(
        [(8, 8), (card_width - 8, card_height - 8)],
        radius=28,
        outline=(180, 160, 120),
        width=6
    )

    draw.rounded_rectangle(
        [(22, 22), (card_width - 22, card_height - 22)],
        radius=24,
        outline=(220, 205, 170),
        width=2
    )

    title_top = card_height - title_area_h - margin
    title_bottom = card_height - margin

    draw.rounded_rectangle(
        [(margin, title_top), (card_width - margin, title_bottom)],
        radius=24,
        fill=(248, 244, 236),
        outline=(210, 195, 160),
        width=3
    )

    title_font = get_japanese_font(52)
    bbox = draw.textbbox((0, 0), card_name, font=title_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    text_x = (card_width - text_w) // 2
    text_y = title_top + (title_area_h - text_h) // 2 - 8

    draw.text((text_x, text_y), card_name, font=title_font, fill=(70, 60, 45))

    if output_path is None:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_card.png")

    card.save(output_path)
    return output_path


# =========================
# AIテキスト生成
# =========================
def build_card_generation_prompt(theme: str) -> str:
    return f"""
あなたはオラクルカード作家です。
やさしく、癒しがあり、前向きで、少し神秘的で、ほんの少しユーモアのあるカードを作ってください。

テーマ: {theme}

出力ルール:
- 日本語
- カード名は短く美しい表現
- メッセージは60〜120文字程度
- JSONのみで出力
- 形式は必ず以下:
{{"name":"カード名","message":"メッセージ"}}
""".strip()


def normalize_card_type(card_type: str) -> str:
    if not card_type:
        return "guide"

    t = str(card_type).strip().lower()

    if t in ["guide", "guidance", "導き"]:
        return "guide"
    if t in ["warn", "warning", "警告"]:
        return "warn"
    if t in ["heal", "healing", "回復", "癒し"]:
        return "heal"
    if t in ["shift", "change", "変化", "転換"]:
        return "shift"

    return "guide"


def build_cards_text(cards: List[Dict]) -> str:
    lines = []
    type_labels = {
        "guide": "導き",
        "warn": "警告",
        "heal": "回復",
        "shift": "変化"
    }

    for c in cards:
        name = c.get("name", "名称未設定")
        message = c.get("message", "")
        card_type = normalize_card_type(c.get("type", "guide"))
        jp_type = type_labels.get(card_type, "導き")
        lines.append(f"- {name}（{jp_type}）: {message}")

    return "\n".join(lines)


def build_one_card_prompt(card: Dict, question: str = "") -> str:
    name = card.get("name", "名称未設定")
    message = card.get("message", "")
    card_type = normalize_card_type(card.get("type", "guide"))

    type_meaning = {
        "guide": "導き。前に進むヒント",
        "warn": "警告。やりすぎや見落としへの注意",
        "heal": "回復。休息、癒し、心を整える",
        "shift": "変化。流れの切り替わり、転換点"
    }.get(card_type, "導き。前に進むヒント")

    prompt = f"""
あなたは「微睡（まどろみ）の魔導書」に宿る、古き魔法使いです。
相談者の心にそっと灯りをともすように、神秘的で、やさしく、少しユーモアのある言葉でリーディングしてください。

【話し方のルール】
- やさしい口調で話す
- 神秘的だが難しすぎない
- 少しだけクスッとする、やわらかなユーモアを入れる
- 不安をあおりすぎない
- 断定しすぎない
- 最後は安心感のある言葉で締める

【相談内容】
{question.strip() if question and question.strip() else "相談内容は特に書かれていません。今の相談者に必要なメッセージをやさしく読んでください。"}

【引かれたカード】
{name}
役割: {type_meaning}
カードの言葉: {message}

【出力形式】
【カードのささやき】
2〜4文で、このカードが今伝えたいことを神秘的に、やさしく述べてください。

【今日の小さな魔法】
今日すぐできる小さな行動を、1〜2個、やさしく提案してください。

【魔法のことば】
短く印象的な一言で締めてください。

【禁止】
- 強い決めつけ
- 恐怖をあおる表現
- 説教っぽい言い方
- 世界観を壊す現実的すぎる説明
"""
    return prompt.strip()


def build_three_card_prompt(cards: List[Dict], question: str = "") -> str:
    labels = ["過去", "現在", "未来"]
    type_labels = {
        "guide": "導き",
        "warn": "警告",
        "heal": "回復",
        "shift": "変化"
    }

    lines = []
    for i, c in enumerate(cards[:3]):
        name = c.get("name", "名称未設定")
        message = c.get("message", "")
        card_type = normalize_card_type(c.get("type", "guide"))
        label = labels[i] if i < len(labels) else f"カード{i+1}"
        jp_type = type_labels.get(card_type, "導き")
        lines.append(f"{label}: {name}（{jp_type}）: {message}")

    cards_text = "\n".join(lines)

    prompt = f"""
あなたは「微睡（まどろみ）の魔導書」に宿る、古き魔法使いです。
3枚のカードを、過去・現在・未来の流れとして読み解いてください。
相談者の心をやさしく整えるように、神秘的で、少しユーモアのある語り口で伝えてください。

【話し方のルール】
- やさしい口調で話す
- 神秘的だが難しすぎない
- 少しだけクスッとする、やわらかなユーモアを入れる
- 不安をあおりすぎない
- 断定しすぎない
- 最後は安心感のある言葉で締める

【相談内容】
{question.strip() if question and question.strip() else "相談内容は特に書かれていません。3枚の流れから、今必要なメッセージをやさしく読んでください。"}

【引かれたカード】
{cards_text}

【出力形式】
【物語の流れ】
過去→現在→未来の流れを、つながりのある物語としてやさしく説明してください。

【いま心に起きていること】
相談者の今の状態を、やさしく整理するように伝えてください。

【未来へ向けた小さな魔法】
今日からできる小さな行動を1〜3個、具体的に提案してください。

【魔法のことば】
短く印象的な一言で締めてください。

【禁止】
- 強い決めつけ
- 恐怖をあおる表現
- 説教っぽい言い方
- 世界観を壊す現実的すぎる説明
"""
    return prompt.strip()


def build_general_reading_prompt(cards: List[Dict], question: str = "") -> str:
    cards_text = build_cards_text(cards)

    prompt = f"""
あなたは「微睡（まどろみ）の魔導書」に宿る、古き魔法使いです。
相談者の心にそっと灯りをともすように、神秘的で、やさしく、少しユーモアのある言葉で総合リーディングしてください。

【話し方のルール】
- やさしい口調で話す
- 神秘的だが難しすぎない
- 少しだけクスッとする、やわらかなユーモアを入れる
- 不安をあおりすぎない
- 断定しすぎない
- 最後は安心感のある言葉で締める

【カードの役割】
- guide = 導き。前に進むヒント
- warn = 警告。やりすぎや見落としへの注意
- heal = 回復。休息、癒し、心を整える
- shift = 変化。流れの切り替わり、転換点

【相談内容】
{question.strip() if question and question.strip() else "相談内容は特に書かれていません。カード全体から、今必要なメッセージをやさしく読んでください。"}

【引かれたカード一覧】
{cards_text}

【リーディングで行うこと】
1. カード全体から見えるテーマをまとめる
2. 今の相談者の心の状態をやさしく読み解く
3. 今日からできる小さな行動を提案する
4. 最後に短い「魔法のことば」で締める

【出力形式】
【全体の流れ】
2〜5文で、カード全体のテーマをまとめてください。

【いまの心の状態】
相談者の気持ちを整理するように、やさしく読み解いてください。

【今日の小さな魔法】
今日すぐできる行動を1〜3個、具体的に提案してください。

【魔法のことば】
短く印象的な一言で締めてください。

【禁止】
- 強い決めつけ
- 恐怖をあおる表現
- 説教っぽい言い方
- 世界観を壊す現実的すぎる説明
"""
    return prompt.strip()


def generate_ai_reading(prompt: str) -> str:
    if client is None:
        return "OPENAI_API_KEY が未設定です。"

    try:
        response = client.responses.create(
            model="gpt-5",
            input=prompt
        )

        if hasattr(response, "output_text") and response.output_text:
            return response.output_text.strip()

        return "AIリーディングを取得できませんでした。"

    except Exception as e:
        return f"AIリーディング生成エラー: {e}"


def build_general_reading_prompt(cards: List[Dict], question: str = "") -> str:
    cards_text = build_cards_text(cards)

    prompt = f"""
あなたは「微睡（まどろみ）の魔導書」に宿る、古き魔法使いです。
相談者の心にそっと灯りをともすように、神秘的で、やさしく、少しユーモアのある言葉で総合リーディングしてください。

【話し方のルール】
- やさしい口調で話す
- 神秘的だが難しすぎない
- 少しだけクスッとする、やわらかなユーモアを入れる
- 不安をあおりすぎない
- 断定しすぎない
- 最後は安心感のある言葉で締める

【カードの役割】
- guide = 導き。前に進むヒント
- warn = 警告。やりすぎや見落としへの注意
- heal = 回復。休息、癒し、心を整える
- shift = 変化。流れの切り替わり、転換点

【相談内容】
{question.strip() if question and question.strip() else "相談内容は特に書かれていません。カード全体から、今必要なメッセージをやさしく読んでください。"}

【引かれたカード一覧】
{cards_text}

【リーディングで行うこと】
1. カード全体から見えるテーマをまとめる
2. 今の相談者の心の状態をやさしく読み解く
3. 今日からできる小さな行動を提案する
4. 最後に短い「魔法のことば」で締める

【出力形式】
【全体の流れ】
2〜5文で、カード全体のテーマをまとめてください。

【いまの心の状態】
相談者の気持ちを整理するように、やさしく読み解いてください。

【今日の小さな魔法】
今日すぐできる行動を1〜3個、具体的に提案してください。

【魔法のことば】
短く印象的な一言で締めてください。

【禁止】
- 強い決めつけ
- 恐怖をあおる表現
- 説教っぽい言い方
- 世界観を壊す現実的すぎる説明
"""
    return prompt.strip()


def generate_ai_reading(prompt: str) -> str:
    if client is None:
        return "OPENAI_API_KEY が未設定です。"

    try:
        response = client.responses.create(
            model="gpt-5",
            input=prompt
        )

        if hasattr(response, "output_text") and response.output_text:
            return response.output_text.strip()

        return "AIリーディングを取得できませんでした。"

    except Exception as e:
        return f"AIリーディング生成エラー: {e}"




def generate_ai_card(theme: str) -> Dict:
    if client is None:
        raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    response = client.responses.create(
        model="gpt-5",
        input=build_card_generation_prompt(theme)
    )

    text = response.output_text.strip()

    try:
        data = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("AI応答をJSONとして読めませんでした。")
        data = json.loads(match.group(0))

    card = {
        "id": new_card_id(),
        "name": str(data.get("name", "")).strip(),
        "message": str(data.get("message", "")).strip(),
        "image": ""
    }

    if not card["name"] or not card["message"]:
        raise ValueError("カード名またはメッセージが空です。")

    return card


def add_ai_card_to_json(theme: str) -> Dict:
    new_card = generate_ai_card(theme)
    cards = load_cards()
    cards.append(new_card)
    save_cards(cards)
    return new_card


def add_multiple_ai_cards_to_json(count: int, theme: str) -> List[Dict]:
    created_cards = []
    cards = load_cards()

    for _ in range(count):
        card = generate_ai_card(theme)
        cards.append(card)
        created_cards.append(card)

    save_cards(cards)
    return created_cards


# =========================
# AI画像生成
# =========================
def build_image_prompt(card: Dict, theme: str = "やさしい癒し") -> str:
    name = card.get("name", "")
    message = card.get("message", "")

    prompt = f"""
Create a beautiful oracle card illustration.

Theme: {theme}
Card title: {name}
Meaning: {message}

Style requirements:
- spiritual fantasy
- soft, elegant, gentle, healing atmosphere
- highly detailed illustration
- symbolic composition
- luminous light
- harmonious colors
- vertical portrait composition
- suitable for oracle card art
- no text
- no letters
- no words
- no watermark
- no frame text
"""
    return prompt.strip()

def optimize_image_file(
    input_path: str,
    max_width: int = 768,
    max_height: int = 1152,
    png_compress_level: int = 9
) -> str:
    img = Image.open(input_path)

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    img.thumbnail((max_width, max_height))

    img.save(
        input_path,
        format="PNG",
        optimize=True,
        compress_level=png_compress_level
    )
    return input_path


def generate_card_image(card: Dict, theme: str = "やさしい癒し") -> str:
    if client is None:
        raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    result = client.images.generate(
        model="gpt-image-1",
        prompt=build_image_prompt(card, theme),
        size="1024x1536",
        quality="medium",
        output_format="png"
    )

    image_b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)

    safe_name = make_safe_filename(card.get("name", "card"))
    file_path = IMAGE_DIR / f"{safe_name}.png"

    if file_path.exists():
        n = 2
        while True:
            candidate = IMAGE_DIR / f"{safe_name}_{n}.png"
            if not candidate.exists():
                file_path = candidate
                break
            n += 1

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    optimize_image_file(str(file_path))

    st.success(f"今回の保存先: {file_path}")
    return str(Path("images") / file_path.name)


def attach_image_to_saved_card(
    target_card: Dict,
    image_path: str,
    card_image_path: str = ""
) -> bool:
    cards = load_cards()
    idx = find_card_index(cards, target_card)
    if idx == -1:
        return False

    cards[idx]["image"] = str(Path(image_path).as_posix()) if image_path else ""

    if card_image_path:
        cards[idx]["card_image"] = str(Path(card_image_path).as_posix())

    save_cards(cards)
    return True


# =========================
# 表示関数
# =========================
def display_one_card_with_effect(card: dict) -> None:
    area = st.empty()

    area.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #ece6f6, #f7f1ff);
            border-radius: 20px;
            padding: 50px 20px;
            margin: 12px 0;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            color: #7b6f8f;
            font-size: 1.1rem;
            font-weight: bold;
        ">
            カードを引いています…
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(1.0)

    with area.container():
        st.markdown(
            f"""
            <div style="
                background: rgba(255,255,255,0.92);
                border-radius: 20px;
                padding: 20px;
                margin: 12px 0;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                border: 1px solid rgba(255,255,255,0.7);
            ">
                <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 12px;">
                    {card.get('name', '名称未設定')}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        show_path = get_display_image_path(card)
        if show_path:
            try:
                st.image(show_path, width=280)
            except Exception as e:
                st.warning(f"画像を表示できませんでした: {e}")
                st.info("このカードは画像なしで表示しています。")

        st.write(card.get("message", ""))


def display_three_cards_sequential(cards: list) -> None:
    labels = ["過去", "現在", "未来"]
    placeholders = [st.empty(), st.empty(), st.empty()]

    for i, card in enumerate(cards[:3]):
        placeholders[i].markdown(
            """
            <div style="
                background: linear-gradient(135deg, #ece6f6, #f7f1ff);
                border-radius: 20px;
                padding: 40px 20px;
                margin: 12px 0;
                text-align: center;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                color: #7b6f8f;
                font-size: 1.1rem;
                font-weight: bold;
            ">
                カードを開いています…
            </div>
            """,
            unsafe_allow_html=True
        )

        time.sleep(0.8)

        with placeholders[i].container():
            st.markdown(
                f"""
                <div style="
                    background: rgba(255,255,255,0.92);
                    border-radius: 20px;
                    padding: 20px;
                    margin: 12px 0;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                    border: 1px solid rgba(255,255,255,0.7);
                ">
                    <div style="
                        font-size: 0.95rem;
                        color: #7b6f8f;
                        margin-bottom: 8px;
                        letter-spacing: 0.08em;
                    ">
                        {labels[i]}
                    </div>
                    <div style="
                        font-size: 1.4rem;
                        font-weight: bold;
                        margin-bottom: 12px;
                    ">
                        {card.get('name', '名称未設定')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            show_path = get_display_image_path(card)
            if show_path:
                try:
                    st.image(show_path, width=260)
                except Exception as e:
                    st.warning(f"画像を表示できませんでした: {e}")
                    st.info("このカードは画像なしで表示しています。")

            st.write(card.get("message", ""))

        time.sleep(0.6)


def display_result_card(card: dict, show_ai_message: Optional[str] = None):
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="card-title">✨ {card.get("name", "名称未設定")}</div>',
        unsafe_allow_html=True
    )

    show_path = get_display_image_path(card)
    if show_path:
        try:
            st.image(show_path, width=320)
        except Exception as e:
            st.warning(f"画像を表示できませんでした: {e}")

    st.markdown('<div class="section-label">カードメッセージ</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="card-message">{card.get("message", "")}</div>',
        unsafe_allow_html=True
    )

    if show_ai_message:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">AIリーディング</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-message">{show_ai_message}</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


def display_three_cards(cards: List[Dict]):
    labels = ["過去", "現在", "未来"]
    cols = st.columns(3)

    for i, card in enumerate(cards[:3]):
        with cols[i]:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="section-label">🔮 {labels[i]}</div>
                    <div class="card-title">{card.get("name", "名称未設定")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            show_path = get_display_image_path(card)
            if show_path:
                try:
                    st.image(show_path, width=220)
                except Exception as e:
                    st.warning(f"画像を表示できませんでした: {e}")

            st.markdown(
                f'<div class="card-message">{card.get("message", "")}</div>',
                unsafe_allow_html=True
            )


def display_three_cards_responsive(cards: List[Dict]):
    is_mobile = st.session_state.get("is_mobile", False)
    labels = ["過去", "現在", "未来"]

    if is_mobile:
        for i, card in enumerate(cards[:3]):
            st.markdown(f"### 🔮 {labels[i]}")
            display_result_card(card)
    else:
        display_three_cards(cards)


def display_card(card: Dict, show_actions: bool = False, index: int = 0, theme: str = "やさしい癒し") -> None:
    st.markdown(f"### {card.get('name', '名称未設定')}")

    show_path = get_display_image_path(card)
    if show_path:
        try:
            st.image(show_path, width=260)
        except Exception as e:
            st.warning(f"画像を表示できませんでした: {e}")

    st.write(card.get("message", ""))

    if show_actions:
        col1, col2, col3 = st.columns(3)

        with col1:
            button_key = f"gen_img_{card.get('id', index)}"
            if st.button("このカード画像を生成", key=button_key, use_container_width=True):
                try:
                    with st.spinner("画像生成中..."):
                        path = generate_card_image(card, theme=theme)

                    abs_image_path = resolve_image_path(path)
                    if not abs_image_path:
                        raise FileNotFoundError(f"生成画像が見つかりません: {path}")

                    with st.spinner("カード化中..."):
                        card_path_abs = create_card_design(
                            image_path=abs_image_path,
                            card_name=card.get("name", "無題")
                        )

                    card_path_rel = str(Path("images") / Path(card_path_abs).name)

                    ok = attach_image_to_saved_card(
                        card,
                        image_path=path,
                        card_image_path=card_path_rel
                    )

                    if ok:
                        st.success("画像とカードデザインを保存しました。")
                        st.rerun()
                    else:
                        st.warning("保存更新に失敗しました。")

                except Exception as e:
                    st.error(f"画像生成エラー: {e}")

        with col2:
            delete_key = f"delete_card_{card.get('id', index)}"
            if st.button("このカードを削除", key=delete_key, use_container_width=True):
                ok = delete_card_and_images(card)
                if ok:
                    st.success("カードと画像を削除しました。")
                    st.rerun()
                else:
                    st.warning("カード削除に失敗しました。")

        with col3:
            if show_path:
                st.caption("画像あり")
            else:
                st.caption("画像なし")

    st.divider()


# =========================
# 初期化
# =========================
ensure_sample_cards()
init_session_state()
cards = load_cards()


# =========================
# タイトル
# =========================
st.title("🔮 オラクルカードアプリ")
st.caption("カード作成・AI生成・画像生成つき")

if not API_KEY:
    st.warning("OPENAI_API_KEY が未設定です。AIカード生成と画像生成は使えません。")


# =========================
# サイドバー
# =========================
with st.sidebar:
    st.markdown("## ⚙️ 設定")

    draw_mode = st.radio(
        "引き方を選択",
        ["1枚引き", "3枚引き", "総合リーディング"],
        index=0,
        key="draw_mode_main"
    )

    st.session_state["ai_card_theme"] = st.text_input(
        "AIカードのテーマ",
        value=st.session_state.get("ai_card_theme", "やさしい癒し")
    )

    theme = st.selectbox(
        "表示テーマ",
        ["やさしい癒し", "幻想的", "神秘的", "高貴", "春の光"],
        index=0,
        key="ui_theme"
    )

    show_ai = st.toggle("AIリーディングを表示", value=True)
    show_history = st.toggle("履歴を表示", value=True)

    st.markdown("---")
    st.write(f"登録カード数: {len(cards)}")

    if st.button("履歴をクリア", use_container_width=True):
        st.session_state["history"] = []
        st.success("履歴をクリアしました。")


# =========================
# タブ
# =========================
tab1, tab2, tab3 = st.tabs(["🔮 占う", "🗂 カード一覧・管理", "🕘 履歴"])


# =========================
# tab1 占う
# =========================
with tab1:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.subheader("カードを引く")

    question = st.text_area(
        "今の気持ちや相談内容",
        placeholder="例：気持ちを整えたいです / 人間関係についてやさしく見てほしいです / これからの流れを知りたいです",
        key="question_input",
        height=100
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        draw_one = st.button("1枚引き", use_container_width=True, key="draw_one_tab1")

    with col2:
        draw_three = st.button("3枚引き", use_container_width=True, key="draw_three_tab1")

    with col3:
        draw_ai = st.button("総合リーディング", use_container_width=True, key="draw_ai_tab1")

    st.markdown('</div>', unsafe_allow_html=True)

    # 1枚引き
    if draw_one:
        with st.spinner("カードを引いています…"):
            time.sleep(1)

        if not cards:
            st.error("カードがありません。")
        else:
            chosen = random.choice(cards)
            st.session_state["last_result_type"] = "one"
            st.session_state["last_result_cards"] = [chosen]
            st.session_state["last_ai_text"] = ""
            st.session_state["show_sequence_done"] = False
            save_history(f"1枚引き：{chosen.get('name', '名称未設定')}")

    # 3枚引き
    if draw_three:
        with st.spinner("カードを引いています…"):
            time.sleep(1)

        if len(cards) < 3:
            st.error("3枚引きするにはカードが3枚以上必要です。")
        else:
            chosen_cards = random.sample(cards, 3)
            st.session_state["last_result_type"] = "three"
            st.session_state["last_result_cards"] = chosen_cards
            st.session_state["last_ai_text"] = ""
            st.session_state["show_sequence_done"] = False

            names = " / ".join([c.get("name", "名称未設定") for c in chosen_cards])
            save_history(f"3枚引き：{names}")

    # AI総合リーディング
    if draw_ai:
        with st.spinner("魔導書をひらいています…"):
            time.sleep(1.2)

        if not cards:
            st.error("カードがありません。")
        else:
            result_cards = st.session_state.get("last_result_cards", [])
            result_type = st.session_state.get("last_result_type", "")

            # まだカードを引いていない場合は3枚引き
            if not result_cards:
                if len(cards) < 3:
                    st.error("3枚引きするにはカードが3枚以上必要です。")
                else:
                    chosen_cards = random.sample(cards, 3)
                    result_cards = chosen_cards
                    result_type = "three"

                    st.session_state["last_result_cards"] = result_cards
                    st.session_state["last_result_type"] = result_type
                    st.session_state["show_sequence_done"] = False

            if result_cards:
                try:
                    if result_type == "one" and len(result_cards) >= 1:
                        prompt = build_one_card_prompt(result_cards[0], question=question)
                    elif result_type == "three" and len(result_cards) >= 3:
                        prompt = build_three_card_prompt(result_cards[:3], question=question)
                    else:
                        prompt = build_general_reading_prompt(result_cards, question=question)

                    st.session_state["last_ai_text"] = generate_ai_reading(prompt)

                    names = " / ".join([c.get("name", "名称未設定") for c in result_cards])
                    save_history(f"AI総合：{names}")

                except Exception as e:
                    st.session_state["last_ai_text"] = f"AIリーディングエラー: {e}"

    result_type = st.session_state.get("last_result_type", "")
    result_cards = st.session_state.get("last_result_cards", [])
    last_ai_text = st.session_state.get("last_ai_text", "")
    sequence_done = st.session_state.get("show_sequence_done", False)

    if result_type == "one" and result_cards:
        st.markdown("### あなたへのカード")
        if not sequence_done:
            display_one_card_with_effect(result_cards[0])
            st.session_state["show_sequence_done"] = True
        else:
            display_result_card(result_cards[0])

        if last_ai_text:
            st.markdown("### ✨ 魔導書からのメッセージ")
            st.markdown(
                f'<div class="card-message">{last_ai_text}</div>',
                unsafe_allow_html=True
            )

    elif result_type == "three" and len(result_cards) >= 3:
        st.markdown("### 3枚引きの結果")
        if not sequence_done:
            display_three_cards_sequential(result_cards[:3])
            st.session_state["show_sequence_done"] = True
        else:
            display_three_cards_responsive(result_cards[:3])

        if last_ai_text:
            st.markdown("### ✨ 魔導書からのメッセージ")
            st.markdown(
                f'<div class="card-message">{last_ai_text}</div>',
                unsafe_allow_html=True
            )


# =========================
# tab2 カード一覧・管理
# =========================
with tab2:
    st.subheader("カードを手動追加")

    with st.form("manual_add_form"):
        new_name = st.text_input("カード名")
        new_message = st.text_area("メッセージ", height=100)
        submitted = st.form_submit_button("追加する", use_container_width=True)

        if submitted:
            if not new_name.strip() or not new_message.strip():
                st.error("カード名とメッセージを入力してください。")
            else:
                cards.append({
                    "id": new_card_id(),
                    "name": new_name.strip(),
                    "message": new_message.strip(),
                    "image": ""
                })
                save_cards(cards)
                st.success("カードを追加しました。")
                st.rerun()

    st.divider()

    st.subheader("画像データの整理")

    col_fix1, col_fix2, col_fix3, col_fix4 = st.columns(4)

    with col_fix1:
        if st.button("画像パスを修正する", key="normalize_image_paths", use_container_width=True):
            fixed = normalize_card_paths()
            st.success(f"修正件数: {fixed}")
            st.rerun()

    with col_fix2:
        if st.button("消えた画像パスを整理する", key="clean_missing_image_paths", use_container_width=True):
            fixed = clean_missing_image_paths()
            st.success(f"整理件数: {fixed}")
            st.rerun()

    with col_fix3:
        if st.button("画像を軽量化する", key="optimize_all_images", use_container_width=True):
            fixed = optimize_all_images()
            st.success(f"軽量化件数: {fixed}")
            st.rerun()

    with col_fix4:
        if st.button("未使用画像を削除する", key="delete_unused_images", use_container_width=True):
            fixed = delete_unused_images()
            st.success(f"削除件数: {fixed}")
            st.rerun()

    st.divider()

    st.subheader("AIでカードを1枚生成")

    col_a, col_b = st.columns(2)

    with col_b:
        if st.button("AIで1枚＋画像も生成", key="one_ai_generate_with_image", use_container_width=True):
            try:
                with st.spinner("AIカード生成中..."):
                    card = add_ai_card_to_json(
                        theme=st.session_state.get("ai_card_theme", "やさしい癒し")
                    )

                with st.spinner("画像生成中..."):
                    image_path = generate_card_image(
                        card,
                        theme=st.session_state.get("ai_card_theme", "やさしい癒し")
                    )

                abs_image_path = resolve_image_path(image_path)
                if not abs_image_path:
                    raise FileNotFoundError(f"生成画像が見つかりません: {image_path}")

                with st.spinner("カードデザイン作成中..."):
                    card_image_abs = create_card_design(
                        image_path=abs_image_path,
                        card_name=card.get("name", "無題")
                    )

                card_image_rel = str(Path("images") / Path(card_image_abs).name)

                attach_image_to_saved_card(
                    card,
                    image_path=image_path,
                    card_image_path=card_image_rel
                )

                st.success("AIカード・画像・カードデザインを保存しました。")
                st.rerun()

            except Exception as e:
                st.error(f"AI＋画像生成エラー: {e}")

    st.divider()

    st.subheader("AIで複数カード生成")

    bulk_count = st.number_input(
        "生成枚数",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="bulk_ai_card_count_v2"
    )

    generate_images = st.checkbox(
        "カード画像もAI生成する",
        value=True,
        key="generate_ai_images"
    )

    if st.button("AIカードをまとめて生成して保存", key="bulk_generate_ai_cards", use_container_width=True):
        try:
            with st.spinner("AIが複数カードを生成中です..."):
                created_cards = add_multiple_ai_cards_to_json(
                    count=int(bulk_count),
                    theme=st.session_state.get("ai_card_theme", "やさしい癒し")
                )

            if generate_images:
                progress = st.progress(0, text="画像生成中...")
                for i, card in enumerate(created_cards, start=1):
                    image_path = generate_card_image(
                        card,
                        theme=st.session_state.get("ai_card_theme", "やさしい癒し")
                    )
                    attach_image_to_saved_card(card, image_path)
                    card["image"] = image_path
                    progress.progress(i / len(created_cards), text=f"画像生成中... {i}/{len(created_cards)}")
                progress.empty()

            st.success(f"{len(created_cards)}枚のカードを保存しました。")
            st.rerun()

        except Exception as e:
            st.error(f"複数生成エラー: {e}")

    st.divider()

    st.subheader("既存カードに画像を付ける")

    latest_cards_for_images = load_cards()
    cards_without_image = [
        card for card in latest_cards_for_images
        if not get_display_image_path(card)
    ]

    st.write(f"画像未設定カード: {len(cards_without_image)}枚")

    col_c, col_d = st.columns(2)

    with col_c:
        max_batch = min(10, max(1, len(cards_without_image))) if cards_without_image else 1
        batch_image_count = st.number_input(
            "今回生成する枚数",
            min_value=1,
            max_value=max_batch,
            value=min(3, max_batch),
            step=1,
            key="batch_existing_image_count"
        )

    with col_d:
        if st.button("未画像カードに画像を一括生成", key="generate_missing_images", use_container_width=True):
            if not cards_without_image:
                st.info("画像未設定カードはありません。")
            else:
                try:
                    target_cards = cards_without_image[:int(batch_image_count)]
                    progress = st.progress(0, text="画像生成中...")
                    for i, card in enumerate(target_cards, start=1):
                        path = generate_card_image(
                            card,
                            theme=st.session_state.get("ai_card_theme", "やさしい癒し")
                        )
                        attach_image_to_saved_card(card, path)
                        progress.progress(i / len(target_cards), text=f"画像生成中... {i}/{len(target_cards)}")

                    progress.empty()
                    st.success(f"{len(target_cards)}枚に画像を追加しました。")
                    st.rerun()

                except Exception as e:
                    st.error(f"画像一括生成エラー: {e}")

    st.divider()

    st.subheader("カード一覧")

    latest_cards = load_cards()

    if not latest_cards:
        st.info("カードがまだありません。")
    else:
        show_only_with_image = st.checkbox("画像ありカードのみ表示", value=False, key="show_only_with_image")
        show_debug = st.checkbox("画像デバッグ情報を表示", value=False, key="show_image_debug")
        keyword = st.text_input("カード検索", value="", key="card_search_keyword").strip()

        filtered_cards = []
        for card in latest_cards:
            img_exists = bool(get_display_image_path(card))

            if show_only_with_image and not img_exists:
                continue

            if keyword:
                combined = f"{card.get('name', '')} {card.get('message', '')}"
                if keyword not in combined:
                    continue

            filtered_cards.append(card)

        st.write(f"表示件数: {len(filtered_cards)}件")

        for idx, card in enumerate(filtered_cards):
            if show_debug:
                with st.expander(f"画像デバッグ情報: {card.get('name', '名称未設定')} / {card.get('id', '')}", expanded=False):
                    debug_path = get_display_image_path(card)
                    st.write("id:", card.get("id", ""))
                    st.write("name:", card.get("name", ""))
                    st.write("image:", card.get("image", ""))
                    st.write("card_image:", card.get("card_image", ""))
                    st.write("resolved:", debug_path)
                    st.write("resolved exists:", os.path.exists(debug_path) if debug_path else False)

            display_card(
                card,
                show_actions=True,
                index=idx,
                theme=st.session_state.get("ai_card_theme", "やさしい癒し")
            )

# =========================
# tab3 履歴
# =========================
with tab3:
    st.subheader("履歴")

    if show_history:
        history_list = st.session_state.get("history", [])
        display_history(history_list)
    else:
        st.info("サイドバーで履歴表示がオフになっています。")