import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA ---
URL_API = "https://script.google.com/macros/s/AKfycbwWKkt_CCd8dIU9EOwonm7wr62mBd8y1bwGfLjlHVZrkBn2sZbF5GewnxCfoDHJZiP9/exec"

st.set_page_config(page_title="Konkursownik v8", layout="wide", page_icon="🏆")

def pobierz_wszystko():
    try:
        r = requests.get(URL_API)
        dane = r.json()
        df_k = pd.DataFrame(dane['konkursy'][1:], columns=dane['konkursy'][0]) if len(dane['konkursy']) > 1 else pd.DataFrame()
        df_z = pd.DataFrame(dane['zgloszenia'][1:], columns=dane['zgloszenia'][0]) if len(dane['zgloszenia']) > 1 else pd.DataFrame()
        return df_k, df_z
    except: return pd.DataFrame(), pd.DataFrame()

def wyslij(payload):
    try: requests.post(URL_API, data=json.dumps(payload)); return True
    except: return False

# --- INTERFEJS ---
st.title("🏆 Ekspercki Manager Konkursowy v8")

with st.sidebar:
    st.header("📥 Import z Gemini")
    json_in = st.text_area("Wklej JSON:", height=200)
    if st.button("🚀 Dodaj Konkurs", use_container_width=True):
        match = re.search(r'\{.*\}', json_in, re.DOTALL)
        if match:
            d = json.loads(match.group())
            p = {"type": "konkursy", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
                 "Konkurs": d.get('Konkurs', ''), "Koniec": d.get('Koniec', ''), "Zadanie": d.get('Pelne_Zadanie', ''),
                 "Limit": d.get('Limit', ''), "Kryteria": d.get('Kryteria', ''), "Nr_Paragonu_Info": d.get('Nr_Paragonu_Info', ''),
                 "Paragon": d.get('Paragon', ''), "Agencja": d.get('Agencja', ''), "Data_Wynikow": d.get('Data_Wynikow', '')}
            if wyslij(p): st.success("Dodano!"); st.rerun()

df_k, df_z = pobierz_wszystko()

if not df_k.empty:
    c_sel, c_del = st.columns([3, 1])
    wybor = c_sel.selectbox("Wybierz konkurs:", df_k['Konkurs'].tolist())
    k_info = df_k[df_k['Konkurs'] == wybor].iloc[0]
    k_id = int(k_info['ID'])

    if c_del.button("🗑️ Usuń CAŁY konkurs", use_container_width=True):
        wyslij({"type": "konkursy", "action": "delete", "id": k_id})
        wyslij({"type": "zgloszenia", "action": "delete_all_zgloszenia", "konkurs_id": k_id})
        st.rerun()

    st.divider()

    # --- PRZYWRÓCONE SZCZEGÓŁY KONKURSU ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Koniec", k_info['Koniec'])
    m2.metric("🏢 Agencja", k_info.get('Agencja', 'Brak'))
    m3.metric("📏 Limit", k_info['Limit'])
    m4.metric("🧾 Paragon", k_info['Paragon'])

    st.info(f"📣 **Wyniki:** {k_info.get('Data_Wynikow', 'Brak danych')}")

    col_a, col_b = st.columns(2)
    with col_a: st.warning(f"⚖️ **Kryteria Jury:**\n\n{k_info['Kryteria']}")
    with col_b: st.success(f"🔍 **Instrukcja Paragonu:**\n\n{k_info['Nr_Paragonu_Info']}")
    
    with st.expander("📝 Pełna treść zadania"):
        st.write(k_info['Zadanie'])

    # --- ZGŁOSZENIA ---
    st.divider()
    st.subheader("🎫 Zarządzanie zgłoszeniami")
    
    with st.expander("➕ Dodaj nowe zgłoszenie"):
        n_p = st.text_input("Nr paragonu")
        txt = st.text_area("Praca")
        if st.button("Zapisz w chmurze"):
            if wyslij({"type": "zgloszenia", "action": "add", "id": int(datetime.now().strftime("%Y%m%d%H%M%S")), 
                       "konkurs_id": k_id, "Nr_Paragonu": n_p, "Tekst": txt, "Data": datetime.now().strftime("%Y-%m-%d %H:%M")}):
                st.rerun()

    szukaj = st.text_input("🔍 Wyszukiwarka paragonów:", placeholder="Wpisz numer...")

    if not df_z.empty:
        moje_z = df_z[df_z['Konkurs_ID'].astype(str) == str(k_id)]
        if szukaj:
            moje_z = moje_z[moje_z['Nr_Paragonu'].astype(str).str.contains(szukaj, case=False)]

        for _, row in moje_z.iterrows():
            with st.container(border=True):
                z_id = row['ID']
                col_txt, col_btns = st.columns([4, 1])
                
                with col_txt:
                    st.write(f"🧾 **Paragon:** {row['Nr_Paragonu']}")
                    st.write(f"💬 {row['Tekst']}")
                    st.caption(f"Data dodania: {row['Data']}")
                
                with col_btns:
                    if st.button("✏️ Edytuj", key=f"ed_{z_id}", use_container_width=True):
                        st.session_state[f"edit_mode_{z_id}"] = True
                    
                    if st.button("🗑️ Usuń", key=f"del_z_{z_id}", use_container_width=True):
                        wyslij({"type": "zgloszenia", "action": "delete", "id": z_id})
                        st.rerun()

                # Formularz edycji
                if st.session_state.get(f"edit_mode_{z_id}", False):
                    with st.form(key=f"form_{z_id}"):
                        nowy_nr = st.text_input("Popraw nr", value=row['Nr_Paragonu'])
                        nowy_txt = st.text_area("Popraw tekst", value=row['Tekst'])
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("Zapisz"):
                            wyslij({"type": "zgloszenia", "action": "update", "id": z_id, "Nr_Paragonu": nowy_nr, "Tekst": nowy_txt})
                            st.session_state[f"edit_mode_{z_id}"] = False
                            st.rerun()
                        if c2.form_submit_button("Anuluj"):
                            st.session_state[f"edit_mode_{z_id}"] = False
                            st.rerun()
else:
    st.info("Baza pusta.")
