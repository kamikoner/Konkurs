import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="Konkursownik Cloud", layout="wide")

# --- POŁĄCZENIE Z ARKUSZAMI GOOGLE ---
# W chmurze skonfigurujemy to w sekcji "Secrets"
conn = st.connection("gsheets", type=GSheetsConnection)

def wczytaj_konkursy():
    try:
        return conn.read(worksheet="konkursy")
    except:
        return pd.DataFrame(columns=["ID", "Konkurs", "Koniec", "Zadanie", "Limit", "Kryteria", "Nr_Paragonu_Info", "Paragon"])

def wczytaj_zgloszenia():
    try:
        return conn.read(worksheet="zgloszenia")
    except:
        return pd.DataFrame(columns=["Konkurs_ID", "Nr_Paragonu", "Tekst", "Data"])

# --- INTERFEJS ---
st.title("🏆 Mobilny Manager Konkursowy")

# PASEK BOCZNY - IMPORT
with st.sidebar:
    st.header("📥 Nowy Konkurs")
    import_json = st.text_area("Wklej JSON od Gemini:", height=150)
    if st.button("Dodaj Konkurs"):
        try:
            d = json.loads(import_json)
            df_k = wczytaj_konkursy()
            nowe_id = int(datetime.now().strftime("%Y%m%d%H%M%S"))
            nowy_row = pd.DataFrame([{
                "ID": nowe_id, "Konkurs": d['Konkurs'], "Koniec": d['Koniec'],
                "Zadanie": d['Pelne_Zadanie'], "Limit": d['Limit'],
                "Kryteria": d.get('Kryteria', ''), "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                "Paragon": d['Paragon']
            }])
            df_final = pd.concat([df_k, nowy_row], ignore_index=True)
            conn.update(worksheet="konkursy", data=df_final)
            st.success("Dodano do chmury!")
            st.rerun()
        except Exception as e: st.error(f"Błąd: {e}")

# PANEL GŁÓWNY
df_k = wczytaj_konkursy()
df_z = wczytaj_zgloszenia()

if not df_k.empty:
    wybor = st.selectbox("Wybierz konkurs:", df_k['Konkurs'].tolist())
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📅 Koniec: {k_info['Koniec']}\n\n🧾 Nr paragonu: {k_info['Nr_Paragonu_Info']}")
    with col2:
        st.warning(f"⚖️ Kryteria: {k_info['Kryteria']}")

    st.divider()
    # Dodawanie zgłoszenia
    with st.expander("➕ Dodaj zgłoszenie / paragon"):
        nr_p = st.text_input("Nr paragonu")
        tekst = st.text_area("Twoja praca")
        if st.button("Zapisz w Arkuszu"):
            nowe_z = pd.DataFrame([{"Konkurs_ID": k_info['ID'], "Nr_Paragonu": nr_p, "Tekst": tekst, "Data": datetime.now().strftime("%Y-%m-%d %H:%M")}])
            df_z_final = pd.concat([df_z, nowe_z], ignore_index=True)
            conn.update(worksheet="zgloszenia", data=df_z_final)
            st.success("Zapisano!")
            st.rerun()

    # Wyświetlanie zgłoszeń
    st.subheader("Twoje paragony")
    moje_zgl = df_z[df_z['Konkurs_ID'] == k_info['ID']]
    st.table(moje_zgl[["Nr_Paragonu", "Tekst", "Data"]])