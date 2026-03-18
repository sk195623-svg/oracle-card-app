import os
import json
import random
import base64
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

import streamlit as st
from openai import OpenAI

# ▼ここに入れる
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"
IMAGE_DIR.mkdir(exist_ok=True)

from typing import List, Dict, Optional

import streamlit as st
from openai import OpenAI

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

        image_path = card.get("image", "")
        if image_path:
            st.image(image_path, width=280)

        st.write(card.get("message", ""))


def display_three_cards_sequential(cards: list) -> None:
    labels = ["過去", "現在", "未来"]
    placeholders = [st.empty(), st.empty(), st.empty()]

    for i, card in enumerate(cards):
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

            image_path = card.get("image", "")
            if image_path:
                st.image(image_path, width=260)

            st.write(card.get("message", ""))

        time.sleep(0.6)

# =========================
# ページ設定（最優先）
# =========================
st.set_page_config(
    page_title="Oracle Card Reader",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

CARDS_JSON = "cards.json"
IMAGE_DIR = Path("images")
IMAGE_DIR.mkdir(exist_ok=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY) if API_KEY else None

# =========================
# ⭐ カード表示関数（ここ！）
# =========================
import os

def display_result_card(card: dict, show_ai_message: str | None = None):
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="card-title">✨ {card.get("name", "名称未設定")}</div>',
        unsafe_allow_html=True
    )

    image_path = card.get("image", "")
    if image_path and os.path.exists(image_path):
        st.image(image_path, width=320)

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

def display_three_cards(cards: list[dict]):
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

            image_path = card.get("image", "")
            if image_path and os.path.exists(image_path):
                st.image(image_path, width=220)

            st.markdown(
                f'<div class="card-message">{card.get("message", "")}</div>',
                unsafe_allow_html=True
            )


def display_three_cards_responsive(cards: list[dict]):
    labels = ["過去", "現在", "未来"]
    is_mobile = st.session_state.get("is_mobile", False)

    if is_mobile:
        for i, card in enumerate(cards[:3]):
            st.markdown(f"### 🔮 {labels[i]}")
            display_result_card(card)
    else:
        display_three_cards(cards)


def init_session_state():
    if "history" not in st.session_state:
        st.session_state["history"] = []

    if "last_result_type" not in st.session_state:
        st.session_state["last_result_type"] = ""

    if "last_result_cards" not in st.session_state:
        st.session_state["last_result_cards"] = []

    if "last_ai_text" not in st.session_state:
        st.session_state["last_ai_text"] = ""


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


