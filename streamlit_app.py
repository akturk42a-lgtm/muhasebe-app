import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF
from calendar import monthrange

# --- AYARLAR ---
st.set_page_config(page_title="A-Gala Kassenbuch", page_icon="💰")

# --- 🚀 BAŞLANGIÇ BAKİYESİ (BURAYI DEĞİŞTİR) ---
INITIAL_CASH_BALANCE = 1000.00 
# ----------------------------------------------

# Almanca Ay İsimleri
GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}

# Supabase Bağlantısı
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("💰 a-gala / KASSENBUCH")

# --- VERİ GİRİŞİ (EINGABE) ---
with st.form("kayit_formu", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        # Tarih girişi (Kullanıcı arayüzünde takvim olarak açılır)
        tarih = st.date_input("DATUM", datetime.date.today())
        belge_no = st.text_input("BELEG NR")
    with col_b:
        # Varsayılan olarak AUSGABEN seçili (İlk sıraya alındı)
        tur = st.selectbox("VORGANGSTYP", ["AUSGABEN", "EINNAHMEN"])
        tutar = st.number_input("BETRAG (€)", min_value=0.0, step=0.01)
    
    aciklama = st.text_input("BESCHREIBUNG")
    submit = st.form_submit_button("Buchung Speichern")

    if submit:
        data = {"tarih": str(tarih), "belge_no": belge_no, "tur": tur, "aciklama": aciklama, "tutar": tutar}
        supabase.table("muhasebe").insert(data).execute()
        st.success(f"Erfolgreich gespeichert!")

# --- AYLIK RAPORLAMA VE PDF ---
st.divider()
st.subheader("📄 Monatsbericht Erstellen")

today = datetime.date.today()
col_m, col_y = st.columns(2)

selected_month_name = col_m.selectbox("Monat wählen", list(GERMAN_MONTHS.values()), index=today.month - 1)
selected_month = list(GERMAN_MONTHS.keys())[list(GERMAN_MONTHS.values()).index(selected_month_name)]
# Yıl listesi 2026'dan başlıyor
selected_year = col_y.selectbox("Jahr wählen", [2026, 2027, 2028, 2029, 2030], index=0)

start_date = datetime.date(selected_year, selected_month, 1)
last_day = monthrange(selected_year, selected_month)[1]
end_date = datetime.date(selected_year, selected_month, last_day)

if st.button("PDF Bericht Generieren"):
    # 1. ÖNCEKİ DÖNEMDEN DEVREDENİ HESAPLA
    prev_res = supabase.table("muhasebe").select("tur, tutar").lt("tarih", str(start_date)).execute()
    db_prev_balance = 0.0
    for item in prev_res.data:
        db_prev_balance += float(item['tutar']) if item['tur'] == 'EINNAHMEN' else -float(item['tutar'])
    
    total_opening_balance = INITIAL_CASH_BALANCE + db_prev_balance

    # 2. SEÇİLEN AYIN VERİLERİ
    res = supabase.table("muhasebe").select("*").gte("tarih", str(start_date)).lte("tarih", str(end_date)).order("tarih").execute()
    
    if res.data:
        df_rep = pd.DataFrame(res.data)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, "KASSENBERICHT", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        # PDF üzerinde formatlanmış tarih: GG.AA.YYYY
        pdf.cell(190, 10, f"Monat: {selected_month_name} {selected_year}", ln=True, align="C")
        pdf.ln(10)

        # ÜBERTRAG (DEVREDEN)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(130, 10, f"Vortrag aus dem Vormonat", 1, 0, "L", True)
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
            # Tarihi formatla: YYYY-MM-DD -> DD.MM.YYYY
            fmt_date = datetime.datetime.strptime(str(row['tarih']), '%Y-%m-%d').strftime('%d.%m.%Y')
            pdf.cell(25, 8, fmt_date, 1)
            pdf.cell(30, 8, str(row['belge_no']), 1)
            pdf.cell(75, 8, str(row['aciklama'])[:40], 1)
            val = float(row['tutar'])
            if row['tur'] == 'EINNAHMEN':
                pdf.cell(30, 8, f"{val:.2f}", 1, 0, "R"); pdf.cell(30, 8, "-", 1, 0, "R")
                m_in += val
            else:
                pdf.cell(30, 8, "-", 1, 0, "R"); pdf.cell(30, 8, f"{val:.2f}", 1, 0, "R")
                m_out += val
            pdf.ln()

        # ÖZET
        pdf.ln(5)
        closing_balance = total_opening_balance + m_in - m_out
        pdf.set_font("Arial", "B", 10)
        pdf.cell(130, 8, "Summe Einnahmen:", 0); pdf.cell(60, 8, f"+ {m_in:.2f} EUR", 0, 1, "R")
        pdf.cell(130, 8, "Summe Ausgaben:", 0); pdf.cell(60, 8, f"- {m_out:.2f} EUR", 0, 1, "R")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(130, 10, "Endbestand:", 0); pdf.cell(60, 10, f"{closing_balance:.2f} EUR", 0, 1, "R")

        pdf_output = bytes(pdf.output())
        st.download_button(label=f"📥 {selected_month_name} Bericht PDF", data=pdf_output, file_name=f"Kassenbericht_{selected_month_name}.pdf")
    else:
        st.warning("Keine Daten gefunden.")

# --- AKTUELLER MONAT LİSTESİ ---
st.divider()
st.subheader(f"Buchungen im {GERMAN_MONTHS[today.month]}")

current_month_start = today.replace(day=1)
response = supabase.table("muhasebe").select("*").gte("tarih", str(current_month_start)).order("tarih", desc=True).execute()

if response.data:
    df_list = pd.DataFrame(response.data)
    # Listede tarih formatı: GG.AA.YYYY
    df_list['tarih'] = pd.to_datetime(df_list['tarih']).dt.strftime('%d.%m.%Y')
    df_display = df_list[['tarih', 'belge_no', 'tur', 'aciklama', 'tutar']].copy()
    df_display.columns = ['Datum', 'Beleg Nr', 'Typ', 'Beschreibung', 'Betrag (€)']
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("Noch keine Buchungen in diesem Monat.")
