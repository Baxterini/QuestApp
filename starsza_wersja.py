import datetime as dt
import random
import streamlit as st
from pydantic import BaseModel
from typing import List

st.set_page_config(page_title="Health Motywator", page_icon="💪", layout="centered")

# ---------- Modele ----------
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
    "Krótka medytacja wdzięczności (3 min)",
    "Wejdź po schodach zamiast windą",
]

# ---------- Ustawienia dnia ----------
today = dt.date.today().isoformat()
st.title("💪 Health Motywator")
st.caption(f"Dzień: {today}")

mode = st.toggle("Hard mode (wszystkie cele)", value=False, help="Wyłączone = Light (3 filary). Włączone = pełny zestaw.")
tasks = LIGHT_TASKS + (EXTRA_TASKS if mode else [])

# ---------- Stan dzienny ----------
if "done" not in st.session_state or st.session_state.get("date") != today:
    st.session_state["done"] = {t.name: False for t in tasks}
    st.session_state["water_ml"] = 0
    st.session_state["date"] = today
    st.session_state["bonus"] = random.choice(BONUS_POOL)

# dopasuj stan do listy zadań (gdy przełączysz tryb)
for t in tasks:
    st.session_state["done"].setdefault(t.name, False)

# ---------- Podsumowanie ----------
col1, col2 = st.columns(2)
with col1:
    st.subheader("🎯 Cele na dziś")
with col2:
    completed = sum(st.session_state["done"].get(t.name, False) for t in tasks)
    st.metric("Postęp", f"{completed}/{len(tasks)}")

# ---------- Checklisty ----------
for t in tasks:
    st.checkbox(
        f"**{t.name}** — _{t.category}_",
        value=st.session_state["done"].get(t.name, False),
        key=f"cb_{t.name}",
        help=t.hint,
        on_change=lambda key=t.name: st.session_state["done"].update({key: st.session_state[f'cb_{key}']})
    )

st.divider()

# ---------- Licznik wody ----------
st.subheader("💧 Licznik wody")
col_w1, col_w2, col_w3 = st.columns([1,2,1])
with col_w1:
    if st.button("-250 ml"):
        st.session_state["water_ml"] = max(0, st.session_state["water_ml"] - 250)
with col_w2:
    st.progress(min(st.session_state["water_ml"]/2000, 1.0))
    st.write(f"Wypite: **{st.session_state['water_ml']} ml / 2000 ml**")
with col_w3:
    if st.button("+250 ml"):
        st.session_state["water_ml"] += 250

st.info(f"🎲 Bonus dnia: **{st.session_state['bonus']}** (opcjonalnie)")

# ---------- Motywacja ----------
tips = [
    "Małe kroki > wielkie zrywy. Liczy się ciągłość.",
    "Jeśli dziś nie idealnie — jutro wracasz na tor. Zero dramatu.",
    "Woda, sen i ruch to święta trójca — reszta to bonusy.",
]
st.success("💬 " + random.choice(tips))
