import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF
from calendar import monthrange

# --- AYARLAR ---
st.set_page_config(page_title="A-Gala Kassenbuch", page_icon="💰")

# --- 🚀 BAŞLANGIÇ BAKİYESİ (BURAYI DEĞİŞTİR) ---
# Uygulamayı kullanmaya başladığın andaki ilk ana parayı buraya yaz:
INITIAL_CASH_BALANCE = 1000.00  # Örn: 1000 Euro ile başladın
# ----------------------------------------------

# Supabase Bağlantısı
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("💰 a-gala / KASSENBUCH")

# --- VERİ GİRİŞİ (EINGABE) ---
with st.form("kayit_formu", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        tarih = st.date_input("DATUM", datetime.date.today())
        belge_no = st.text_input("BELEG NR")
    with col_b:
        tur = st.selectbox("VORGANGSTYP", ["EINNAHMEN", "AUSGABEN"])
        tutar = st.number_input("BETRAG (€)", min_value=0.0, step=0.01)
    
    aciklama = st.text_input("BESCHREIBUNG")
    submit = st.form_submit_button("Buchung Speichern")

    if submit:
        data = {"tarih": str(tarih), "belge_no": belge_no, "tur": tur, "aciklama": aciklama, "tutar": tutar}
        supabase.table("muhasebe").insert(data).execute()
        st.success(f"Erfolgreich gespeichert!")

# --- AYLIK RAPORLAMA (MONATSBERICHT) ---
st.divider()
st.subheader("📄 Monatsbericht Erstellen")

today = datetime.date.today()
col_m, col_y = st.columns(2)
selected_month = col_m.selectbox("Monat wählen", range(1, 13), index=today.month - 1)
selected_year = col_y.selectbox("Jahr wählen", [2025, 2026], index=0)

# Ayın aralığını hesapla
start_date = datetime.date(selected_year, selected_month, 1)
last_day = monthrange(selected_year, selected_month)[1]
end_date = datetime.date(selected_year, selected_month, last_day)

if st.button("PDF Bericht Generieren"):
    # 1. ÖNCEKİ DÖNEMDEN DEVREDENİ HESAPLA
    # Veritabanındaki seçilen aydan önceki tüm işlemler
    prev_res = supabase.table("muhasebe").select("tur, tutar").lt("tarih", str(start_date)).execute()
    
    db_prev_balance = 0.0
    for item in prev_res.data:
        if item['tur'] == 'EINNAHMEN':
            db_prev_balance += float(item['tutar'])
        else:
            db_prev_balance -= float(item['tutar'])
    
    # Toplam Devreden = Senin kodun içine yazdığın sabit + Veritabanındaki eski farklar
    total_opening_balance = INITIAL_CASH_BALANCE + db_prev_balance

    # 2. SEÇİLEN AYIN VERİLERİNİ ÇEK
    res = supabase.table("muhasebe").select("*").gte("tarih", str(start_date)).lte("tarih", str(end_date)).order("tarih").execute()
    
    if res.data:
        df_rep = pd.DataFrame(res.data)
        
        # PDF Hazırlığı
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, "KASSENBERICHT", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.cell(190, 10, f"Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}", ln=True, align="C")
        pdf.ln(10)

        # ÜBERTRAG (DEVREDEN) SATIRI
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(130, 10, "Vortrag aus dem Vormonat (Devreden Bakiye)", 1, 0, "L", True)
        pdf.cell(60, 10, f"{total_opening_balance:.2f} EUR", 1, 1, "R", True)
        pdf.ln(2)

        # TABLO BAŞLIKLARI
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(25, 10, "Datum", 1, 0, "C", True)
        pdf.cell(30, 10, "Beleg", 1, 0, "C", True)
        pdf.cell(75, 10, "Beschreibung", 1, 0, "C", True)
        pdf.cell(30, 10, "Einnahme", 1, 0, "C", True)
        pdf.cell(30, 10, "Ausgabe", 1, 0, "C", True)
        pdf.ln()

        # VERİLER
        pdf.set_font("Arial", "", 9)
        m_in, m_out = 0.0, 0.0
        for _, row in df_rep.iterrows():
            pdf.cell(25, 8, str(row['tarih']), 1)
            pdf.cell(30, 8, str(row['belge_no']), 1)
            pdf.cell(75, 8, str(row['aciklama'])[:40], 1)
            
            val = float(row['tutar'])
            if row['tur'] == 'EINNAHMEN':
                pdf.cell(30, 8, f"{val:.2f}", 1, 0, "R")
                pdf.cell(30, 8, "-", 1, 0, "R")
                m_in += val
            else:
                pdf.cell(30, 8, "-", 1, 0, "R")
                pdf.cell(30, 8, f"{val:.2f}", 1, 0, "R")
                m_out += val
            pdf.ln()

        # ÖZET VE KAPANIŞ (ENDBESTAND)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        closing_balance = total_opening_balance + m_in - m_out

        pdf.cell(130, 8, "Summe Einnahmen (Bu Ay Toplam Gelir):", 0)
        pdf.cell(60, 8, f"+ {m_in:.2f} EUR", 0, 1, "R")
        pdf.cell(130, 8, "Summe Ausgaben (Bu Ay Toplam Gider):", 0)
        pdf.cell(60, 8, f"- {m_out:.2f} EUR", 0, 1, "R")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.set_font("Arial", "B", 11)
        pdf.cell(130, 10, "Endbestand (Gelecek Aya Devreden):", 0)
        pdf.cell(60, 10, f"{closing_balance:.2f} EUR", 0, 1, "R")

        # İndirme Butonu
        pdf_output = bytes(pdf.output())
        st.download_button(label="📥 Bericht herunterladen", data=pdf_output, 
                           file_name=f"Kassenbericht_{selected_month}_{selected_year}.pdf", mime="application/pdf")
    else:
        st.warning("Keine Daten gefunden.")
