import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re
import base64

# --- KONFIGURACJA ---
# TUTAJ WKLEJ SWÓJ LINK Z WDROŻENIA APPS SCRIPT
URL_API = "https://script.google.com/macros/s/AKfycbypVdCzKAyg7X6o0ZPNQPYbt9fB2NUAbxwIjQZruGghPGEpdcbamDpAhGCso0g3xp7Q/exec"

st.set_page_config(page_title="Konkursownik", layout="wide", page_icon="🏆")

# Inicjalizacja wersji formularza do czyszczenia pól
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# --- 1. FUNKCJE POMOCNICZE ---

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
        with st.spinner("Synchronizacja z chmurą..."):
            requests.post(URL_API, data=json.dumps(payload), timeout=30)
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return False

# --- 2. INTERFEJS UŻYTKOWNIKA ---

st.title("🏆 Konkursownik Mateusza")

with st.sidebar:
    if st.button("🔄 Synchronizuj dane", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.header("📥 Import z Gemini")
    json_in = st.text_area("Wklej JSON:", height=150)
    if st.button("🚀 Dodaj Konkurs", use_container_width=True):
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
    # WYBÓR KONKURSU
    c_sel, c_del = st.columns([3, 1])
    wybor = c_sel.selectbox("Wybierz aktywny konkurs:", df_k['Konkurs'].tolist())
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = int(k_info['ID'])

    if c_del.button("🗑️ Usuń konkurs", use_container_width=True):
        if wyslij_i_odswiez({"type": "konkursy", "action": "delete", "id": k_id}):
            wyslij_i_odswiez({"type": "zgloszenia", "action": "delete_all_zgloszenia", "konkurs_id": k_id})
            st.rerun()

    st.divider()
    
    # SEKCJA 1: KLUCZOWE METRYKI (AGENCJA I RESZTA)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Koniec", sformatuj_date(k_info['Koniec']), delta=ile_dni_zostalo(k_info['Koniec']))
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    st.info(f"📣 **Kiedy i gdzie wyniki:** {sformatuj_date(k_info.get('Data_Wynikow', 'Brak'))}")

    # SEKCJA 2: KRYTERIA I INSTRUKCJA PARAGONU
    col_kryst, col_para = st.columns(2)
    with col_kryst:
        st.warning(f"⚖️ **Kryteria Jury:**\n\n{k_info.get('Kryteria', 'Brak danych')}")
    with col_para:
        st.success(f"🔍 **Instrukcja numeru paragonu:**\n\n{k_info.get('Nr_Paragonu_Info', 'Brak danych')}")
    
    with st.expander("📝 Pełna treść zadania konkursowego"):
        st.write(k_info.get('Zadanie', 'Brak treści'))

    # SEKCJA 3: DODAWANIE ZGŁOSZENIA
    st.divider()
    st.subheader("🎫 Dodaj nowe zgłoszenie")
    with st.expander("➕ FORMULARZ ZGŁOSZENIOWY", expanded=True):
        n_p = st.text_input("Numer paragonu / dowodu zakupu", key=f"np_{st.session_state.form_version}")
        txt = st.text_area("Twoja praca konkursowa", height=150, key=f"txt_{st.session_state.form_version}")
        
        # Licznik znaków live
        limit_digits = "".join(filter(str.isdigit, str(k_info['Limit'])))
        max_ch = int(limit_digits) if limit_digits else 2000
        dlugosc = len(txt)
        if dlugosc > max_ch: st.error(f"📏 Znaki: {dlugosc} / {max_ch} (PRZEKROCZONO!)")
        else: st.caption(f"📏 Znaki: {dlugosc} / {max_ch}")

        # Upload zdjęcia
        foto = st.file_uploader("📸 Dodaj zdjęcie paragonu (opcjonalnie)", type=['jpg', 'jpeg', 'png'], key=f"file_{st.session_state.form_version}")

        if st.button("💾 Zapisz zgłoszenie i zdjęcie", use_container_width=True):
            if n_p and txt:
                file_data, file_name, mime_type = "", "", ""
                if foto:
                    file_data = base64.b64encode(foto.read()).decode()
                    file_name = foto.name
                    mime_type = foto.type

                payload = {
                    "type": "zgloszenia", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                    "konkurs_id": k_id, "Nr_Paragonu": n_p, "Tekst": txt,
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "fileData": file_data, "fileName": file_name, "mimeType": mime_type
                }
                if wyslij_i_odswiez(payload):
                    st.session_state.form_version += 1
                    st.rerun()
            else:
                st.warning("Uzupełnij numer paragonu i tekst pracy.")

    # SEKCJA 4: LISTA TWOICH ZGŁOSZEŃ
    st.divider()
    szukaj = st.text_input("🔍 Szukaj po numerze paragonu:", placeholder="Wpisz fragment numeru...")

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
                
                # Przycisk zdjęcia
                foto_url = row.get('Zdjecie_URL', '')
                if foto_url and foto_url.startswith("http"):
                    st.link_button("📂 Zobacz zdjęcie paragonu", foto_url)
                
                st.caption(f"Dodano: {sformatuj_date(row['Data'])}")
                
                c1, c2, c3 = st.columns([1,1,2])
                if c1.button("✏️", key=f"e_{z_id}"): st.session_state[f"ed_{z_id}"] = True
                if c2.button("🗑️", key=f"d_{z_id}"): 
                    if wyslij_i_odswiez({"type": "zgloszenia", "action": "delete", "id": z_id}): st.rerun()
                
                label = "🥈 Odznacz wygraną" if is_winner else "🏆 ZAZNACZ WYGRANĄ!"
                st_status = "Nie" if is_winner else "Tak"
                if c3.button(label, key=f"w_{z_id}"):
                    if wyslij_i_odswiez({"type": "zgloszenia", "action": "update_status", "id": z_id, "status": st_status}):
                        st.rerun()

                # Edycja
                if st.session_state.get(f"ed_{z_id}", False):
                    with st.form(f"ed_form_{z_id}"):
                        nn = st.text_input("Popraw nr", value=row['Nr_Paragonu'])
                        nt = st.text_area("Popraw tekst", value=row['Tekst'])
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
