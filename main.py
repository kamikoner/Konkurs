import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA ---
URL_API = "https://script.google.com/macros/s/AKfycbwWKkt_CCd8dIU9EOwonm7wr62mBd8y1bwGfLjlHVZrkBn2sZbF5GewnxCfoDHJZiP9/exec"

st.set_page_config(page_title="Konkursownik", layout="wide", page_icon="⚡")

# --- 1. FUNKCJE POMOCNICZE (DATY I CACHE) ---

def sformatuj_date(data_str):
    if not data_str or data_str == 'Brak': return "Brak"
    try:
        dt = pd.to_datetime(data_str)
        return dt.strftime('%d.%m.%Y o %H:%M')
    except: return data_str

def ile_dni_zostalo(data_konca_str):
    try:
        data_konca = pd.to_datetime(data_konca_str).date()
        dzis = datetime.now().date()
        roznica = (data_konca - dzis).days
        if roznica < 0: return " (Zakończony)"
        elif roznica == 0: return " (TO DZISIAJ!)"
        elif roznica == 1: return " (Został 1 dzień)"
        else: return f" (Zostało {roznica} dni)"
    except: return ""

# PRZYSPIESZENIE: Pobieranie danych z pamięci podręcznej (Cache)
@st.cache_data(ttl=600) # Dane ważne przez 10 minut
def pobierz_dane_z_chmury():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except:
        return pd.DataFrame(), pd.DataFrame()

def wyslij_i_odswiez(payload):
    try:
        with st.spinner("Zapisywanie w Arkuszu Google..."):
            requests.post(URL_API, data=json.dumps(payload))
            st.cache_data.clear() # Czyścimy pamięć, aby pobrać nowe dane po zapisie
            return True
    except:
        return False

# --- 2. INTERFEJS UŻYTKOWNIKA ---

st.title("⚡ Konkursownik Mateusza")

with st.sidebar:
    st.header("⚙️ Zarządzanie")
    # Przycisk ręcznego odświeżania
    if st.button("🔄 Synchronizuj z Google", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.header("📥 Nowy Konkurs")
    json_in = st.text_area("Wklej JSON z Gemini:", height=150)
    if st.button("🚀 Dodaj do Bazy", use_container_width=True):
        match = re.search(r'\{.*\}', json_in, re.DOTALL)
        if match:
            d = json.loads(match.group())
            p = {"type": "konkursy", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                 "Konkurs": d.get('Konkurs', ''), "Koniec": d.get('Koniec', ''), "Zadanie": d.get('Pelne_Zadanie', ''),
                 "Limit": d.get('Limit', ''), "Kryteria": d.get('Kryteria', ''), "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                 "Paragon": d.get('Paragon', ''), "Agencja": d.get('Agencja', ''), "Data_Wynikow": d.get('Data_Wynikow', '')}
            if wyslij_i_odswiez(p): st.rerun()

# POBRANIE DANYCH (Szybkie, bo z Cache)
df_k, df_z = pobierz_dane_z_chmury()

if not df_k.empty:
    c_sel, c_del = st.columns([3, 1])
    wybor = c_sel.selectbox("Wybierz konkurs:", df_k['Konkurs'].tolist())
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = int(k_info['ID'])

    if c_del.button("🗑️ Usuń konkurs", use_container_width=True):
        if wyslij_i_odswiez({"type": "konkursy", "action": "delete", "id": k_id}):
            wyslij_i_odswiez({"type": "zgloszenia", "action": "delete_all_zgloszenia", "konkurs_id": k_id})
            st.rerun()

    st.divider()

    # METRYKI
    m1, m2, m3, m4 = st.columns(4)
    data_k = sformatuj_date(k_info['Koniec'])
    dni_info = ile_dni_zostalo(k_info['Koniec'])
    m1.metric("📅 Koniec", data_k, delta=dni_info if "dni" in dni_info or "dzień" in dni_info else None)
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    st.info(f"📣 **Wyniki:** {sformatuj_date(k_info.get('Data_Wynikow', 'Brak'))}")

    col_a, col_b = st.columns(2)
    with col_a: st.warning(f"⚖️ **Kryteria:**\n\n{k_info['Kryteria']}")
    with col_b: st.success(f"🔍 **Nr Paragonu:**\n\n{k_info['Nr_Paragonu_Info']}")

    # --- ZGŁOSZENIA ---
    st.divider()
    with st.expander("➕ DODAJ NOWY PARAGON / PRACĘ", expanded=False):
        n_p = st.text_input("Numer paragonu", key="field_np")
        txt = st.text_area("Twoja praca", height=150, key="field_txt")
        
        limit_digits = "".join(filter(str.isdigit, str(k_info['Limit'])))
        max_ch = int(limit_digits) if limit_digits else 2000
        akt_len = len(txt)
        st.caption(f"Znaki: {akt_len} / {max_ch}")
        
        if st.button("💾 Zapisz zgłoszenie"):
            if n_p and txt:
                p_z = {"type": "zgloszenia", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")), 
                       "konkurs_id": k_id, "Nr_Paragonu": n_p, "Tekst": txt, "Data": datetime.now().strftime("%Y-%m-%d %H:%M")}
                if wyslij_i_odswiez(p_z): st.rerun()

    # WYSZUKIWARKA
    szukaj = st.text_input("🔍 Wyszukaj paragon (filtrowanie natychmiastowe):")

    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        if szukaj:
            moje_z = moje_z[moje_z['Nr_Paragonu'].astype(str).str.contains(szukaj, case=False)]

        for _, row in moje_z.iterrows():
            with st.container(border=True):
                z_id = row['ID']
                ct, cb = st.columns([4, 1])
                with ct:
                    st.write(f"🧾 **{row['Nr_Paragonu']}** | {row['Tekst']}")
                    st.caption(f"Dodano: {sformatuj_date(row['Data'])}")
                with cb:
                    if st.button("✏️", key=f"e_{z_id}"): st.session_state[f"ed_{z_id}"] = True
                    if st.button("🗑️", key=f"d_{z_id}"): 
                        if wyslij_i_odswiez({"type": "zgloszenia", "action": "delete", "id": z_id}): st.rerun()

                if st.session_state.get(f"ed_{z_id}", False):
                    with st.form(f"f_{z_id}"):
                        nn = st.text_input("Nr", value=row['Nr_Paragonu'])
                        nt = st.text_area("Tekst", value=row['Tekst'])
                        if st.form_submit_button("Zapisz"):
                            if wyslij_i_odswiez({"type": "zgloszenia", "action": "update", "id": z_id, "Nr_Paragonu": nn, "Tekst": nt}):
                                st.session_state[f"ed_{z_id}"] = False
                                st.rerun()
                        if st.form_submit_button("Anuluj"):
                            st.session_state[f"ed_{z_id}"] = False
                            st.rerun()
else:
    st.info("Baza jest pusta. Dodaj pierwszy konkurs w panelu bocznym.")
