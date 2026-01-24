import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA ---
URL_API = "https://script.google.com/macros/s/AKfycbx9yyR8k46tU6AFO8UOKCcxEbHeXH0Ka-rYZNAUK9LbfWQF9JRzFfCf-n7ma6mgu6J5/exec"

st.set_page_config(page_title="Konkursownik PRO v6", layout="wide", page_icon="🏆")

def pobierz_wszystko():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except:
        return pd.DataFrame(), pd.DataFrame()

def wyslij_do_bazy(payload):
    requests.post(URL_API, data=json.dumps(payload))

# --- INTERFEJS ---
st.title("🏆 Ekspercki Manager Konkursowy")

with st.sidebar:
    st.header("📥 Nowy Konkurs")
    json_input = st.text_area("Wklej JSON z czatu Gemini:", height=200)
    if st.button("Dodaj Konkurs"):
        try:
            clean_json = json_input.strip()
            if clean_json.startswith("```"):
                clean_json = clean_json.replace("```json", "", 1).replace("```", "", 1)
            d = json.loads(clean_json.strip())
            
            payload = {
                "type": "konkursy",
                "action": "add",
                "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                "Konkurs": d.get('Konkurs', ''),
                "Koniec": d.get('Koniec', ''),
                "Zadanie": d.get('Pelne_Zadanie', ''),
                "Limit": d.get('Limit', ''),
                "Kryteria": d.get('Kryteria', ''),
                "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                "Paragon": d.get('Paragon', ''),
                "Agencja": d.get('Agencja', 'Brak danych'),
                "Data_Wynikow": d.get('Data_Wynikow', 'Brak danych')
            }
            wyslij_do_bazy(payload)
            st.success("Dodano!")
            st.rerun()
        except: st.error("Błąd formatu JSON!")

df_k, df_z = pobierz_wszystko()

if not df_k.empty:
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        wybor = st.selectbox("Wybierz konkurs:", df_k['Konkurs'].tolist())
    
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = k_info['ID']

    with col_del:
        st.write("")
        if st.button("🗑️ Usuń konkurs", use_container_width=True):
            wyslij_do_bazy({"type": "konkursy", "action": "delete", "id": k_id})
            wyslij_do_bazy({"type": "zgloszenia", "action": "delete", "konkurs_id": k_id})
            st.rerun()

    st.divider()

    # WYŚWIETLANIE SZCZEGÓŁÓW
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Koniec", k_info['Koniec'])
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    st.info(f"📣 **Kiedy wyniki:** {k_info.get('Data_Wynikow', 'Brak danych')}")

    c1, c2 = st.columns(2)
    with c1:
        st.warning(f"⚖️ **Kryteria:** {k_info['Kryteria']}")
    with c2:
        st.success(f"🔍 **Jaki numer paragonu:** {k_info['Nr_Paragonu_Info']}")
    
    with st.expander("📝 Pełne zadanie"):
        st.write(k_info['Zadanie'])

    # ZGŁOSZENIA
    st.divider()
    st.subheader("🎫 Twoje zgłoszenia")
    with st.expander("➕ Dodaj zgłoszenie"):
        nr_p = st.text_input("Nr paragonu")
        tekst = st.text_area("Twoja praca")
        if st.button("Zapisz"):
            wyslij_do_bazy({"type": "zgloszenia", "action": "add", "konkurs_id": k_id, "Nr_Paragonu": nr_p, "Tekst": tekst, "Data": datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.rerun()

    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        for _, row in moje_z.iterrows():
            with st.container(border=True):
                st.write(f"🧾 **Paragon:** {row['Nr_Paragonu']} | 💬 {row['Tekst']}")
else:
    st.info("Baza jest pusta.")
