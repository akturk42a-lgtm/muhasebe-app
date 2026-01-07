import streamlit as st
from supabase import create_client
import datetime

# Sayfa ayarları
st.set_page_config(page_title="Aktürk Muhasebe", page_icon="📊")

# Supabase bağlantı bilgileri (Bunları Streamlit panelinden gireceğiz)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📊 İşletme Gelir-Gider Takibi")

# --- FORM BÖLÜMÜ ---
with st.form("kayit_formu", clear_on_submit=True):
    tarih = st.date_input("Tarih", datetime.date.today())
    belge_no = st.text_input("Belge / Fatura Numarası")
    tur = st.selectbox("İşlem Türü", ["Gelir", "Gider"])
    aciklama = st.text_input("Açıklama (Örn: Kira, Mal Alımı)")
    tutar = st.number_input("Tutar (€)", min_value=0.0, step=0.01)
    
    submit = st.form_submit_button("Veritabanına Kaydet")

    if submit:
        data = {
            "tarih": str(tarih),
            "belge_no": belge_no,
            "tur": tur,
            "aciklama": aciklama,
            "tutar": tutar
        }
        supabase.table("muhasebe").insert(data).execute()
        st.success(f"Başarıyla kaydedildi: {tutar} €")

# --- LİSTELEME BÖLÜMÜ ---
st.divider()
st.subheader("Son Kayıtlar")
response = supabase.table("muhasebe").select("*").order("tarih", desc=True).limit(10).execute()
if response.data:
    st.table(response.data)
