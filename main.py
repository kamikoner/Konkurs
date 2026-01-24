import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re
import base64

# --- KONFIGURACJA ---
URL_API = "https://script.google.com/macros/s/AKfycbypVdCzKAyg7X6o0ZPNQPYbt9fB2NUAbxwIjQZruGghPGEpdcbamDpAhGCso0g3xp7Q/exec"

st.set_page_config(page_title="Konkursownik", layout="wide", page_icon="📸")

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# --- FUNKCJE ---
def sformatuj_date(data_str):
    if not data_str or data_str == 'Brak': return "Brak"
    try: return pd.to_datetime(data_str).strftime('%d.%m.%Y o %H:%M')
    except: return data_str

@st.cache_data(ttl=600)
def pobierz_dane_z_chmury():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except: return pd.DataFrame(), pd.DataFrame()

def wyslij_i_odswiez(payload):
    try:
        requests.post(URL_API, data=json.dumps(payload), timeout=20)
        st.cache_data.clear()
        return True
    except: return False

# --- UI ---
st.title("📸 Konkursownik")

df_k, df_z = pobierz_dane_z_chmury()

if not df_k.empty:
    wybor = st.selectbox("Wybierz konkurs:", df_k['Konkurs'].tolist())
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = int(k_info['ID'])

    # --- DODAWANIE ZDJĘCIA ---
    with st.expander("➕ DODAJ ZGŁOSZENIE ZE ZDJĘCIEM", expanded=True):
        n_p = st.text_input("Numer paragonu", key=f"np_{st.session_state.form_version}")
        txt = st.text_area("Twoja praca", key=f"txt_{st.session_state.form_version}")
        
        # Nowe pole: Uploader
        uploaded_file = st.file_uploader("Dodaj zdjęcie paragonu (opcjonalnie)", type=['jpg', 'jpeg', 'png'], key=f"file_{st.session_state.form_version}")
        
        if st.button("💾 Zapisz zgłoszenie"):
            if n_p and txt:
                file_data, file_name, mime_type = "", "", ""
                if uploaded_file:
                    file_data = base64.b64encode(uploaded_file.read()).decode()
                    file_name = uploaded_file.name
                    mime_type = uploaded_file.type

                payload = {
                    "type": "zgloszenia", "action": "add", 
                    "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                    "konkurs_id": k_id, "Nr_Paragonu": n_p, "Tekst": txt,
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "fileData": file_data, "fileName": file_name, "mimeType": mime_type
                }
                if wyslij_i_odswiez(payload):
                    st.session_state.form_version += 1
                    st.rerun()

    # --- LISTA ZGŁOSZEŃ ---
    st.divider()
    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        for _, row in moje_z.iterrows():
            with st.container(border=True):
                st.write(f"🧾 **Paragon: {row['Nr_Paragonu']}**")
                st.write(f"💬 {row['Tekst']}")
                
                # WYŚWIETLANIE ZDJĘCIA
                url = row.get('Zdjecie_URL', '')
                if url and url.startswith("http"):
                    # Mały podgląd lub link
                    st.link_button("📂 Zobacz/Pobierz zdjęcie paragonu", url)
                else:
                    st.caption("Brak zdjęcia dla tego zgłoszenia.")
                
                # Przyciski usuwania/edycji (jak w v17)
                # ...
else:
    st.info("Baza pusta.")
