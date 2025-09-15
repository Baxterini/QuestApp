QuestApp 🧙‍♂️ – osobisty „Quest Master”

Aplikacja Streamlit, która wspiera zdrowe nawyki i uważność.
Dwa pokoje: Motywator zdrowia (woda + nawyki) oraz Mind (medytacje z AI + odsłuch).

✨ Funkcje (MVP)

Motywator zdrowia 💪🥦

Licznik wody 💧 (szklanki / cel dzienny)

Nawyki codzienne 🌞 (np. rozgrzewka, spacer)

Tryb 30 dni (zwykły / hard mode)

Mind 🧘

Generowanie krótkiej medytacji (OpenAI, GPT-4o-mini)

Odsłuch (gTTS → MP3)

st.download_button – pobierz wygenerowaną medytację

🔧 Wymagania

Python 3.10+

Patrz requirements.txt oraz packages.txt (zawiera ffmpeg dla pydub)

⚙️ Instalacja (lokalnie)
# (opcjonalnie) nowe środowisko
conda create -n questapp python=3.10 -y
conda activate questapp

# instalacja zależności
pip install -r requirements.txt

# uruchomienie
streamlit run app.py
