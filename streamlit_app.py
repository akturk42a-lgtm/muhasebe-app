import streamlit as st
from supabase import create_client
import datetime
import pandas as pd

# Sayfa Ayarları (Almanca Başlık)
st.set_page_config(page_title="Aktürk Buchhaltung", page_icon="📊")

# Supabase Bağlantısı
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📊 Einnahmen & Ausgaben")

# --- FORM BÖLÜMÜ (ALMANCA) ---
with st.form("kayit_formu", clear_on_submit=True):
    # Tarih formatını Avrupa stiline uygun yapıyoruz
    tarih = st.date_input("Datum", datetime.date.today())
    belge_no = st.text_input("Belegnummer / Rechnungsnummer")
    tur = st.selectbox("Vorgangstyp", ["Einnahme", "Ausgabe"])
    aciklama = st.text_input("Beschreibung (z.B. Miete, Wareneinkauf)")
    tutar = st.number_input("Betrag (€)", min_value=0.0, step=0.01)
    
    submit = st.form_submit_button("Speichern")

    if submit:
        data = {
            "tarih": str(tarih),
            "belge_no": belge_no,
            "tur": tur,
            "aciklama": aciklama,
            "tutar": tutar
        }
        supabase.table("muhasebe").insert(data).execute()
        st.success(f"Erfolgreich gespeichert: {tutar} €")

# --- LİSTELEME VE FORMATLAMA ---
st.divider()
st.subheader("Letzte Buchungen")

response = supabase.table("muhasebe").select("*").order("tarih", desc=True).limit(20).execute()

if response.data:
    # Verileri daha iyi formatlamak için Pandas kullanıyoruz
    df = pd.DataFrame(response.data)
    
    # Karmaşık tarihleri temizleme (Sadece Gün.Ay.Yıl Saat:Dakika)
    df['olusturma_tarihi'] = pd.to_datetime(df['olusturma_tarihi']).dt.strftime('%d.%m.%Y %H:%M')
    df['tarih'] = pd.to_datetime(df['tarih']).dt.strftime('%d.%m.%Y')
    
    # Sütun isimlerini Almanca yapma
    df = df.rename(columns={
        "tarih": "Datum",
        "belge_no": "Beleg-Nr",
        "tur": "Typ",
        "aciklama": "Beschreibung",
        "tutar": "Betrag (€)",
        "olusturma_tarihi": "Erstellungsdatum"
    })
    
    # ID sütununu gizleyip listeleme
    st.dataframe(df.drop(columns=['id']), use_container_width=True)
else:
    st.info("Noch keine Daten vorhanden.")

