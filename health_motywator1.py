import datetime as dt
import json
import random
from pathlib import Path
from typing import List

import streamlit as st
from pydantic import BaseModel

st.set_page_config(page_title="Health Motywator", page_icon="💪", layout="centered")

DATA_FILE = Path("health_data.json")

# ---------- MODELE ----------
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

# ---------- PERSISTENCJA ----------
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # domyślna struktura
    return {"days": {}, "challenge": {"start_date": None}, "last_bonus": {}}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

data = load_data()

# ---------- USTAWIENIA DNIA ----------
today = dt.date.today().isoformat()
st.title("💪 Health Motywator")
st.caption(f"Dzień: {today}")

mode = st.toggle("Hard mode (wszystkie cele)", value=False, help="Wyłączone = Light (3 filary). Włączone = pełny zestaw.")
tasks = LIGHT_TASKS + (EXTRA_TASKS if mode else [])

# zainicjalizuj dzień
day_state = data["days"].get(today) or {
    "done": {t.name: False for t in tasks},
    "water_ml": 0,
    "notes": "",
    "bonus": random.choice(BONUS_POOL),
}
# dostosuj do bieżącej listy zadań (gdy zmienisz tryb)
for t in tasks:
    day_state["done"].setdefault(t.name, False)

data["days"][today] = day_state
save_data(data)

# ---------- 30 DNI BEZ ALKOHOLU ----------
st.subheader("🧱 Wyzwanie: 30 dni bez alkoholu")

start_date_str = data["challenge"].get("start_date")
cols = st.columns([2,1,1])

with cols[0]:
    start_label = "Ustaw datę startu wyzwania"
    start_date = st.date_input(start_label, value=dt.date.fromisoformat(start_date_str) if start_date_str else dt.date.today())
with cols[1]:
    if st.button("Start od dziś"):
        data["challenge"]["start_date"] = dt.date.today().isoformat()
        save_data(data)
        st.rerun()
with cols[2]:
    if st.button("Wyczyść start"):
        data["challenge"]["start_date"] = None
        save_data(data)
        st.rerun()

# jeśli zmieniono w kalendarzu — zapisz
if start_date_str != (start_date.isoformat() if start_date else None):
    data["challenge"]["start_date"] = start_date.isoformat() if start_date else None
    save_data(data)

start_date_str = data["challenge"].get("start_date")
if start_date_str:
    start_date_dt = dt.date.fromisoformat(start_date_str)
    # dzień 1 = dzień startu
    days_passed = (dt.date.today() - start_date_dt).days + 1
    days_passed = max(0, min(days_passed, 30))
    days_left = 30 - days_passed
    pct = days_passed / 30
    st.progress(pct, text=f"Postęp: {days_passed}/30 dni")
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Dni minęły", days_passed)
    mcol2.metric("Zostało", days_left)
    mcol3.metric("Start", start_date_dt.strftime("%Y-%m-%d"))

    if days_passed >= 30:
        st.success("🏆 30 dni zaliczone! Jeśli chcesz, wyznacz nowy cel albo wydłuż serię.")
else:
    st.info("Ustaw datę startu — od niej liczymy 30 dni i odliczamy postęp.")

st.divider()

# ---------- PODSUMOWANIE CELÓW DNIA ----------
col1, col2 = st.columns(2)
with col1:
    st.subheader("🎯 Cele na dziś")
with col2:
    completed = sum(day_state["done"].get(t.name, False) for t in tasks)
    st.metric("Postęp", f"{completed}/{len(tasks)}")

# ---------- CHECKLISTY ----------
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

# ---------- LICZNIK WODY ----------
st.subheader("💧 Licznik wody (cel 2000 ml)")
col_w1, col_w2, col_w3 = st.columns([1,2,1])

def adjust_water(delta):
    day_state["water_ml"] = max(0, day_state["water_ml"] + delta)
    data["days"][today] = day_state
    save_data(data)

with col_w1:
    if st.button("-250 ml"):
        adjust_water(-250)
with col_w2:
    st.progress(min(day_state["water_ml"]/2000, 1.0))
    st.write(f"Wypite: **{day_state['water_ml']} ml / 2000 ml**")
with col_w3:
    if st.button("+250 ml"):
        adjust_water(+250)

# ---------- BONUS DNIA ----------
st.info(f"🎲 Bonus dnia: **{day_state['bonus']}** (opcjonalnie)")

st.divider()

# ---------- NOTATKI ----------
st.subheader("📝 Notatki na dziś")
notes_val = st.text_area("Co warto zapamiętać (myśli, spostrzeżenia, wdzięczność)?",
                         value=day_state.get("notes", ""), height=140,
                         placeholder="Np. „Dziś najtrudniejsza była ochota na słodkie po obiedzie…”")
if st.button("Zapisz notatki"):
    day_state["notes"] = notes_val
    data["days"][today] = day_state
    save_data(data)
    st.success("Zapisano notatki.")

# ---------- MOTYWACJA KONTEKSTOWA ----------
def motivation(completed, total, days_passed, start_set):
    if not start_set:
        return "Każda duża zmiana zaczyna się od decyzji. Ustaw datę startu i zrób dziś pierwszy krok."
    if days_passed == 1:
        return "Dzień 1 — najważniejszy. Ustal rytm: prosto, spokojnie, konsekwentnie."
    if days_passed in (7, 14, 21):
        return f"To już {days_passed} dni ciągłości. Małe rzeczy, codziennie — tworzą wielkie efekty."
    if completed == total and total > 0:
        return "Pięknie! Dziś komplet. Odłóż koronę na nocnym stoliku i jutro zrób to znowu 👑"
    if completed >= max(1, total//2):
        return "Już ponad połowa na dziś. Jeszcze trochę i zamykasz dzień na zielono!"
    return "Nie musisz robić wszystkiego naraz. Zaznacz jedną rzecz teraz — rozruch to 80% sukcesu."

mot_msg = motivation(completed, len(tasks), days_passed if data["challenge"]["start_date"] else 0, bool(data["challenge"]["start_date"]))
st.success("💬 " + mot_msg)

st.caption("Tip: Ten progress bar 30-dniowy łatwo podmienić na 🧩 puzzle/obrazek wypełniający się dzień po dniu.")
