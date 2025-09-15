# health_motywator.py
import datetime as dt
import json
import random
import hashlib
from pathlib import Path
from typing import List

import streamlit as st
from pydantic import BaseModel
from streamlit_sortables import sort_items

# ---------------- UI / STYL ----------------
st.set_page_config(page_title="Health Motywator", page_icon="🚵", layout="centered")

PEACH = "#FFDAB9"  # PeachPuff
st.markdown(
    f"""
    <style>
    .stApp {{
        background: {PEACH};
        background: linear-gradient(180deg, {PEACH} 0%, #fff7f2 100%);
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

# ---------------- DANE ----------------
DATA_FILE = Path("health_data.json")

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"days": {}, "challenge": {"start_date": None}}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

data = load_data()

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

def hash_key(s: str) -> str:
    """(3) Krótkie, stabilne klucze dla przycisków/komponentów."""
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]

# ---------------- STAN DNIA ----------------
today = dt.date.today().isoformat()
st.title("🚵 Health Motywator — Bike Quest")
st.caption(f"Dzień: {today}")

# Przycisk trybu „Hard” — ale (2) tryb zamrażamy na dany dzień
ui_mode_toggle = st.toggle(
    "Hard mode (wszystkie cele)",
    value=False,
    help="Wyłączone = Light (3 filary). Włączone = pełny zestaw."
)

# Wczytaj/utwórz day_state
day_state = data["days"].get(today) or {
    "mode": "Hard" if ui_mode_toggle else "Light",  # (2) zapisz tryb w stanie dnia
    "done": {},
    "water_ml": 0,
    "notes": "",
    "bonus": random.choice(BONUS_POOL),
}
# Zamrożony tryb na dziś:
effective_mode_is_hard = (day_state.get("mode", "Light") == "Hard")
tasks = LIGHT_TASKS + (EXTRA_TASKS if effective_mode_is_hard else [])

# Upewnij się, że 'done' ma klucze wszystkich obecnych zadań
for t in tasks:
    day_state["done"].setdefault(t.name, False)

data["days"][today] = day_state
save_data(data)

# --- KANBAN: status + kolejność kart ---
if "status" not in day_state:
    day_state["status"] = {
        t.name: ("Done" if day_state["done"].get(t.name) else "To do") for t in tasks
    }

if "order" not in day_state:
    day_state["order"] = {"To do": [], "Doing": [], "Done": []}
    for t in tasks:
        s = day_state["status"][t.name]
        if t.name not in day_state["order"][s]:
            day_state["order"][s].append(t.name)

# (1) Sprzątanie kart po zmianie listy zadań + dopisanie brakujących
names_set = {t.name for t in tasks}
for col in ("To do", "Doing", "Done"):
    day_state["order"][col] = [n for n in day_state["order"][col] if n in names_set]

for t in tasks:
    s = day_state["status"].get(t.name, "To do")
    day_state["status"][t.name] = s
    if t.name not in day_state["order"][s]:
        day_state["order"][s].append(t.name)

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

# ---- (4) LAYOUT SWITCH z fallbackiem ----
data.setdefault("ui", {}).setdefault("layout", "Classic")
try:
    layout = st.segmented_control(
        "Układ",
        options=["Classic", "Kanban", "Focus", "Dashboard"],
        selection_mode="single",
        default=data["ui"]["layout"]
    )
except Exception:
    # Fallback dla starszych wersji Streamlit
    opts = ["Classic", "Kanban", "Focus", "Dashboard"]
    layout = st.radio("Układ", opts, index=opts.index(data["ui"]["layout"]))

if layout != data["ui"]["layout"]:
    data["ui"]["layout"] = layout
    save_data(data)

def on_check_change(name):
    day_state["done"][name] = st.session_state[f"cb_{name}"]
    data["days"][today] = day_state
    save_data(data)

def render_classic(tasks, day_state):
    for t in tasks:
        st.checkbox(
            f"**{t.name}** — _{t.category}_",
            value=day_state["done"].get(t.name, False),
            key=f"cb_{t.name}",
            help=t.hint,
            on_change=on_check_change,
            args=(t.name,),
        )

def render_kanban(tasks, day_state):
    st.caption("Przeciągaj karty w obrębie kolumn; między kolumnami przenoś przyciskami.")

    names = {t.name: t for t in tasks}
    order = day_state["order"]
    status = day_state["status"]

    cols = st.columns(3)
    columns = ["To do", "Doing", "Done"]

    for col_name, col in zip(columns, cols):
        with col:
            st.subheader(col_name)

            # DRAG: sortowanie wewnątrz kolumny
            current = [n for n in order[col_name] if n in names]
            new_order = sort_items(current, direction="vertical", key=f"sort_{col_name}")
            if new_order != order[col_name]:
                order[col_name] = new_order
                save_data(data)

            # Karty + przyciski przenoszące między kolumnami
            for name in new_order:
                t = names[name]
                with st.container(border=True):
                    st.markdown(
                        f"**{t.name}**  \n_{t.category}_  \n<small>{t.hint}</small>",
                        unsafe_allow_html=True
                    )
                    b1, b2, b3 = st.columns([1,1,1])
                    # ◀️ w lewo
                    with b1:
                        k = hash_key(f"left_{col_name}_{name}")
                        if col_name != "To do" and st.button("◀️", key=k):
                            order[col_name].remove(name)
                            dest = "Doing" if col_name == "Done" else "To do"
                            order[dest].append(name)
                            status[name] = dest
                            day_state["done"][name] = (dest == "Done")
                            save_data(data); st.rerun()
                    # ▶️ w prawo
                    with b2:
                        k = hash_key(f"right_{col_name}_{name}")
                        if col_name != "Done" and st.button("▶️", key=k):
                            order[col_name].remove(name)
                            dest = "Doing" if col_name == "To do" else "Done"
                            order[dest].append(name)
                            status[name] = dest
                            day_state["done"][name] = (dest == "Done")
                            save_data(data); st.rerun()
                    # status
                    with b3:
                        st.caption("✅ ukończone" if col_name == "Done" else ("⏳ w trakcie" if col_name == "Doing" else "🗒️ do zrobienia"))

def render_focus(tasks, day_state):
    st.subheader("🎯 Focus na 1–3 kluczowe")
    focus = [t for t in tasks if not day_state["done"].get(t.name)][:3]
    for t in focus:
        k = hash_key(f"focus_{t.name}")
        if st.button(f"Zrób teraz: {t.name}", key=k):
            day_state["done"][t.name] = True
            save_data(data); st.rerun()

def render_dashboard(tasks, day_state):
    st.subheader("📊 Dashboard dnia")
    completed_local = sum(day_state["done"].values())
    st.metric("Zadania ukończone", f"{completed_local}/{len(tasks)}")
    st.progress(completed_local/max(1,len(tasks)))
    st.write("✅", ", ".join([t for t, v in day_state["done"].items() if v]) or "—")
    st.write("🕗", ", ".join([t for t, v in day_state["done"].items() if not v]) or "—")

# Wywołanie wybranego widoku
if layout == "Classic":
    render_classic(tasks, day_state)
elif layout == "Kanban":
    render_kanban(tasks, day_state)
elif layout == "Focus":
    render_focus(tasks, day_state)
else:
    render_dashboard(tasks, day_state)

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
            # (5) gracz na mecie 👑
            if i == total and days_passed >= total:
                row.append("👑")        # osiągnięta meta
            elif i == total:
                row.append("🏰")        # meta (jeszcze nie osiągnięta)
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
