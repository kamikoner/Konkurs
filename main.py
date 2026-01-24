import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA ---
# TUTAJ WKLEJ SWÓJ LINK Z WDROŻENIA APPS SCRIPT (Web App URL)
URL_API = "https://script.google.com/macros/s/AKfycbx9yyR8k46tU6AFO8UOKCcxEbHeXH0Ka-rYZNAUK9LbfWQF9JRzFfCf-n7ma6mgu6J5/exec"

st.set_page_config(page_title="Konkursownik PRO v6", layout="wide", page_icon="🏆")

# --- FUNKCJE KOMUNIKACJI Z ARKUSZEM ---
def pobierz_wszystko():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        # Tworzenie DataFrame z danych (zakładki konkursy i zgloszenia)
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

def wyslij_do_bazy(payload):
    try:
        r = requests.post(URL_API, data=json.dumps(payload))
        if r.status_code == 200:
            return True
        else:
            st.error(f"Błąd serwera: {r.status_code}")
            return False
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return False

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🏆 Ekspercki Manager Konkursowy v6")
st.caption("Synchronizacja z Google Sheets | Agencja | Data Wyników | Multi-Paragon")

# BOCZNY PANEL - IMPORT NOWEGO KONKURSU (ANALIZA AI)
with st.sidebar:
    st.header("📥 Nowy Konkurs")
    st.write("Wklej analizę od Gemini:")
    json_input = st.text_area("JSON Input", height=250, label_visibility="collapsed")
    
    if st.button("🚀 Dodaj Konkurs do Bazy", use_container_width=True):
        if json_input:
            try:
                # PANCERNE CZYSZCZENIE JSON (wyciąga tylko tekst między { a })
                match = re.search(r'\{.*\}', json_input, re.DOTALL)
                if match:
                    clean_json = match.group()
                else:
                    st.error("Nie znaleziono poprawnego kodu JSON w tekście!")
                    st.stop()

                d = json.loads(clean_json)
                
                # Przygotowanie danych dla Apps Script (10 kolumn dla konkursu)
                payload = {
                    "type": "konkursy",
                    "action": "add",
                    "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                    "Konkurs": d.get('Konkurs', 'Bez nazwy'),
                    "Koniec": d.get('Koniec', ''),
                    "Zadanie": d.get('Pelne_Zadanie', ''),
                    "Limit": d.get('Limit', 'Brak'),
                    "Kryteria": d.get('Kryteria', 'Brak danych'),
                    "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', 'Nieokreślono'),
                    "Paragon": d.get('Paragon', 'Nie'),
                    "Agencja": d.get('Agencja', 'Brak danych'),
                    "Data_Wynikow": d.get('Data_Wynikow', 'Brak danych')
                }
                
                if wyslij_do_bazy(payload):
                    st.success("Konkurs zapisany w chmurze!")
                    st.rerun()
            except Exception as e:
                st.error(f"Błąd danych: {e}")
        else:
            st.warning("Najpierw wklej dane JSON!")

# POBIERANIE DANYCH
df_k, df_z = pobierz_wszystko()

if not df_k.empty:
    # WYBÓR KONKURSU
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        lista_k = df_k['Konkurs'].tolist()
        wybor = st.selectbox("Wybierz konkurs:", lista_k)
    
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = k_info['ID']

    with col_del:
        st.write("") 
        if st.button("🗑️ Usuń konkurs", use_container_width=True):
            wyslij_do_bazy({"type": "konkursy", "action": "delete", "id": k_id})
            wyslij_do_bazy({"type": "zgloszenia", "action": "delete", "konkurs_id": k_id})
            st.warning("Usunięto pomyślnie!")
            st.rerun()

    st.divider()

    # SEKCJA 1: KLUCZOWE METRYKI
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Koniec zgłoszeń", k_info['Koniec'])
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    # SEKCJA 2: SZCZEGÓŁY STRATEGICZNE
    st.info(f"📣 **Kiedy i gdzie wyniki:** {k_info.get('Data_Wynikow', 'Brak danych')}")

    c_kryst, c_paragon = st.columns(2)
    with c_kryst:
        st.warning(f"⚖️ **Kryteria Jury:**\n\n{k_info['Kryteria']}")
    with c_paragon:
        st.success(f"🔍 **Instrukcja numeru paragonu:**\n\n{k_info['Nr_Paragonu_Info']}")
    
    with st.expander("📝 Pełna treść zadania konkursowego"):
        st.write(k_info['Zadanie'])

    # SEKCJA 3: ZGŁOSZENIA (MULTI-PARAGON)
    st.divider()
    st.subheader(f"🎫 Twoje zgłoszenia")

    with st.expander("➕ Dodaj nowe zgłoszenie do tego konkursu"):
        nr_p = st.text_input("Numer paragonu / dowodu zakupu")
        txt_zgl = st.text_area("Twoja praca konkursowa", height=150)
        
        # Licznik znaków (wyciąga cyfry z limitu)
        limit_digits = "".join(filter(str.isdigit, str(k_info['Limit'])))
        max_ch = int(limit_digits) if limit_digits else 2000
        
        st.caption(f"Znaki: {len(txt_zgl)} / {max_ch}")
        if len(txt_zgl) > max_ch:
            st.error("Przekroczono limit znaków!")

        if st.button("💾 Zapisz zgłoszenie"):
            if nr_p and txt_zgl:
                payload_z = {
                    "type": "zgloszenia",
                    "action": "add",
                    "konkurs_id": k_id,
                    "Nr_Paragonu": nr_p,
                    "Tekst": txt_zgl,
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                if wyslij_do_bazy(payload_z):
                    st.success("Zgłoszenie zapisane!")
                    st.rerun()
            else:
                st.warning("Uzupełnij numer paragonu i tekst.")

    # WYŚWIETLANIE HISTORII ZGŁOSZEŃ
    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        if not moje_z.empty:
            for _, row in moje_z.iterrows():
                with st.container(border=True):
                    st.write(f"🧾 **Paragon:** {row['Nr_Paragonu']}")
                    st.write(f"💬 {row['Tekst']}")
                    st.caption(f"Dodano: {row['Data']}")
        else:
            st.info("Brak zgłoszeń dla tego konkursu.")
else:
    st.info("Baza konkursów jest pusta. Użyj panelu bocznego, aby dodać pierwszy konkurs.")