# =========================
# データ入出力
# =========================
def load_cards() -> List[Dict]:
    if not os.path.exists(CARDS_JSON):
        return []

    try:
        with open(CARDS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def save_cards(cards: List[Dict]) -> None:
    with open(CARDS_JSON, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)


def ensure_sample_cards() -> None:
    if os.path.exists(CARDS_JSON):
        return

    sample_cards = [
        {
            "name": "月のしずく",
            "message": "静かな時間の中に、あなたへの答えがやさしく落ちてきます。急がず、心の声を聞いてください。",
            "image": ""
        },
        {
            "name": "光の扉",
            "message": "新しい流れが始まろうとしています。少しの勇気が、未来の扉を開きます。",
            "image": ""
        },
        {
            "name": "風の導き",
            "message": "変化は恐れるものではなく、あなたを新しい場所へ運ぶ追い風です。",
            "image": ""
        },
        {
            "name": "星の約束",
            "message": "願いはすでに宇宙へ届いています。信じる気持ちを持ち続けてください。",
            "image": ""
        },
        {
            "name": "花ひらく心",
            "message": "優しさを自分にも向けるとき、心は自然にひらいていきます。",
            "image": ""
        },
        {
            "name": "朝の祝福",
            "message": "今日という一日は、あなたに新しい祝福を届けるために始まっています。",
            "image": ""
        },
        {
            "name": "水鏡",
            "message": "感情を否定せず映してみましょう。そこに大切な本音があります。",
            "image": ""
        },
        {
            "name": "虹の橋",
            "message": "今の迷いは、次の希望へ渡るための途中にあります。安心して進んでください。",
            "image": ""
        },
        {
            "name": "大地の抱擁",
            "message": "足元を整えれば、運は自然と安定します。まずは日常を大切に。",
            "image": ""
        },
        {
            "name": "天使のささやき",
            "message": "見えない助けはすぐそばにあります。ひとりで抱え込まなくて大丈夫です。",
            "image": ""
        }
    ]
    save_cards(sample_cards)


# =========================
# 共通処理
# =========================
def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def make_safe_filename(name: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]+', "_", name)
    safe = re.sub(r"\s+", "_", safe).strip("._ ")
    return safe or "card"

def get_japanese_font(size: int):
    font_candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
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

    # 背景カード
    card = Image.new("RGB", (card_width, card_height), "white")
    draw = ImageDraw.Draw(card)

    # 元画像をカード上部に収める
    target_w = card_width - margin * 2
    target_h = image_area_h

    img = base_img.copy()
    img.thumbnail((target_w, target_h))

    paste_x = (card_width - img.width) // 2
    paste_y = margin + (target_h - img.height) // 2
    card.paste(img, (paste_x, paste_y))

    # 外枠
    draw.rounded_rectangle(
        [(8, 8), (card_width - 8, card_height - 8)],
        radius=28,
        outline=(180, 160, 120),
        width=6
    )

    # 内側枠
    draw.rounded_rectangle(
        [(22, 22), (card_width - 22, card_height - 22)],
        radius=24,
        outline=(220, 205, 170),
        width=2
    )

    # タイトル帯
    title_top = card_height - title_area_h - margin
    title_bottom = card_height - margin

    draw.rounded_rectangle(
        [(margin, title_top), (card_width - margin, title_bottom)],
        radius=24,
        fill=(248, 244, 236),
        outline=(210, 195, 160),
        width=3
    )

    # タイトル文字
    title_font = get_japanese_font(52)

    bbox = draw.textbbox((0, 0), card_name, font=title_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    text_x = (card_width - text_w) // 2
    text_y = title_top + (title_area_h - text_h) // 2 - 8

    draw.text(
        (text_x, text_y),
        card_name,
        font=title_font,
        fill=(70, 60, 45)
    )

    # 保存先
    if output_path is None:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_card.png")

    card.save(output_path)
    return output_path

def find_card_index(cards: List[Dict], target: Dict) -> int:
    target_name = normalize_text(target.get("name", ""))
    target_message = normalize_text(target.get("message", ""))

    for i, card in enumerate(cards):
        if (
            normalize_text(card.get("name", "")) == target_name
            and normalize_text(card.get("message", "")) == target_message
        ):
            return i
    return -1


# =========================
# AIテキスト生成
# =========================
def build_card_generation_prompt(theme: str) -> str:
    return f"""
あなたはオラクルカード作家です。
やさしく、癒しがあり、前向きで、スピリチュアルすぎても怖くならないカードを作ってください。

テーマ: {theme}

出力ルール:
- 日本語
- カード名は短く美しい表現
- メッセージは60〜120文字程度
- JSONのみで出力
- 形式は必ず以下:
{{"name":"カード名","message":"メッセージ"}}
""".strip()


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
        # 念のためJSON部分だけ抜き出す
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("AI応答をJSONとして読めませんでした。")
        data = json.loads(match.group(0))

    card = {
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

    # 同名がある場合は連番
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

    st.success(f"今回の保存先: {file_path}")

    # cards.json には相対パスで保存
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

    cards[idx]["image"] = image_path
    if card_image_path:
        cards[idx]["card_image"] = card_image_path

    save_cards(cards)
    return True


# =========================
# 画面表示補助
# =========================
def display_card(card: Dict, show_actions: bool = False, index: int = 0, theme: str = "やさしい癒し") -> None:
    st.markdown(f"### {card.get('name', '名称未設定')}")

    card_image_path = card.get("card_image", "")
    image_path = card.get("image", "")

    show_path = ""
    if card_image_path and os.path.exists(card_image_path):
        show_path = card_image_path
    elif image_path and os.path.exists(image_path):
        show_path = image_path

    if show_path:
        st.image(show_path, width=260)

    st.write(card.get("message", ""))

    if show_actions:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("このカード画像を生成", key=f"gen_img_{index}", width="stretch"):
                try:
                    with st.spinner("画像生成中..."):
                        path = generate_card_image(card, theme=theme)

                    abs_image_path = str((BASE_DIR / path).resolve()) if not os.path.isabs(path) else path

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
            if card_image_path and os.path.exists(card_image_path):
                st.caption("カード画像あり")
            elif image_path and os.path.exists(image_path):
                st.caption("画像あり")
            else:
                st.caption("画像なし")

    st.divider()


# =========================
# 初期化
# =========================
ensure_sample_cards()
init_session_state()

if "ai_card_theme" not in st.session_state:
    st.session_state["ai_card_theme"] = "やさしい癒し"

# ←ここに追加（②）
if "show_sequence_done" not in st.session_state:
    st.session_state["show_sequence_done"] = False

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

    if st.button("履歴をクリア", width="stretch"):
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

    question = st.text_input(
        "今の気持ちや相談内容",
        placeholder="例：仕事の流れ、人間関係、今日の運気…",
        key="question_input"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        draw_one = st.button("1枚引き", width="stretch", key="draw_one_tab1")

    with col2:
        draw_three = st.button("3枚引き", width="stretch", key="draw_three_tab1")

    with col3:
        draw_ai = st.button("AI総合リーディング", width="stretch", key="draw_ai_tab1")

    st.markdown('</div>', unsafe_allow_html=True)

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

    if draw_three:
        with st.spinner("3枚のカードを展開しています…"):
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

    if draw_ai:
        with st.spinner("リーディング中…"):
            time.sleep(1.5)

        if not cards:
            st.error("カードがありません。")
        else:
            chosen = random.choice(cards)
            st.session_state["last_result_type"] = "ai"
            st.session_state["last_result_cards"] = [chosen]

            if client and show_ai:
                try:
                    prompt = f"""
あなたはやさしく上品なオラクルカードリーダーです。
次のカードについて、日本語で自然であたたかいリーディングをしてください。

【相談内容】
{question}

【カード名】
{chosen.get("name", "")}

【カードメッセージ】
{chosen.get("message", "")}

条件:
- やさしい語り口
- 180〜300字程度
- 前向きで押しつけがましくない
- 最後に短い行動アドバイスを添える
"""
                    response = client.responses.create(
                        model="gpt-5",
                        input=prompt
                    )
                    st.session_state["last_ai_text"] = response.output_text.strip()
                except Exception as e:
                    st.session_state["last_ai_text"] = f"AIリーディングエラー: {e}"
            else:
                st.session_state["last_ai_text"] = ""

            save_history(f"AI総合：{chosen.get('name', '名称未設定')}")

    result_type = st.session_state.get("last_result_type", "")
    result_cards = st.session_state.get("last_result_cards", [])
    sequence_done = st.session_state.get("show_sequence_done", False)

    if result_type == "one" and result_cards:
        st.markdown("### あなたへのカード")

        if not sequence_done:
            display_one_card_with_effect(result_cards[0])
            st.session_state["show_sequence_done"] = True
        else:
            display_result_card(result_cards[0])

    elif result_type == "three" and result_cards:
        st.markdown("### 3枚引きの結果")

        if not sequence_done:
            display_three_cards_sequential(result_cards)
            st.session_state["show_sequence_done"] = True
        else:
            display_three_cards_responsive(result_cards)

    elif result_type == "ai" and result_cards:
        display_result_card(
            result_cards[0],
            st.session_state["last_ai_text"] if show_ai else None
        )


# =========================
# tab2 カード一覧・管理
# =========================
with tab2:
    st.subheader("カードを手動追加")

    with st.form("manual_add_form"):
        new_name = st.text_input("カード名")
        new_message = st.text_area("メッセージ", height=100)
        submitted = st.form_submit_button("追加する", width="stretch")

        if submitted:
            if not new_name.strip() or not new_message.strip():
                st.error("カード名とメッセージを入力してください。")
            else:
                cards.append({
                    "name": new_name.strip(),
                    "message": new_message.strip(),
                    "image": ""
                })
                save_cards(cards)
                st.success("カードを追加しました。")
                st.rerun()

    st.divider()

    st.subheader("AIでカードを1枚生成")

    col_a, col_b = st.columns(2)

    with col_b:
        if st.button("AIで1枚＋画像も生成", key="one_ai_generate_with_image", width="stretch"):
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

                abs_image_path = str((BASE_DIR / image_path).resolve()) if not os.path.isabs(image_path) else image_path

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

    if st.button("AIカードをまとめて生成して保存", key="bulk_generate_ai_cards", width="stretch"):
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
        if not card.get("image") or not os.path.exists(card.get("image", ""))
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
        if st.button("未画像カードに画像を一括生成", key="generate_missing_images", width="stretch"):
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
        keyword = st.text_input("カード検索", value="", key="card_search_keyword").strip()

        filtered_cards = []
        for card in latest_cards:
            img = card.get("card_image") or card.get("image", "")

            img_exists = False
            if img:
                abs_img = str((BASE_DIR / img).resolve()) if not os.path.isabs(img) else img
                img_exists = os.path.exists(abs_img)

            if show_only_with_image and not img_exists:
                continue

            if keyword:
                combined = f"{card.get('name', '')} {card.get('message', '')}"
                if keyword not in combined:
                    continue

            filtered_cards.append(card)

        st.write(f"表示件数: {len(filtered_cards)}件")

        for idx, card in enumerate(filtered_cards):
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