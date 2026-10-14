import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Gelir-Gider & Muhasebe Takip",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Veritabanı Bağlantısı ve Tablo Oluşturma
def db_baglantisi():
    conn = sqlite3.connect("muhasebe.db", check_same_thread=False)
    return conn

def tablolari_olustur():
    with db_baglantisi() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                tur TEXT NOT NULL,
                kategori TEXT NOT NULL,
                tutar REAL NOT NULL,
                aciklama TEXT,
                yil_ay TEXT NOT NULL
            )
        """)
        conn.commit()

tablolari_olustur()

# Veritabanı Yardımcı Fonksiyonları
def islem_ekle(tarih, tur, kategori, tutar, aciklama):
    yil_ay = tarih.strftime("%Y-%m")
    with db_baglantisi() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO islemler (tarih, tur, kategori, tutar, aciklama, yil_ay)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tarih.strftime("%Y-%m-%d"), tur, kategori, tutar, aciklama, yil_ay))
        conn.commit()

def islem_sil(islem_id):
    with db_baglantisi() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM islemler WHERE id = ?", (islem_id,))
        conn.commit()

def islemleri_getir(yil_ay=None):
    with db_baglantisi() as conn:
        if yil_ay and yil_ay != "Tüm Zamanlar":
            df = pd.read_sql_query(
                "SELECT * FROM islemler WHERE yil_ay = ? ORDER BY tarih DESC, id DESC",
                conn,
                params=(yil_ay,)
            )
        else:
            df = pd.read_sql_query(
                "SELECT * FROM islemler ORDER BY tarih DESC, id DESC",
                conn
            )
    return df

def mevcut_aylari_getir():
    with db_baglantisi() as conn:
        df = pd.read_sql_query("SELECT DISTINCT yil_ay FROM islemler ORDER BY yil_ay DESC", conn)
    return df["yil_ay"].tolist()

# CSS İle Arayüzü Güzelleştirme
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px 20px;
        border-left: 5px solid #2b5c8f;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Başlık
st.title("💼 Gelir - Gider & Kâr/Zarar Muhasebe Takip Sistemi")
st.markdown("Aylık finansal hareketlerinizi kaydedin, kategorilendirin ve kâr/zarar durumunuzu anlık olarak analiz edin.")
st.write("---")

# Yan Panel (Sidebar) - Filtreleme ve Hızlı İşlem
st.sidebar.header("🗓️ Dönem Seçimi")
ay_listesi = mevcut_aylari_getir()
suanki_ay = datetime.now().strftime("%Y-%m")

secenekler = ["Tüm Zamanlar"]
if suanki_ay not in ay_listesi:
    secenekler.append(suanki_ay)
secenekler.extend(ay_listesi)
secenekler = sorted(list(set(secenekler)), reverse=True)

secilen_ay = st.sidebar.selectbox("Görüntülenecek Ay / Dönem:", secenekler, index=0)

# Yan Panel - Yeni Kayıt Formu
st.sidebar.markdown("---")
st.sidebar.header("➕ Yeni Kayıt Ekle")

with st.sidebar.form(key="islem_formu", clear_on_submit=True):
    islem_tur = st.selectbox("İşlem Türü", ["Gelir (Girdi)", "Gider (Çıktı)"])
    
    gelir_kategorileri = ["Satış / Ciro", "Hizmet Bedeli", "Kira Geliri", "Yatırım", "Diğer Gelir"]
    gider_kategorileri = ["Kira", "Maaş / Personel", "Fatura (Elektrik/Su/İnt)", "Hammadde / Mal Alımı", "Vergi / Harç", "Pazarlama / Reklam", "Ulaşım / Yakıt", "Diğer Gider"]
    
    kategori_secenek = gelir_kategorileri if "Gelir" in islem_tur else gider_kategorileri
    kategori = st.selectbox("Kategori", kategori_secenek)
    
    tutar = st.number_input("Tutar (₺)", min_value=0.01, step=50.0, format="%.2f")
    tarih = st.date_input("İşlem Tarihi", value=date.today())
    aciklama = st.text_input("Açıklama (Opsiyonel)", "")
    
    kaydet_btn = st.form_submit_button("💾 İşlemi Kaydet")
    
    if kaydet_btn:
        tur_kod = "Gelir" if "Gelir" in islem_tur else "Gider"
        islem_ekle(tarih, tur_kod, kategori, tutar, aciklama)
        st.success("✅ İşlem başarıyla kaydedildi!")
        st.rerun()

# Ana Sayfa Verileri Getirme
df_islemler = islemleri_getir(secilen_ay)

# KPI / Özet Kartları
toplam_gelir = df_islemler[df_islemler["tur"] == "Gelir"]["tutar"].sum() if not df_islemler.empty else 0.0
toplam_gider = df_islemler[df_islemler["tur"] == "Gider"]["tutar"].sum() if not df_islemler.empty else 0.0
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
    st.metric(
        label="⚖️ Net Kâr / Zarar",
        value=f"{net_kar:,.2f} ₺",
        delta=f"{net_kar:,.2f} ₺",
        delta_color="normal" if net_kar >= 0 else "inverse"
    )

with col4:
    kar_marji = ((net_kar / toplam_gelir) * 100) if toplam_gelir > 0 else 0
    st.metric(
        label="📊 Kâr Marjı",
        value=f"%{kar_marji:.1f}"
    )

st.write("---")

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📋 İşlem Listesi ve Silme", "📈 Grafikler ve Analiz", "📊 Aylık Karşılaştırma Raporu"])

with tab1:
    st.subheader(f"Dönem İşlemleri ({secilen_ay})")
    
    if df_islemler.empty:
        st.info("Bu döneme ait henüz kayıtlı bir gelir veya gider bulunmuyor. Sol menüden yeni işlem ekleyebilirsiniz.")
    else:
        # Silme Bölümü
        col_list, col_sil = st.columns([3, 1])
        
        with col_sil:
            st.markdown("#### 🗑️ İşlem Sil")
            silinecek_id = st.selectbox(
                "Silmek istediğiniz ID:",
                options=df_islemler["id"].tolist(),
                format_func=lambda x: f"ID #{x} - {df_islemler.loc[df_islemler['id'] == x, 'kategori'].values[0]} ({df_islemler.loc[df_islemler['id'] == x, 'tutar'].values[0]:,.2f} ₺)"
            )
            
            if st.button("⚠️ Seçilen İşlemi Sil", type="primary"):
                islem_sil(silinecek_id)
                st.warning(f"ID #{silinecek_id} başarıyla silindi!")
                st.rerun()
                
            # CSV Dışa Aktarma
            csv_data = df_islemler.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Tabloyu CSV Olarak İndir",
                data=csv_data,
                file_name=f"muhasebe_{secilen_ay}.csv",
                mime="text/csv"
            )
        
        with col_list:
            st.markdown("#### 📋 Kayıtlı Hareketler")
            
            gorunum_df = df_islemler.copy()
            gorunum_df["Tutar (₺)"] = gorunum_df["tutar"].apply(lambda x: f"{x:,.2f} ₺")
            gorunum_df = gorunum_df.rename(columns={
                "id": "ID",
                "tarih": "Tarih",
                "tur": "Tür",
                "kategori": "Kategori",
                "aciklama": "Açıklama"
            })
            
            # Renkli veya biçimlendirilmiş gösterim
            st.dataframe(
                gorunum_df[["ID", "Tarih", "Tür", "Kategori", "Tutar (₺)", "Açıklama"]],
                use_container_width=True,
                height=380
            )

with tab2:
    st.subheader("Dönem Gelir ve Gider Dağılımı")
    if df_islemler.empty:
        st.info("Grafik oluşturmak için veri bulunamadı.")
    else:
        g1, g2 = st.columns(2)
        
        df_giderler = df_islemler[df_islemler["tur"] == "Gider"]
        df_gelirler = df_islemler[df_islemler["tur"] == "Gelir"]
        
        with g1:
            if not df_giderler.empty:
                gider_ozet = df_giderler.groupby("kategori")["tutar"].sum().reset_index()
                fig_gider = px.pie(
                    gider_ozet,
                    values="tutar",
                    names="kategori",
                    title="🔴 Gider (Çıktı) Dağılımı",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Reds_r
                )
                st.plotly_chart(fig_gider, use_container_width=True)
            else:
                st.info("Bu dönem için kayıtlı gider bulunmuyor.")
                
        with g2:
            if not df_gelirler.empty:
                gelir_ozet = df_gelirler.groupby("kategori")["tutar"].sum().reset_index()
                fig_gelir = px.pie(
                    gelir_ozet,
                    values="tutar",
                    names="kategori",
                    title="🟢 Gelir (Girdi) Dağılımı",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Greens_r
                )
                st.plotly_chart(fig_gelir, use_container_width=True)
            else:
                st.info("Bu dönem için kayıtlı gelir bulunmuyor.")

with tab3:
    st.subheader("📊 Aylık Kâr / Zarar Karşılaştırma Raporu")
    
    df_tum = islemleri_getir("Tüm Zamanlar")
    if df_tum.empty:
        st.info("Karşılaştırma için yeterli veri bulunmamaktadır.")
    else:
        # Aylık özet gruplaması
        aylik_pivot = df_tum.pivot_table(
            index="yil_ay",
            columns="tur",
            values="tutar",
            aggfunc="sum",
            fill_value=0
        ).reset_index()
        
        if "Gelir" not in aylik_pivot.columns:
            aylik_pivot["Gelir"] = 0.0
        if "Gider" not in aylik_pivot.columns:
            aylik_pivot["Gider"] = 0.0
            
        aylik_pivot = aylik_pivot.sort_values("yil_ay")
        aylik_pivot["Net Kâr / Zarar"] = aylik_pivot["Gelir"] - aylik_pivot["Gider"]
        aylik_pivot["Kâr Durumu"] = aylik_pivot["Net Kâr / Zarar"].apply(lambda x: "🟢 Kâr" if x >= 0 else "🔴 Zarar")
        
        # Kar/Zarar Çubuk Grafiği
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=aylik_pivot["yil_ay"],
            y=aylik_pivot["Gelir"],
            name="Toplam Gelir",
            marker_color="#2ecc71"
        ))
        fig_bar.add_trace(go.Bar(
            x=aylik_pivot["yil_ay"],
            y=aylik_pivot["Gider"],
            name="Toplam Gider",
            marker_color="#e74c3c"
        ))
        fig_bar.add_trace(go.Scatter(
            x=aylik_pivot["yil_ay"],
            y=aylik_pivot["Net Kâr / Zarar"],
            name="Net Kâr/Zarar",
            mode="lines+markers+text",
            text=[f"{v:,.0f}₺" for v in aylik_pivot["Net Kâr / Zarar"]],
            textposition="top center",
            line=dict(color="#2980b9", width=3)
        ))
        
        fig_bar.update_layout(
            title="Aylara Göre Gelir, Gider ve Net Kâr/Zarar Seyri",
            barmode="group",
            xaxis_title="Dönem (Yıl-Ay)",
            yaxis_title="Tutar (₺)",
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tablo Formatında Gösterim
        tablo_gosterim = aylik_pivot.copy()
        tablo_gosterim["Gelir"] = tablo_gosterim["Gelir"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim["Gider"] = tablo_gosterim["Gider"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim["Net Kâr / Zarar"] = tablo_gosterim["Net Kâr / Zarar"].apply(lambda x: f"{x:,.2f} ₺")
        tablo_gosterim = tablo_gosterim.rename(columns={"yil_ay": "Ay / Dönem"})
        
        st.dataframe(tablo_gosterim[["Ay / Dönem", "Gelir", "Gider", "Net Kâr / Zarar", "Kâr Durumu"]], use_container_width=True)
