import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Ön Muhasebe & Kâr-Zarar Takip",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Veritabanı Başlatma
DB_FILE = "muhasebe.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            tur TEXT NOT NULL,
            kategori TEXT NOT NULL,
            aciklama TEXT,
            tutar REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Veri Tabanı Yardımcı Fonksiyonları
def veri_ekle(tarih, tur, kategori, aciklama, tutar):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar) VALUES (?, ?, ?, ?, ?)",
        (tarih.strftime("%Y-%m-%d"), tur, kategori, aciklama, float(tutar))
    )
    conn.commit()
    conn.close()

def veri_sil(islem_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM islemler WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()

def verileri_getir():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM islemler ORDER BY tarih DESC, id DESC", conn)
    conn.close()
    if not df.empty:
        df["tarih"] = pd.to_datetime(df["tarih"])
        df["yil_ay"] = df["tarih"].dt.strftime("%Y-%m")
    return df

# Verileri Yükle
df = verileri_getir()

# Başlık ve Üst Panel
st.title("💼 Aylık Ön Muhasebe & Kâr / Zarar Yönetimi")
st.caption("Gelir (Girdi) ve Gider (Çıktı) kalemlerinizi yönetin, aylık kâr/zarar durumunuzu anlık takip edin.")

# Kenar Çubuğu: Yeni Kalem Ekleme ve Ay Filtresi
with st.sidebar:
    st.header("➕ Yeni Kalem Ekle")
    
    with st.form("yeni_islem_formu", clear_on_submit=True):
        tarih = st.date_input("İşlem Tarihi", value=datetime.today())
        tur = st.radio("İşlem Türü", options=["Gelir (Girdi)", "Gider (Çıktı)"], horizontal=True)
        
        gelir_kategorileri = ["Satış / Ciro", "Hizmet Geliri", "Tahsilat", "Faiz / Yatırım", "Diğer Gelir"]
        gider_kategorileri = ["Kira", "Personel / Maaş", "Fatura (Elektrik/Su/İnt)", "Hammadde / Malzeme", "Vergi / Harç", "Pazarlama / Reklam", "Ulaşım / Yakıt", "Diğer Gider"]
        
        kategori_listesi = gelir_kategorileri if "Gelir" in tur else gider_kategorileri
        kategori = st.selectbox("Kategori", options=kategori_listesi)
        
        ozel_kategori = st.text_input("Özel Kategori (Opsiyonel)")
        if ozel_kategori.strip():
            kategori = ozel_kategori.strip()
            
        aciklama = st.text_area("Açıklama", placeholder="İşlem detayı (Örn: Mart ayı dükkan kirası)")
        tutar = st.number_input("Tutar (₺)", min_value=0.01, step=100.0, format="%.2f")
        
        kaydet = st.form_submit_button("💾 Kalemi Kaydet", use_container_width=True)
        if kaydet:
            tur_kisa = "Gelir" if "Gelir" in tur else "Gider"
            veri_ekle(tarih, tur_kisa, kategori, aciklama, tutar)
            st.success(f"{tur_kisa} başarıyla kaydedildi!")
            st.rerun()

    st.markdown("---")
    st.header("🗓️ Ay Seçimi")
    
    # Mevcut ayların listesini çıkar
    if not df.empty:
        mevcut_aylar = sorted(df["yil_ay"].unique(), reverse=True)
        suanki_ay = datetime.today().strftime("%Y-%m")
        if suanki_ay not in mevcut_aylar:
            mevcut_aylar.insert(0, suanki_ay)
    else:
        mevcut_aylar = [datetime.today().strftime("%Y-%m")]

    secilen_ay = st.selectbox(
        "Görüntülenecek Ayı Seçin",
        options=["Tüm Zamanlar"] + mevcut_aylar,
        index=1 if len(mevcut_aylar) > 0 else 0
    )

# Filtreleme
if secilen_ay == "Tüm Zamanlar":
    aktif_df = df.copy()
    donem_metni = "Tüm Zamanlar"
else:
    aktif_df = df[df["yil_ay"] == secilen_ay].copy() if not df.empty else pd.DataFrame()
    donem_metni = datetime.strptime(secilen_ay, "%Y-%m").strftime("%B %Y") if secilen_ay != "Tüm Zamanlar" else "Seçili Dönem"

# Metrik Kartları
st.subheader(f"📊 {donem_metni} Özeti")

toplam_gelir = aktif_df[aktif_df["tur"] == "Gelir"]["tutar"].sum() if not aktif_df.empty else 0.0
toplam_gider = aktif_df[aktif_df["tur"] == "Gider"]["tutar"].sum() if not aktif_df.empty else 0.0
net_kar = toplam_gelir - toplam_gider

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🟢 Toplam Girdi (Gelir)",
        value=f"{toplam_gelir:,.2f} ₺"
    )

