import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA ---
# TUTAJ WKLEJ SWÓJ LINK Z WDROŻENIA APPS SCRIPT
URL_API = "https://script.google.com/macros/s/AKfycbzHvyBE4VEIGcIQNIMTicU1Epi9WfkV8CWtN-fbMlFzJFspRhNCJvf4ljrD2GIsSWDB/exec"

st.set_page_config(page_title="Konkursownik PRO Cloud", layout="wide")

# --- FUNKCJE KOMUNIKACJI ---
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

# BOCZNY PANEL - IMPORT JSON OD GEMINI
with st.sidebar:
    st.header("📥 Nowy Konkurs")
    json_input = st.text_area("Wklej JSON z czatu Gemini:", height=200)
    if st.button("Dodaj Konkurs"):
        try:
            d = json.loads(json_input)
            payload = {
                "type": "konkursy",
                "action": "add",
                "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                "Konkurs": d['Konkurs'],
                "Koniec": d['Koniec'],
                "Zadanie": d['Pelne_Zadanie'],
                "Limit": d['Limit'],
                "Kryteria": d.get('Kryteria', ''),
                "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                "Paragon": d['Paragon']
            }
            wyslij_do_bazy(payload)
            st.success("Dodano do Arkusza!")
            st.rerun()
        except:
            st.error("Błąd formatu JSON!")

# POBIERANIE DANYCH
df_k, df_z = pobierz_wszystko()

if not df_k.empty:
    # WYBÓR KONKURSU
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        lista_k = df_k['Konkurs'].tolist()
        wybor = st.selectbox("Zarządzaj konkursem:", lista_k)
    
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = k_info['ID']

    with col_del:
        st.write("")
        if st.button("🗑️ Usuń konkurs"):
            wyslij_do_bazy({"type": "konkursy", "action": "delete", "id": k_id})
            wyslij_do_bazy({"type": "zgloszenia", "action": "delete", "konkurs_id": k_id})
            st.warning("Usunięto!")
            st.rerun()

    st.divider()

    # WYŚWIETLANIE SZCZEGÓŁÓW
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"📅 **Koniec:** {k_info['Koniec']}\n\n⚖️ **Kryteria:** {k_info['Kryteria']}")
    with c2:
        st.success(f"🧾 **Nr paragonu:** {k_info['Nr_Paragonu_Info']}\n\n📏 **Limit:** {k_info['Limit']}")
    
    with st.expander("📝 Zobacz pełne zadanie"):
        st.write(k_info['Zadanie'])

    # SEKCJA ZGŁOSZEŃ (WIELE PARAGONÓW)
    st.divider()
    st.subheader(f"🎫 Twoje zgłoszenia")

    with st.expander("➕ Dodaj nowe zgłoszenie do tego konkursu"):
        nr_p = st.text_input("Numer paragonu")
        txt_zgl = st.text_area("Twoja praca konkursowa", height=150)
        
        # Licznik znaków
        limit_val = str(k_info['Limit'])
        max_ch = int(limit_val) if limit_val.isdigit() else 2000
        st.caption(f"Znaki: {len(txt_zgl)} / {max_ch}")
        
        if st.button("Zapisz zgłoszenie"):
            payload_z = {
                "type": "zgloszenia",
                "action": "add",
                "konkurs_id": k_id,
                "Nr_Paragonu": nr_p,
                "Tekst": txt_zgl,
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            wyslij_do_bazy(payload_z)
            st.success("Zgłoszenie zapisane!")
            st.rerun()

    # LISTA ZAPISANYCH ZGŁOSZEŃ
    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        for _, row in moje_z.iterrows():
            with st.container(border=True):
                st.write(f"🧾 **Paragon:** {row['Nr_Paragonu']}")
                st.write(f"💬 {row['Tekst']}")
                st.caption(f"Data: {row['Data']}")
else:
    st.info("Baza jest pusta. Dodaj konkurs w panelu bocznym.")

