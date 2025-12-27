import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. AYARLAR & TASARIM (FTHLABZ MOBILE PRO)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="⚜️")

st.markdown("""
<style>
    /* Ana Tema: Siyah & Gold */
    .stApp { background-color: #000000; color: #FFD700; }
    
    /* Input Alanı (Ortalı ve Şık) */
    .stTextInput > div > div > input { 
        color: #FFD700; 
        background-color: #111111; 
        border: 1px solid #FFD700; 
        text-align: center; 
        font-weight: bold;
        border-radius: 10px;
    }
    
    /* Metinler ve Başlıklar */
    h1, h2, h3, p, span, label, div { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    
    /* Metrik Kutuları (Kart Görünümü) */
    div[data-testid="metric-container"] { 
        background-color: #111111; 
        border: 1px solid #333; 
        color: #FFD700; 
        border-radius: 8px;
        text-align: center;
        padding: 5px;
    }
    
    /* Yasal Uyarı Kutusu (En Altta) */
    .footer-box { 
        background-color: #1a0000; 
        border-top: 2px solid #FF0000; 
        padding: 20px; 
        text-align: center; 
        font-size: 0.75em; 
        color: #aa4444 !important; 
        margin-top: 50px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. BAŞLIK (DERLİ TOPLU LOGO)
# -----------------------------------------------------------------------------
st.markdown("""
<div style='text-align: center; padding-bottom: 20px;'>
    <h1 style='font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px #000000;'>⚜️ FTHLABZ ⚜️</h1>
    <h3 style='font-size: 1.2em; margin: 0; letter-spacing: 3px; opacity: 0.9;'>PRO TRADER SYSTEM</h3>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HESAPLAMA MOTORU (3'lü ONAY SİSTEMİ)
# -----------------------------------------------------------------------------
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df is None or len(df) < 50: return None, "Veri yetersiz."
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)

        # --- İNDİKATÖRLER ---
        # 1. SMA 21
        df['SMA21'] = ta.sma(df['Close'], length=21)
        
        # 2. ZLSMA 32
        df['ZLSMA'] = ta.linreg(df['Close'], length=32, offset=0)
        
        # 3. SAR
        df.ta.psar(af0=0.02, af=0.02, max_af=0.2, append=True)
        psar_cols = [c for c in df.columns if c.startswith('PSAR')]
        if psar_cols: df['SAR'] = df[psar_cols].bfill(axis=1).iloc[:, 0]
        else: df['SAR'] = df['Close']

        # 4. ADX (Güç için)
        df.ta.adx(length=14, append=True)
        # Sütun isimlerini güvenli alalım
        try:
            df['ADX_VAL'] = df[df.columns[df.columns.str.startswith('ADX_')][0]]
            df['DMP_VAL'] = df[df.columns[df.columns.str.startswith('DMP_')][0]]
            df['DMN_VAL'] = df[df.columns[df.columns.str.startswith('DMN_')][0]]
        except:
            # Yedek hesaplama (hata olursa çökmesin)
            df['ADX_VAL'] = 0; df['DMP_VAL'] = 0; df['DMN_VAL'] = 0

        return df, None
    except Exception as e: return None, str(e)

# -----------------------------------------------------------------------------
# 4. ARAYÜZ VE SİNYAL MANTIĞI
# -----------------------------------------------------------------------------
# Input Alanı
col_in1, col_in2, col_in3 = st.columns([1, 2, 1])
with col_in2:
    ticker = st.text_input("", value="THYAO.IS", placeholder="Hisse Kodu (Örn: GARAN.IS)").upper()

df, error = analyze_stock(ticker)

if error:
    st.error(f"Hata: {error}")
elif df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- MANTIK (LOGIC) ---
    # 1. ZLSMA Durumu
    zlsma_bull = last['Close'] > last['ZLSMA']
    
    # 2. SMA 21 Durumu
    sma_bull = last['Close'] > last['SMA21']
    
    # 3. SAR Durumu
    sar_bull = last['Close'] > last['SAR']
    
    # 4. ADX Durumu
    adx_bull = last['DMP_VAL'] > last['DMN_VAL']
    
    # --- PUANLAMA (En az 3 Onay) ---
    bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
    bear_count = 4 - bull_count
    
    signal_text = "NÖTR / BEKLE"
    signal_color = "off"
    
    if bull_count >= 3:
        signal_text = "🚀 AL" if bull_count == 3 else "🚀 GÜÇLÜ AL"
        signal_color = "normal" # Streamlit yeşil algılar (positive delta)
    elif bear_count >= 3:
        signal_text = "🔻 SAT" if bear_count == 3 else "🩸 GÜÇLÜ SAT"
        signal_color = "inverse" # Streamlit kırmızı algılar (negative delta)

    # --- METRİKLER (2x2 Düzen - Mobilde Yan Yana) ---
    
    # SATIR 1: FİYAT ve SİNYAL
    m_row1_col1, m_row1_col2 = st.columns(2)
    
    with m_row1_col1:
        fiyat_degisim = last['Close'] - prev['Close']
        st.metric("FİYAT", f"{last['Close']:.2f}", f"{fiyat_degisim:.2f}")
        
    with m_row1_col2:
        # Renk hilesi: Eğer AL ise delta pozitif (yeşil), SAT ise negatif (kırmızı) olsun
        delta_val = bull_count if bull_count >= 3 else -bear_count if bear_count >=3 else 0
        st.metric("SİNYAL", signal_text, f"Güç: {int((bull_count/4)*100)}%" if bull_count >=3 else f"Güç: {int((bear_count/4)*100)}%", delta_color="normal" if bull_count >=3 else "inverse")

    st.write("") # Küçük boşluk

    # SATIR 2: ZLSMA ve SMA (OKLU GÖSTERİM)
    m_row2_col1, m_row2_col2 = st.columns(2)
    
    with m_row2_col1:
        # ZLSMA Logic
        z_icon = "🟢 YUKARI" if zlsma_bull else "🔴 AŞAĞI"
        st.metric("ZLSMA (Yön)", z_icon, f"{last['ZLSMA']:.2f}", delta_color="off")
        
    with m_row2_col2:
        # SMA Logic
        s_icon = "🟢 YUKARI" if sma_bull else "🔴 AŞAĞI"
        st.metric("SMA 21 (Yön)", s_icon, f"{last['SMA21']:.2f}", delta_color="off")

    st.write("") # Küçük boşluk

    # SATIR 3: SAR ve ADX (YUKARI ALINDI)
    m_row3_col1, m_row3_col2 = st.columns(2)
    
    with m_row3_col1:
        sar_durum = "🟢 ALICILI" if sar_bull else "🔴 SATICILI"
        st.metric("SAR (Baskı)", sar_durum, f"{last['SAR']:.2f}", delta_color="off")
        
    with m_row3_col2:
        adx_durum = "🟢 BOĞA" if adx_bull else "🔴 AYI"
        st.metric("ADX (Trend)", adx_durum, f"{last['ADX_VAL']:.1f}", delta_color="off")

    # --- GRAFİK ---
    st.markdown("---")
    fig = go.Figure()
    
    # Mumlar
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    
    # Çizgiler
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZLSMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SMA 21'))
    
    # SAR Noktaları
    fig.add_trace(go.Scatter(x=df.index, y=df['SAR'], mode='markers', marker=dict(color='white', size=2), name='SAR'))

    # Grafik Ayarları (Mobil İçin Yükseklik Optimize Edildi)
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10), # Kenar boşluklarını azalttık
        template="plotly_dark", 
        height=400, # Mobil için ideal yükseklik
        paper_bgcolor='black', 
        plot_bgcolor='black', 
        font=dict(color='#FFD700'),
        legend=dict(orientation="h", y=1.1, x=0) # Legend üstte yatay
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Veriler yükleniyor...")

# -----------------------------------------------------------------------------
# 5. FOOTER (YASAL UYARI - EN DİPTE)
# -----------------------------------------------------------------------------
st.markdown("""
<div class="footer-box">
    ⚠️ <b>YASAL UYARI</b><br>
    Burada yer alan bilgi, yorum ve tavsiyeler <b>YATIRIM DANIŞMANLIĞI KAPSAMINDA DEĞİLDİR.</b> 
    Sadece kişisel teknik analiz çalışmasıdır. <br><br>
    FTHLABZ TECHNOLOGY © 2025
</div>
""", unsafe_allow_html=True)
