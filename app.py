# QuestApp.py
import datetime as dt
import json
import random
from pathlib import Path
from typing import List
from openai import OpenAI
import base64
from io import BytesIO
import os
import requests
from shutil import which
import re

import streamlit as st
from pydantic import BaseModel

# ---------------- UI / STYL ----------------
st.set_page_config(page_title="QuestApp", page_icon="🌟", layout="centered")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    if "room" in st.session_state and st.session_state["room"] != "start":
        if st.button("⬅️ Wróć do wyboru pokoju"):
            st.session_state["room"] = "start"
            st.rerun()


PEACH = "#FFDAB9"  # PeachPuff
st.markdown(
    f"""
    <style>
    .stApp {{
        background: {PEACH};
        background: linear-gradient(180deg, {PEACH} 0%, #fff7f2 100%);
    }}
    h1, h2, h3 {{
        text-align: center;
    }}
    .stButton>button {{
        border-radius: 12px;
        padding: 0.5rem 0.9rem;
    }}
    .metric-row .stMetric {{
        background: rgba(255,255,255,0.6);
        border-radius: 12px;
        padding: .6rem;
    }}
    pre, code, .emoji {{
        font-size: 1.05rem;
        line-height: 1.35rem;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Powitanie + prefix wg pory dnia ---
import datetime as _dt

def _time_prefix():
    now = _dt.datetime.now().hour
    if 5 <= now < 12:
        return "Dzień dobry"
    if 12 <= now < 18:
        return "Cześć"
    return "Dobry wieczór"

def greet_user(prefix: str | None = None):
    """Wyświetla powitanie z imieniem/imionami. prefix=None -> wg pory dnia."""
    raw = (st.session_state.get("user_name") or "").strip()
    prefix = prefix or _time_prefix()

    if not raw:
        st.markdown(f"### {prefix}! 👋")
        st.caption("Ustaw imię na ekranie startowym lub w lewym panelu.")
        return

    parts = [p.strip().split()[0].capitalize() for p in raw.split(",") if p.strip()]
    who = parts[0] if len(parts) == 1 else " i ".join(parts)
    st.markdown(f"### {prefix}, {who}! 👋")

def dalle_prompt(topic: str) -> str:
    """Buduje prompt do wizualizacji medytacyjnej (możesz używać w różnych pokojach)."""
    topic = topic.strip() or "spokojny las o świcie"
    return (
        f"Ethereal, calming visualization of '{topic}' for guided meditation. "
        f"Soft light, dreamy, cinematic composition, watercolor + soft gradients, "
        f"high detail, no text, no watermark."
    )

def clean_markdown_for_tts(text: str) -> str:
    """Usuwa proste znaczniki Markdown i emoji/ikony, by gTTS nie czytał gwiazdek itp."""
    # proste wyczyszczenie: gwiazdki, podkreślenia, backticki, nagłówki, cytaty
    text = re.sub(r"[*_`#>]+", " ", text)
    # [tekst](link) -> tekst
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    # usuwamy podwójne i większe spacje
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


# ---------------- DANE ----------------
DATA_FILE = Path("health_data.json")

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"days": {}, "challenge": {"start_date": None}, "user": {}}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

data = load_data()
data.setdefault("user", {})
data["user"].setdefault("name", "")
data["user"].setdefault("goals", [])
save_data(data)

# <<< DODAJ >>>
# Trzymaj imię w session_state, by było dostępne we wszystkich pokojach
if "user_name" not in st.session_state:
    st.session_state["user_name"] = (data["user"]["name"] or "").strip()

# ---------------- ROUTING ----------------
if "room" not in st.session_state:
    st.session_state["room"] = "start"

# Mapka ładnych nazw pokoi (do toastów)
ROOM_LABEL = {
    "start": "Start",
    "health": "Motywator zdrowia",
    "mind": "Mind",
    "sport": "Sport",
    "dieta": "Dieta",
    "study": "Nauka",
    "finance": "Finanse",
    "social": "Social",
    "order": "Porządek",
}

# Toast przy zmianie pokoju (raz na wejście)
_curr = st.session_state["room"]
_last = st.session_state.get("_last_room")

if _last != _curr and _curr != "start":
    pretty = ROOM_LABEL.get(_curr, _curr.title())
    who = (st.session_state.get("user_name") or "").strip()
    msg = f"🤩 Witaj w pokoju {pretty}" + (f", {who}!" if who else "!")
    st.toast(msg)
    st.session_state["_last_room"] = _curr


# ---------------- START SCREEN ----------------
if st.session_state["room"] == "start":
    st.markdown("<h1>✨ QuestApp ✨</h1>", unsafe_allow_html=True)
    st.markdown("### 👋 Cześć! Witaj w Twojej podróży questów")

    name = st.text_input("Jak masz na imię?", value=data["user"]["name"], placeholder="np. Rafał")

    quest_choice = st.selectbox(
        "Co chcesz poprawić?",
        [
            "🚵 Motywator zdrowia",
            "🧘 Mind",
            "🏋️ Sport",
            "🍎 Dieta",
            "📚 Nauka",
            "💸 Finanse",
            "🤝 Social",
            "🧹 Porządek",
        ],
        index=0
    )

    # <<< TU musi być wcięcie >>>
    if st.button("Wejdź do pokoju"):
        # 1) Zapis do pliku
        data["user"]["name"] = name.strip()
        data["user"]["goals"] = [quest_choice]
        save_data(data)

        # 2) Sync do session_state
        st.session_state["user_name"] = data["user"]["name"]

        # 3) Routing
        if "Motywator zdrowia" in quest_choice:   st.session_state["room"] = "health"
        elif "Mind" in quest_choice:              st.session_state["room"] = "mind"
        elif "Sport" in quest_choice:             st.session_state["room"] = "sport"
        elif "Dieta" in quest_choice:             st.session_state["room"] = "dieta"
        elif "Nauka" in quest_choice:             st.session_state["room"] = "study"
        elif "Finanse" in quest_choice:           st.session_state["room"] = "finance"
        elif "Social" in quest_choice:            st.session_state["room"] = "social"
        elif "Porządek" in quest_choice:          st.session_state["room"] = "order"

        # 4) Rerun na końcu
        st.rerun()


# ---------------- MOTYWATOR ZDROWIA 🚵 (pełny) ----------------
elif st.session_state["room"] == "health":
    st.title("🚵 Motywator zdrowia — Bike Quest")
    greet_user("Hej")

    # ---------------- MODELE ----------------
    class Task(BaseModel):
        name: str
        category: str
        hint: str

    LIGHT_TASKS: List[Task] = [
        Task(name="Medytacja 10–15 min", category="Mind 🧘‍♂️", hint="Krótka sesja oddechowa lub body-scan."),
        Task(name="Rower stacjonarny 20–30 min", category="Body 🚴‍♂️", hint="Utrzymaj lekkie tętno, bez zajezdni."),
        Task(name="Sen 7–8 h", category="Regeneracja 😴", hint="Zasłoń ekran min. 1 h przed snem."),
    ]

    EXTRA_TASKS: List[Task] = [
        Task(name="2L wody", category="Hydro 💧", hint="Butelka 1L x2 i po sprawie."),
        Task(name="Spacer 20–30 min", category="Body 🚶‍♂️", hint="Świeże powietrze > scroll."),
        Task(name="1 posiłek warzywno-owocowy", category="Dieta 🍎", hint="Sałatka/owocowy bowl > fastfood."),
        Task(name="Rozciąganie 5–10 min", category="Mobilność 🧘", hint="Szyja, plecy, biodra."),
        Task(name="Dziennik wdzięczności (2–3 zdania)", category="Mind 📓", hint="Co dziś było dobre?"),
        Task(name="Bez telefonu 1 h przed snem", category="Higiena snu 🌙", hint="Papierowa książka wygrywa."),
        Task(name="30 dni bez alkoholu", category="Nawyk 🧱", hint="Liczymy streak dzień po dniu."),
    ]

    BONUS_POOL = [
        "30 przysiadów w ciągu dnia",
        "10 min rozciągania pleców",
        "Zamień słodki napój na wodę",
        "3-min medytacja wdzięczności",
        "Wejdź po schodach zamiast windy",
    ]

    POWERUPS = {5: "💧", 10: "🍎", 15: "🛌", 20: "📓", 25: "🧘", 30: "👑"}  # co 5 pól + meta

    # ---------------- STAN DNIA ----------------
    today = dt.date.today().isoformat()
    st.caption(f"Dzień: {today}")

    mode = st.toggle("Hard mode (wszystkie cele)", value=False, help="Wyłączone = Light (3 filary). Włączone = pełny zestaw.")
    tasks = LIGHT_TASKS + (EXTRA_TASKS if mode else [])

    day_state = data["days"].get(today) or {
        "done": {t.name: False for t in tasks},
        "water_ml": 0,
        "notes": "",
        "bonus": random.choice(BONUS_POOL),
    }
    for t in tasks:
        day_state["done"].setdefault(t.name, False)
    data["days"][today] = day_state
    save_data(data)

    # ---------------- WYZWANIE 30 DNI ----------------
    st.subheader("🧱 30 dni bez alkoholu — odliczanie")
    start_date_str = data["challenge"].get("start_date")

    cols = st.columns([2,1,1])
    with cols[0]:
        start_date = st.date_input(
            "Ustaw datę startu wyzwania",
            value=dt.date.fromisoformat(start_date_str) if start_date_str else dt.date.today()
        )
    with cols[1]:
        if st.button("Start od dziś"):
            data["challenge"]["start_date"] = dt.date.today().isoformat()
            save_data(data); st.rerun()
    with cols[2]:
        if st.button("Wyczyść start"):
            data["challenge"]["start_date"] = None
            save_data(data); st.rerun()

    if start_date_str != (start_date.isoformat() if start_date else None):
        data["challenge"]["start_date"] = start_date.isoformat() if start_date else None
        save_data(data)

    start_date_str = data["challenge"].get("start_date")
    if start_date_str:
        start_dt = dt.date.fromisoformat(start_date_str)
        days_passed = (dt.date.today() - start_dt).days + 1
        days_passed = max(1, min(days_passed, 30))
        days_left = 30 - days_passed
        pct = days_passed / 30
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Dni minęły", days_passed)
        with m2: st.metric("Zostało", days_left)
        with m3: st.metric("Start", start_dt.strftime("%Y-%m-%d"))
        st.progress(pct, text=f"Postęp: {days_passed}/30 dni")
        if days_passed >= 30:
            st.success("🏆 30 dni zaliczone! Chcesz nowy cel albo ciągnąć serię dalej?")
    else:
        days_passed = 0
        st.info("Ustaw datę startu — od niej liczymy 30 dni i odliczamy postęp.")

    st.divider()

    # ---------------- PODSUMOWANIE CELÓW DNIA ----------------
    c1, c2 = st.columns(2)
    with c1: st.subheader("🎯 Cele na dziś")
    completed = sum(day_state["done"].get(t.name, False) for t in tasks)
    with c2:
        st.metric("Postęp", f"{completed}/{len(tasks)}", help="Dzisiejsze checklisty")

    def on_check_change(name):
        day_state["done"][name] = st.session_state[f"cb_{name}"]
        data["days"][today] = day_state
        save_data(data)

    for t in tasks:
        st.checkbox(
            f"**{t.name}** — _{t.category}_",
            value=day_state["done"].get(t.name, False),
            key=f"cb_{t.name}",
            help=t.hint,
            on_change=on_check_change,
            args=(t.name,),
        )

    st.divider()

    # ---------------- LICZNIK WODY ----------------
    st.subheader("💧 Licznik wody (cel 2000 ml)")
    w1, w2, w3 = st.columns([1,2,1])

    def adjust_water(delta):
        day_state["water_ml"] = max(0, day_state["water_ml"] + delta)
        data["days"][today] = day_state
        save_data(data)

    with w1:
        if st.button("-250 ml"): adjust_water(-250)
    with w2:
        st.progress(min(day_state["water_ml"]/2000, 1.0))
        st.write(f"Wypite: **{day_state['water_ml']} ml / 2000 ml**")
    with w3:
        if st.button("+250 ml"): adjust_water(+250)

    st.info(f"🎲 Bonus dnia: **{day_state['bonus']}** (opcjonalnie)")

    st.divider()

    # ---------------- NOTATKI ----------------
    st.subheader("📝 Notatki na dziś")
    notes_val = st.text_area(
        "Co warto zapamiętać (myśli, spostrzeżenia, wdzięczność)?",
        value=day_state.get("notes", ""), height=140,
        placeholder="Np. „Dziś najtrudniejsza była ochota na słodkie po obiedzie…”"
    )
    if st.button("Zapisz notatki"):
        day_state["notes"] = notes_val
        data["days"][today] = day_state
        save_data(data)
        st.success("Zapisano notatki.")

    # ---------------- MOTYWACJA ----------------
    def motivation(completed, total, days_passed, start_set):
        if not start_set:
            return "Każda zmiana zaczyna się od decyzji. Ustaw datę startu i zrób dziś pierwszy krok."
        if days_passed in (1, 2, 3):
            return "Pierwsze dni nadają rytm. Prosto, spokojnie, konsekwentnie."
        if days_passed in (5, 10, 15, 20, 25):
            return f"Checkpoint {days_passed}! Zabierasz ze sobą power-up i jedziesz dalej 🚵"
        if completed == total and total > 0:
            return "Pięknie! Dziś komplet. Korona rośnie w oczach — jutro powtórka 👑"
        if completed >= max(1, total//2):
            return "Ponad połowa za Tobą. Jeszcze chwila i dzień na zielono!"
        return "Nie musisz robić wszystkiego naraz. Jedna rzecz teraz — rozruch to 80% sukcesu."

    st.success("💬 " + motivation(completed, len(tasks), days_passed, bool(start_date_str)))

    st.divider()

    # ---------------- MINI-GRA: BIKE QUEST 6×5 ----------------
    st.subheader("🎮 Bike Quest: 30-dniowa trasa 🚵 → 🏰")
    st.caption("Każdy dzień streaka przesuwa Cię o jedno pole. Co 5 pól — power-up!")

    def draw_rpg_board(days_passed: int) -> str:
        total, rows, cols = 30, 5, 6  # 5 wierszy × 6 kol. = 30
        tiles = []
        for r in range(rows):
            row = []
            for c in range(cols):
                i = r * cols + c + 1
                if i == total:
                    row.append("🏰")        # meta
                elif i == days_passed and i < total:
                    row.append("🚵")        # gracz
                elif i in POWERUPS and i > days_passed:
                    row.append(POWERUPS[i]) # power-up widoczny na trasie
                elif i < days_passed:
                    row.append("🟩")        # przebyte pola (zielone)
                else:
                    row.append("▫️")        # puste pole
            tiles.append("".join(row))
        return "\n".join(tiles)

    # narysuj planszę
    if start_date_str:
        st.text(draw_rpg_board(days_passed))
    else:
        st.info("Ustaw datę startu wyzwania, aby wyruszyć w trasę 🚵")

    # legenda
    st.caption("Legenda: 🚵 Ty | 🟩 przebyte | ▫️ do przejechania | 💧🍎🛌📓🧘 power-upy | 🏰 meta | 👑 nagroda")

# ---------------- MIND ROOM 🧘 ----------------
elif st.session_state["room"] == "mind":
    st.title("🧘 Mind Room — Guided Meditation")
    greet_user("Witaj")

    # --- Klucz API ---
    st.markdown("🔑 Podaj swój klucz OpenAI, aby wygenerować medytację:")
    openai_key = st.text_input("OpenAI API Key", type="password")
    if not openai_key:
        st.info("➡️ Wklej klucz, żeby odblokować generowanie.")

    st.markdown("Witaj w pokoju Mind! Tutaj możesz wygenerować swoją spersonalizowaną medytację ✨")

    # --- Ustawienia ---
    topics = [
        "Poranna wdzięczność",
        "Medytacja na sen",
        "Skupienie i klarowność",
        "Redukcja stresu",
        "Body scan",
        "Akceptacja siebie",
        "Mindfulness w ruchu",
        "Świadomy oddech",
        "Cisza i bezruch",
        "Bycie tu i teraz",
    ]
    selected_topic = st.selectbox("🎯 Wybierz temat medytacji:", [""] + topics)
    user_prompt = st.text_input("📝 Albo wpisz własny temat:", value=selected_topic)
    med_length = st.selectbox("⏱️ Długość medytacji (min):", [5, 10, 15, 20])

    # pamięć sesji
    if "mind_text" not in st.session_state:
        st.session_state["mind_text"] = ""
    if "mind_audio_path" not in st.session_state:
        st.session_state["mind_audio_path"] = ""
    if "mind_image" not in st.session_state:
        st.session_state["mind_image"] = None

    # przyciski
    col1, col2 = st.columns([2,1])
    with col1:
        gen_text_clicked = st.button("🧘 Wygeneruj medytację (tekst)", use_container_width=True)

    # --- 1) Tekst ---
    if gen_text_clicked:
        if not openai_key:
            st.error("Podaj OpenAI API Key.")
            st.stop()
        if not user_prompt:
            st.error("Podaj temat medytacji.")
            st.stop()

        try:
            
            client = OpenAI(api_key=openai_key)

            with st.spinner("Generuję medytację tekstową..."):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Jesteś spokojnym nauczycielem medytacji. Język: polski."},
                        {"role": "user", "content": f"Napisz prowadzoną medytację (~{med_length} minut) po polsku. Temat: {user_prompt}. Dodaj pauzy i wskazówki oddechu."}
                    ],
                    temperature=0.7,
                )
            st.session_state["mind_text"] = resp.choices[0].message.content.strip()
            st.success("✅ Medytacja wygenerowana!")
        except Exception as e:
            st.error(f"❌ Błąd generowania tekstu: {e}")

    if st.session_state.get("mind_text"):
        st.text_area("📜 Podgląd medytacji:", st.session_state["mind_text"], height=300)

        # --- 2) AUDIO: gTTS + miks z tłem ---
        
        st.markdown("### 🎧 Audio – wygeneruj głos i dodaj tło natury") 

        from datetime import datetime
        from gtts import gTTS
        from pydub import AudioSegment
        # używamy shutil.which (from shutil import which na górze pliku)

        # Kandydaci: PATH + Linux (Cloud) + Windows
        candidate_ffmpeg = [
            which("ffmpeg"),
            which("ffmpeg.exe"),
            "/usr/bin/ffmpeg",  # Streamlit Cloud
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ]
        candidate_ffprobe = [
            which("ffprobe"),
            which("ffprobe.exe"),
            "/usr/bin/ffprobe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\ProgramData\chocolatey\bin\ffprobe.exe",
        ]

        ffmpeg_path  = next((p for p in candidate_ffmpeg  if p and os.path.exists(p)), None)
        ffprobe_path = next((p for p in candidate_ffprobe if p and os.path.exists(p)), None)

        st.caption(f"FFmpeg path detected: {ffmpeg_path or 'NONE'}")


        if not ffmpeg_path:
            st.error("Nie znaleziono FFmpeg. Lokalnie doinstaluj lub na Cloud dodaj packages.txt z 'ffmpeg'.")
            st.stop()

        os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")

        # Pydub: wskażemy binarki wprost
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffprobe_path
    

        # Pydub: wskażemy binarki wprost
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffprobe_path


        os.makedirs("meditations", exist_ok=True)
        os.makedirs("assets/sounds", exist_ok=True)

        uploaded_bg = st.file_uploader("Dodaj pliki MP3 z odgłosami natury", type=["mp3"], accept_multiple_files=True)
        if uploaded_bg:
            for up in uploaded_bg:
                with open(os.path.join("assets", "sounds", up.name), "wb") as f:
                    f.write(up.read())
            st.success("✅ Dodano pliki do `assets/sounds/`")

        available_bg = [f for f in os.listdir("assets/sounds") if f.endswith(".mp3")]
        col_bg1, col_bg2 = st.columns([2,1])
        with col_bg1:
            bg_choice = st.selectbox("🎵 Wybierz tło", ["(brak)"] + sorted(available_bg))
        with col_bg2:
            bg_gain_db = st.slider("Głośność tła (dB)", -30, 6, -10)

        v_gain_db = st.slider("🎙️ Głośność głosu (dB)", -6, 12, 4)
        fade_in_ms = st.slider("Fade in (ms)", 0, 8000, 1500, 250)
        fade_out_ms = st.slider("Fade out (ms)", 0, 8000, 2000, 250)

        if st.button("🎙️ Wygeneruj głos i miks"):
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                voice_path = os.path.join("meditations", f"mind_voice_{ts}.mp3")

                


                # czyścimy tekst z markdown/emoji zanim poleci do TTS
                clean_text = clean_markdown_for_tts(st.session_state["mind_text"])

                # generujemy głos
                gTTS(clean_text, lang="pl").save(voice_path)
                # wczytaj jawnie jako MP3 (często usuwa WinError 2 na Windows)
                voice = AudioSegment.from_file(voice_path, format="mp3")
                voice = voice.apply_gain(v_gain_db)
                # (opcjonalnie diagnostyka — możesz usunąć po teście)
                st.caption(f"Loaded voice: {len(voice)} ms")


                if bg_choice != "(brak)":
                    bg = AudioSegment.from_file(os.path.join("assets/sounds", bg_choice)).apply_gain(bg_gain_db)
                    looped = (bg * (len(voice) // len(bg) + 1))[:len(voice)]
                    mixed = voice.overlay(looped)
                    st.caption(f"Loaded background: {bg_choice}, length {len(bg)} ms, gain {bg_gain_db} dB")

                else:
                    mixed = voice

                mixed = mixed.fade_in(fade_in_ms).fade_out(fade_out_ms)
                final_path = os.path.join("meditations", f"mind_final_{ts}.mp3")
                mixed.export(final_path, format="mp3")

                st.session_state["mind_audio_path"] = final_path
                st.success("🎧 Audio gotowe!")
            except Exception as e:
                st.error(f"❌ Błąd audio: {e}")

    # --- Podgląd i pobieranie (osobny blok, niżej) ---
        if st.session_state["mind_audio_path"]:
            st.audio(st.session_state["mind_audio_path"])
            with open(st.session_state["mind_audio_path"], "rb") as f:
                st.download_button("💾 Pobierz MP3", f, "mind_meditation.mp3")



    # # --- 3) Wizualizacja ---
    # col_i1, col_i2 = st.columns(2)
    # with col_i1:
    #     img_size = st.selectbox("🖼️ Rozmiar", ["1024x1024", "1792x1024", "1024x1792"], index=0)
    # with col_i2:
    #     quality = st.selectbox("Jakość", ["standard", "hd"], index=0)

    # gen_img_clicked = st.button("🌌 Generuj wizualizację (DALL·E 3)")

    # if gen_img_clicked:
    #     if not openai_key:
    #         st.error("Podaj OpenAI API Key.")
    #         st.stop()
    #     try:
    #         client = OpenAI(api_key=openai_key)
    #         prompt_text = dalle_prompt(user_prompt)

    #         #quality_api = {"standard": "medium", "hd": "high"}[quality]

    #         with st.spinner("Generuję obraz…"):
    #             resp = client.images.generate(
    #                 model="image-alpha-001", #"gpt-image-1"(DALL-E 3)
    #                 prompt=prompt_text,
    #                 size=img_size,
    #                 #quality=quality_api,
    #                 n=1,
    #             )

    #         # pobieramy URL obrazu
    #         img_url = resp.data[0].url  

    #         # pokazujemy w Streamlit
    #         st.image(img_url, caption="Twoja wizualizacja ✨", use_container_width=True)

    #         # przycisk pobierania
    #         img_bytes = requests.get(img_url).content
    #         st.download_button(
    #             "💾 Pobierz PNG",
    #             data=img_bytes,
    #             file_name="mind_visualization.png",
    #             mime="image/png",
    #         )

    #         # zapis do session_state
    #         st.session_state["mind_image"] = img_bytes
    #         st.success("🖼️ Wizualizacja gotowa!")

    #     except Exception as e:
    #         st.error(f"❌ Błąd generowania obrazu: {e}")

    # --- 3) Wizualizacja ---

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        img_size = st.selectbox("🖼️ Rozmiar", ["256x256", "512x512", "1024x1024"], index=2)
    with col_i2:
        st.caption("DALL·E 2 obsługuje tylko powyższe rozmiary")

    gen_img_clicked = st.button("🌌 Generuj wizualizację (DALL·E 2)")

    if gen_img_clicked:
        if not openai_key:
            st.error("Podaj OpenAI API Key.")
            st.stop()
        try:
            client = OpenAI(api_key=openai_key)
            prompt_text = dalle_prompt(user_prompt)

            with st.spinner("Generuję obraz…"):
                resp = client.images.generate(
                    model="dall-e-2",   # DALL·E 2
                    prompt=prompt_text,
                    size=img_size,
                    n=1,
                )

            # pobieramy URL obrazu
            img_url = resp.data[0].url  

            # pokazujemy w Streamlit
            st.image(img_url, caption="Twoja wizualizacja ✨", use_container_width=True)

            # przycisk pobierania
            img_bytes = requests.get(img_url).content
            st.download_button(
                "💾 Pobierz PNG",
                data=img_bytes,
                file_name=f"mind_visualization_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png",
            )

            # zapis do session_state
            st.session_state["mind_image"] = img_bytes
            st.success("🖼️ Wizualizacja gotowa!")

        except Exception as e:
            st.error(f"❌ Błąd generowania obrazu: {e}")


# ---------------- SPORT ROOM (placeholder) ----------------
elif st.session_state["room"] == "sport":
    st.title("🏋️ Sport (Wkrótce...)")
    greet_user("Hejka")
    st.info("Tu pojawi się pokój sportu (np. cardio, siła, mobilność).")

# ---------------- DIETA ROOM (placeholder) ----------------
elif st.session_state["room"] == "dieta":
    st.title("🍎 Dieta (Wkrótce...)")
    greet_user("Cześć")
    st.info("Tu pojawi się pokój diety (np. zdrowe posiłki, woda, brak alkoholu).")

# ---------------- STUDY ROOM (placeholder) ----------------
elif st.session_state["room"] == "study":
    st.title("📚 Nauka (Wkrótce...)")
    greet_user("Hej")
    st.info("Tu pojawi się pokój nauki (np. pomodoro, fiszki, notatki).")

# ---------------- FINANCE ROOM (placeholder) ----------------
elif st.session_state["room"] == "finance":
    st.title("💸 Finanse (Wkrótce...)")
    greet_user("Dzień dobry")
    st.info("Tu pojawi się pokój finansów (np. budżet, oszczędności, brak zbędnych wydatków).")

# ---------------- SOCIAL ROOM (placeholder) ----------------
elif st.session_state["room"] == "social":
    st.title("🤝 Social (Wkrótce...)")
    greet_user("Witaj")
    st.info("Tu pojawi się pokój relacji (np. networking, kontakt z przyjaciółmi).")

# ---------------- ORDER ROOM (placeholder) ----------------
elif st.session_state["room"] == "order":
    st.title("🧹 Porządek (Wkrótce...)")
    greet_user("Hejka")
    st.info("Tu pojawi się pokój porządku (np. sprzątanie, minimalizm).")