with col2:
    st.metric(
        label="🔴 Toplam Çıktı (Gider)",
        value=f"{toplam_gider:,.2f} ₺"
    )

with col3:
    kar_renk = "normal" if net_kar >= 0 else "inverse"
    st.metric(
        label="⚖️ Net Kâr / Zarar",
        value=f"{net_kar:,.2f} ₺",
        delta=f"{(net_kar):,.2f} ₺ ({'KÂR' if net_kar >= 0 else 'ZARAR'})",
        delta_color=kar_renk
    )

with col4:
    kar_marji = (net_kar / toplam_gelir * 100) if toplam_gelir > 0 else 0.0
    st.metric(
        label="📈 Kâr Marjı",
        value=f"%{kar_marji:.1f}" if toplam_gelir > 0 else "0.0%"
    )

st.markdown("---")

# Sekmeli Detay Görünümü
tab1, tab2, tab3 = st.tabs(["📋 İşlem Kalemleri & Silme", "📊 Grafikler ve Analiz", "📈 Yıllık/Aylık Kâr-Zarar Tablosu"])

# TAB 1: İşlem Kalemleri & Silme
with tab1:
    st.write(f"### {donem_metni} - Kayıtlı Kalemler")
    
    if aktif_df.empty:
        st.info("Bu dönem için henüz bir girdi veya çıktı kaydı bulunmuyor. Soldaki menüden yeni kalem ekleyebilirsiniz.")
    else:
        # Tablo Görünümü
        gosterim_df = aktif_df.copy()
        gosterim_df["Tarih"] = gosterim_df["tarih"].dt.strftime("%d.%m.%Y")
        gosterim_df["Tutar (₺)"] = gosterim_df["tutar"].apply(lambda x: f"{x:,.2f} ₺")
        gosterim_df = gosterim_df.rename(columns={
            "id": "ID",
            "tur": "Tür",
            "kategori": "Kategori",
            "aciklama": "Açıklama"
        })
        
        st.dataframe(
            gosterim_df[["ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar (₺)"]],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 🗑️ Kalem Sil")
        sil_col1, sil_col2 = st.columns([3, 1])
        with sil_col1:
            silinecek_secim = st.selectbox(
                "Silmek istediğiniz kalemi seçin:",
                options=aktif_df["id"].tolist(),
                format_func=lambda x: f"ID #{x} | {aktif_df.loc[aktif_df['id']==x, 'tarih'].dt.strftime('%d.%m.%Y').values[0]} | {aktif_df.loc[aktif_df['id']==x, 'tur'].values[0]} | {aktif_df.loc[aktif_df['id']==x, 'kategori'].values[0]} | {aktif_df.loc[aktif_df['id']==x, 'tutar'].values[0]:,.2f} ₺ - {aktif_df.loc[aktif_df['id']==x, 'aciklama'].values[0] or ''}"
            )
        with sil_col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Seçili Kalemi Sil", type="primary", use_container_width=True):
                veri_sil(silinecek_secim)
                st.success(f"ID #{silinecek_secim} başarıyla silindi!")
                st.rerun()

        # Dışa Aktar Butonu
        st.download_button(
            label="📥 Bu Dönemi CSV Olarak İndir",
            data=aktif_df.to_csv(index=False).encode('utf-8'),
            file_name=f"muhasebe_{secilen_ay}.csv",
            mime="text/csv"
        )

# TAB 2: Grafikler ve Analiz
with tab2:
    if aktif_df.empty:
        st.info("Grafik oluşturmak için en az bir gelir veya gider kaydı girilmelidir.")
    else:
        grafik_col1, grafik_col2 = st.columns(2)
        
        gelirler = aktif_df[aktif_df["tur"] == "Gelir"]
        giderler = aktif_df[aktif_df["tur"] == "Gider"]
        
        with grafik_col1:
            st.write("#### 🟢 Gelir Dağılımı")
            if not gelirler.empty:
                fig_gelir = px.pie(
                    gelirler, 
                    values="tutar", 
                    names="kategori", 
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Greens_r
                )
                fig_gelir.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_gelir, use_container_width=True)
            else:
                st.caption("Seçili dönemde gelir kaydı bulunmuyor.")

        with grafik_col2:
            st.write("#### 🔴 Gider Dağılımı")
            if not giderler.empty:
                fig_gider = px.pie(
                    giderler, 
                    values="tutar", 
                    names="kategori", 
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Reds_r
                )
                fig_gider.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_gider, use_container_width=True)
            else:
                st.caption("Seçili dönemde gider kaydı bulunmuyor.")

