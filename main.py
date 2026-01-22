import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA ---
# TUTAJ WKLEJ SWÓJ LINK Z WDROŻENIA APPS SCRIPT (Web App URL)
URL_API = "TUTAJ_WKLEJ_SWOJ_LINK_Z_APPS_SCRIPT"

st.set_page_config(page_title="Konkursownik PRO Cloud", layout="wide", page_icon="🏆")

# --- FUNKCJE KOMUNIKACJI Z ARKUSZEM ---
def pobierz_wszystko():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        # Tworzenie DataFrame z danych (pierwszy wiersz to nagłówki)
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

def wyslij_do_bazy(payload):
    try:
        requests.post(URL_API, data=json.dumps(payload))
    except Exception as e:
        st.error(f"Błąd wysyłania: {e}")

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🏆 Ekspercki Manager Konkursowy")
st.caption("Zsynchronizowano z Twoim Arkuszem Google")

# BOCZNY PANEL - IMPORT NOWEGO KONKURSU
with st.sidebar:
    st.header("📥 Nowy Konkurs")
    st.write("Wklej tutaj analizę od Gemini:")
    json_input = st.text_area("JSON Input", height=200, label_visibility="collapsed")
    
    if st.button("🚀 Dodaj Konkurs do Bazy"):
        if json_input:
            try:
                # CZYSZCZENIE JSON (usuwanie znaczników ```json i innych śmieci)
                clean_json = json_input.strip()
                if clean_json.startswith("```"):
                    clean_json = clean_json.replace("```json", "", 1).replace("```", "", 1)
                clean_json = clean_json.strip()

                d = json.loads(clean_json)
                
                # Budowanie paczki danych
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
                    "Paragon": d.get('Paragon', 'Nie')
                }
                wyslij_do_bazy(payload)
                st.success("Konkurs dodany pomyślnie!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd formatu JSON! Sprawdź czy skopiowałeś wszystko. ({e})")
        else:
            st.warning("Pole jest puste!")

# POBIERANIE DANYCH Z CHMURY
df_k, df_z = pobierz_wszystko()

if not df_k.empty:
    # WYBÓR KONKURSU Z LISTY
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        lista_k = df_k['Konkurs'].tolist()
        wybor = st.selectbox("Wybierz konkurs, którym chcesz zarządzać:", lista_k)
    
    # Pobranie szczegółów wybranego konkursu
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = k_info['ID']

    with col_del:
        st.write("") # Odstęp dla wyrównania
        if st.button("🗑️ Usuń ten konkurs", use_container_width=True):
            wyslij_do_bazy({"type": "konkursy", "action": "delete", "id": k_id})
            wyslij_do_bazy({"type": "zgloszenia", "action": "delete", "konkurs_id": k_id})
            st.warning(f"Usunięto: {wybor}")
            st.rerun()

    st.divider()

    # WYŚWIETLANIE SZCZEGÓŁÓW (DATY, KRYTERIA, PARAGON)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📅 Data końca", k_info['Koniec'])
    with c2:
        st.metric("📏 Limit znaków", k_info['Limit'])
    with c3:
        st.metric("🧾 Paragon", k_info['Paragon'])

    col_info_1, col_info_2 = st.columns(2)
    with col_info_1:
        st.warning(f"⚖️ **Co ocenia Jury:**\n\n{k_info['Kryteria']}")
    with col_info_2:
        st.success(f"🔍 **Instrukcja numeru paragonu:**\n\n{k_info['Nr_Paragonu_Info']}")
    
    with st.expander("📖 Zobacz pełną treść zadania z regulaminu"):
        st.write(k_info['Zadanie'])

    # SEKCJA ZGŁOSZEŃ (WIELE PARAGONÓW POD JEDEN KONKURS)
    st.divider()
    st.subheader(f"🎫 Twoje zgłoszenia do konkursu: {wybor}")

    with st.expander("➕ Dodaj nowe zgłoszenie (nowy paragon)", expanded=False):
        nr_p = st.text_input("Numer paragonu (zgodnie z instrukcją powyżej)")
        txt_zgl = st.text_area("Twoja praca konkursowa", height=150)
        
        # Logika licznika znaków
        limit_raw = str(k_info['Limit'])
        limit_digits = "".join(filter(str.isdigit, limit_raw))
        max_ch = int(limit_digits) if limit_digits else 2000
        
        dlugosc = len(txt_zgl)
        if dlugosc > max_ch:
            st.error(f"Liczba znaków: {dlugosc} / {max_ch} (PRZEKROCZONO!)")
        else:
            st.caption(f"Liczba znaków: {dlugosc} / {max_ch}")
        
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
                wyslij_do_bazy(payload_z)
                st.success("Zgłoszenie zapisane w chmurze!")
                st.rerun()
            else:
                st.warning("Wypełnij numer paragonu i tekst pracy.")

    # LISTA ZAPISANYCH PARAGONÓW I PRAC
    if not df_z.empty:
        # Filtrowanie zgłoszeń tylko dla tego konkursu (porównujemy jako stringi dla bezpieczeństwa)
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        
        if not moje_z.empty:
            for _, row in moje_z.iterrows():
                with st.container(border=True):
                    st.write(f"🧾 **Paragon:** {row['Nr_Paragonu']}")
                    st.write(f"💬 {row['Tekst']}")
                    st.caption(f"Dodano: {row['Data']}")
        else:
            st.info("Nie dodałeś jeszcze żadnego paragonu do tego konkursu.")
else:
    st.info("Twoja baza jest pusta. Wklej analizę regulaminu w panelu bocznym, aby zacząć.")
