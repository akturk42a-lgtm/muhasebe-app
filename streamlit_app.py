import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF

# Sayfa Ayarları
st.set_page_config(page_title="Aktürk Buchhaltung", page_icon="📊")

# Supabase Bağlantısı
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("a-gala Einnahmen & Ausgaben")

# --- VERİ GİRİŞİ (ALMANCA) ---
with st.form("kayit_formu", clear_on_submit=True):
    tarih = st.date_input("DATUM", datetime.date.today())
    belge_no = st.text_input("BELEG")
    tur = st.selectbox("Vorgangstyp", ["EINNAHMEN", "AUSGABEN"])
    aciklama = st.text_input("GESCHÄFTSVORGANG KASSENBESTAND")
    tutar = st.number_input("Betrag (€)", min_value=0.0, step=0.01)
    submit = st.form_submit_button("Speichern")

    if submit:
        data = {"tarih": str(tarih), "belge_no": belge_no, "tur": tur, "aciklama": aciklama, "tutar": tutar}
        supabase.table("muhasebe").insert(data).execute()
        st.success(f"Gespeichert: {tutar} €")

# --- RAPORLAMA VE PDF BÖLÜMÜ ---
st.divider()
st.subheader("📄 PDF Bericht Erstellen")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Startdatum", datetime.date.today() - datetime.timedelta(days=30))
with col2:
    end_date = st.date_input("Enddatum", datetime.date.today())

if st.button("PDF Generieren"):
    # Verileri seçilen tarihlere göre filtreleyerek çekiyoruz
    res = supabase.table("muhasebe").select("*").gte("tarih", str(start_date)).lte("tarih", str(end_date)).order("tarih").execute()
    
    if res.data:
        df_rep = pd.DataFrame(res.data)
        
        # PDF Oluşturma Ayarları
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, "Buchhaltungsbericht", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(190, 10, f"Zeitraum: {start_date} bis {end_date}", ln=True, align="C")
        pdf.ln(10)

        # Tablo Başlıkları
        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 10, "Datum", 1)
        pdf.cell(40, 10, "Beleg-Nr", 1)
        pdf.cell(30, 10, "Typ", 1)
        pdf.cell(60, 10, "Beschreibung", 1)
        pdf.cell(30, 10, "Betrag", 1)
        pdf.ln()

        # Tablo Verileri
        pdf.set_font("Arial", "", 10)
        for index, row in df_rep.iterrows():
            pdf.cell(30, 10, str(row['tarih']), 1)
            pdf.cell(40, 10, str(row['belge_no']), 1)
            pdf.cell(30, 10, str(row['tur']), 1)
            pdf.cell(60, 10, str(row['aciklama'])[:25], 1) # Uzun açıklamaları keser
            pdf.cell(30, 10, f"{row['tutar']} Euro", 1)
            pdf.ln()

        # PDF'i indirilebilir yapma
        pdf_output = bytes(pdf.output())

        st.download_button(label="📥 PDF Herunterladen", data=pdf_output, file_name=f"Bericht_{start_date}_{end_date}.pdf", mime="application/pdf")
    else:
        st.warning("Keine Daten für diesen Zeitraum gefunden.")

# --- SON KAYITLAR LİSTESİ ---
st.divider()
st.subheader("Letzte Buchungen")
response = supabase.table("muhasebe").select("*").order("tarih", desc=True).limit(10).execute()
if response.data:
    df_list = pd.DataFrame(response.data)
    df_list['tarih'] = pd.to_datetime(df_list['tarih']).dt.strftime('%d.%m.%Y')
    st.dataframe(df_list[['tarih', 'belge_no', 'tur', 'aciklama', 'tutar']], use_container_width=True)