# TAB 3: Aylık Kâr-Zarar Tablosu (Genel Karşılaştırma)
with tab3:
    st.write("### 📅 Ay Ay Kâr - Zarar Dengesi")
    
    if df.empty:
        st.info("Henüz geçmiş kayıt bulunmamaktadır.")
    else:
        # Aylara göre grupla
        aylik_ozet = df.groupby(["yil_ay", "tur"])["tutar"].sum().unstack(fill_value=0)
        
        if "Gelir" not in aylik_ozet.columns:
            aylik_ozet["Gelir"] = 0.0
        if "Gider" not in aylik_ozet.columns:
            aylik_ozet["Gider"] = 0.0
            
        aylik_ozet["Net Kâr / Zarar"] = aylik_ozet["Gelir"] - aylik_ozet["Gider"]
        aylik_ozet["Kâr Marjı (%)"] = aylik_ozet.apply(
            lambda r: (r["Net Kâr / Zarar"] / r["Gelir"] * 100) if r["Gelir"] > 0 else 0.0, axis=1
        )
        
        # Grafik
        aylik_ozet_reset = aylik_ozet.reset_index()
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=aylik_ozet_reset["yil_ay"],
            y=aylik_ozet_reset["Gelir"],
            name="Toplam Gelir (Girdi)",
            marker_color="#2ecc71"
        ))
        fig_bar.add_trace(go.Bar(
            x=aylik_ozet_reset["yil_ay"],
            y=aylik_ozet_reset["Gider"],
            name="Toplam Gider (Çıktı)",
            marker_color="#e74c3c"
        ))
        fig_bar.add_trace(go.Scatter(
            x=aylik_ozet_reset["yil_ay"],
            y=aylik_ozet_reset["Net Kâr / Zarar"],
            name="Net Kâr/Zarar",
            mode="lines+markers",
            line=dict(color="#2980b9", width=3)
        ))
        fig_bar.update_layout(
            barmode="group",
            xaxis_title="Dönem (Yıl-Ay)",
            yaxis_title="Tutar (₺)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Tablo formatı
        tablo_gosterim = aylik_ozet_reset.sort_values("yil_ay", ascending=False).copy()
        tablo_gosterim["Gelir (₺)"] = tablo_gosterim["Gelir"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim["Gider (₺)"] = tablo_gosterim["Gider"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim["Net Kâr / Zarar (₺)"] = tablo_gosterim["Net Kâr / Zarar"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim["Kâr Marjı"] = tablo_gosterim["Kâr Marjı (%)"].apply(lambda x: f"%{x:.1f}")
        
        st.dataframe(
            tablo_gosterim[["yil_ay", "Gelir (₺)", "Gider (₺)", "Net Kâr / Zarar (₺)", "Kâr Marjı"]].rename(columns={"yil_ay": "Ay (Dönem)"}),
            use_container_width=True,
            hide_index=True
        )
