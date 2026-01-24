import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA ---
URL_API = "https://script.google.com/macros/s/AKfycbxsIurMBjUxGPDn7xSYmCSAF3qWChKrg2uId13fwYpDyn7dZSV0Fo4sjJ_wIcpgmqMA/exec"

st.set_page_config(page_title="Konkursownik", layout="wide", page_icon="🏆")

# Inicjalizacja wersji formularza (do czyszczenia pól)
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# --- FUNKCJE POMOCNICZE ---
def sformatuj_date(data_str):
    if not data_str or data_str == 'Brak': return "Brak"
    try: return pd.to_datetime(data_str).strftime('%d.%m.%Y o %H:%M')
    except: return data_str

def ile_dni_zostalo(data_konca_str):
    try:
        data_konca = pd.to_datetime(data_konca_str).date()
        dzis = datetime.now().date()
        roznica = (data_konca - dzis).days
        if roznica < 0: return " (Zakończony)"
        elif roznica == 0: return " (TO DZISIAJ!)"
        else: return f" (Zostało {roznica} dni)"
    except: return ""

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
        with st.spinner("Synchronizacja..."):
            requests.post(URL_API, data=json.dumps(payload), timeout=10)
            st.cache_data.clear()
            return True
    except: return False

# --- INTERFEJS ---
st.title("🏆 Konkursownik Mateusza")

with st.sidebar:
    if st.button("🔄 Synchronizuj dane", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.header("📥 Import z Gemini")
    json_in = st.text_area("Wklej JSON:", height=150)
    if st.button("🚀 Dodaj Konkurs"):
        match = re.search(r'\{.*\}', json_in, re.DOTALL)
        if match:
            d = json.loads(match.group())
            p = {"type": "konkursy", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                 "Konkurs": d.get('Konkurs', ''), "Koniec": d.get('Koniec', ''), "Zadanie": d.get('Pelne_Zadanie', ''),
                 "Limit": d.get('Limit', ''), "Kryteria": d.get('Kryteria', ''), "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                 "Paragon": d.get('Paragon', ''), "Agencja": d.get('Agencja', ''), "Data_Wynikow": d.get('Data_Wynikow', '')}
            if wyslij_i_odswiez(p): st.rerun()

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
    m1.metric("📅 Koniec", sformatuj_date(k_info['Koniec']), delta=ile_dni_zostalo(k_info['Koniec']))
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    st.info(f"📣 **Wyniki:** {sformatuj_date(k_info.get('Data_Wynikow', 'Brak'))}")

    # --- NOWA SEKCJA DODAWANIA Z LICZNIKIEM ---
    st.subheader("🎫 Dodaj nowe zgłoszenie")
    
    # Wyciągamy cyfry z limitu (np. "300 znaków" -> 300)
    limit_str = str(k_info['Limit'])
    limit_digits = "".join(filter(str.isdigit, limit_str))
    max_ch = int(limit_digits) if limit_digits else 2000

    # Pola wejściowe z dynamicznym kluczem (do czyszczenia)
    n_p = st.text_input("Numer paragonu", key=f"np_{st.session_state.form_version}")
    txt = st.text_area("Twoja praca", height=150, key=f"txt_{st.session_state.form_version}")
    
    # LICZNIK ZNAKÓW (LIVE)
    dlugosc = len(txt)
    if dlugosc > max_ch:
        st.error(f"📏 Znaki: {dlugosc} / {max_ch} (PRZEKROCZONO!)")
    else:
        st.success(f"📏 Znaki: {dlugosc} / {max_ch}")

    if st.button("💾 Zapisz zgłoszenie w chmurze", use_container_width=True):
        if n_p and txt:
            p_z = {"type": "zgloszenia", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")), 
                   "konkurs_id": k_id, "Nr_Paragonu": n_p, "Tekst": txt, "Data": datetime.now().strftime("%Y-%m-%d %H:%M")}
            if wyslij_i_odswiez(p_z):
                # Zmieniamy wersję klucza -> pola stają się puste
                st.session_state.form_version += 1
                st.rerun()
        else:
            st.warning("Uzupełnij oba pola!")

    # --- LISTA ZGŁOSZEŃ ---
    st.divider()
    szukaj = st.text_input("🔍 Szukaj paragonu:")

    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        if szukaj: moje_z = moje_z[moje_z['Nr_Paragonu'].astype(str).str.contains(szukaj, case=False)]

        for _, row in moje_z.iterrows():
            z_id = row['ID']
            is_winner = str(row.get('Wygrana', 'Nie')) == 'Tak'
            
            with st.container(border=True):
                if is_winner:
                    st.success(f"🏆 **WYGRANA!** | Paragon: {row['Nr_Paragonu']}")
                else:
                    st.write(f"🧾 **Paragon: {row['Nr_Paragonu']}**")
                
                st.write(f"💬 {row['Tekst']}")
                st.caption(f"Dodano: {sformatuj_date(row['Data'])}")
                
                c1, c2, c3 = st.columns([1,1,2])
                if c1.button("✏️", key=f"e_{z_id}"): st.session_state[f"ed_{z_id}"] = True
                if c2.button("🗑️", key=f"d_{z_id}"): 
                    if wyslij_i_odswiez({"type": "zgloszenia", "action": "delete", "id": z_id}): st.rerun()
                
                label = "🥈 Odznacz wygraną" if is_winner else "🏆 ZAZNACZ WYGRANĄ!"
                st_val = "Nie" if is_winner else "Tak"
                if c3.button(label, key=f"w_{z_id}"):
                    if wyslij_i_odswiez({"type": "zgloszenia", "action": "update_status", "id": z_id, "status": st_val}):
                        st.rerun()

                if st.session_state.get(f"ed_{z_id}", False):
                    with st.form(f"edit_{z_id}"):
                        nn = st.text_input("Nr paragonu", value=row['Nr_Paragonu'])
                        nt = st.text_area("Tekst pracy", value=row['Tekst'])
                        c_ed1, c_ed2 = st.columns(2)
                        if c_ed1.form_submit_button("Zapisz zmiany"):
                            if wyslij_i_odswiez({"type": "zgloszenia", "action": "update", "id": z_id, "Nr_Paragonu": nn, "Tekst": nt}):
                                st.session_state[f"ed_{z_id}"] = False
                                st.rerun()
                        if c_ed2.form_submit_button("Anuluj"):
                            st.session_state[f"ed_{z_id}"] = False
                            st.rerun()
else:
    st.info("Baza konkursów jest pusta.")
