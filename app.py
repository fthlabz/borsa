import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# -----------------------------------------------------------------------------
# 1. SAYFA YAPILANDIRMASI VE FTHLABZ TASARIMI (BLACK & GOLD)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="📈")

# Özel CSS: Siyah Arka Plan, Gold Yazılar
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #000000;
        color: #FFD700;
    }
    /* Input Alanları */
    .stTextInput > div > div > input {
        color: #FFD700;
        background-color: #1a1a1a;
        border: 1px solid #FFD700;
    }
    /* Başlıklar */
    h1, h2, h3 {
        color: #FFD700 !important;
        font-family: 'Helvetica', sans-serif;
        text-transform: uppercase;
    }
    /* Tablo ve Metrikler */
    div[data-testid="metric-container"] {
        background-color: #111111;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
        color: #FFD700;
    }
    label {
        color: #FFD700 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. BAŞLIK VE HİSSE GİRİŞİ
# -----------------------------------------------------------------------------
st.title("⚜️ FTHLABZ PRO TRADER ⚜️")
st.markdown("---")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Hisse Sembolü Girin (Örn: THYAO.IS, AAPL, BTC-USD)", value="THYAO.IS").upper()
with col2:
    st.write("") # Boşluk
    st.info(f"💡 Analiz Edilen: **{ticker}** | Sistem: **Ultimate Strategy**")

# -----------------------------------------------------------------------------
# 3. VERİ ÇEKME VE HESAPLAMA MOTORU
# -----------------------------------------------------------------------------
def get_data(symbol):
    try:
        data = yf.download(symbol, period="1y", interval="1d")
        if len(data) < 50:
            return None
        return data
    except:
        return None

df = get_data(ticker)

if df is not None:
    # --- İNDİKATÖR HESAPLAMALARI (PINE SCRIPT MANTIĞI) ---
    
    # 1. SMA 21
    df['SMA21'] = ta.sma(df['Close'], length=21)
    
    # 2. ZLSMA 32 (Linreg mantığına yakın simülasyon)
    df['ZLSMA'] = ta.linreg(df['Close'], length=32, offset=0)
    
    # 3. SAR
    # Pandas TA SAR farklı dönebilir, manuel hesaplama yerine kütüphane kullanıyoruz
    sar = ta.psar(df['High'], df['Low'], df['Close'], af0=0.01, af=0.01, max_af=0.2)
    # psar dönüşü bazen çoklu sütun olur, birleştiriyoruz
    sar_col = sar.columns[0] # long/short sütunlarını tek mantıkta birleştireceğiz
    df['SAR'] = sar[sar.columns[0]].combine_first(sar[sar.columns[1]])
    
    # 4. ADX (14)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx_df['ADX_14']
    df['DMP'] = adx_df['DMP_14']
    df['DMN'] = adx_df['DMN_14']
    
    # 5. WaveTrend (Hesaplaması Manuel)
    n1 = 10
    n2 = 21
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    esa = ta.ema(ap, length=n1)
    d = ta.ema((ap - esa).abs(), length=n1)
    ci = (ap - esa) / (0.015 * d)
    tci = ta.ema(ci, length=n2)
    df['WT1'] = tci
    df['WT2'] = ta.sma(df['WT1'], length=4)
    
    # --- SİNYAL MANTIĞI (ALGORİTMA) ---
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # Mantıksal Kontroller
    bull_trend = (last_row['Close'] > last_row['ZLSMA']) and (last_row['Close'] > last_row['SMA21'])
    bear_trend = (last_row['Close'] < last_row['ZLSMA']) and (last_row['Close'] < last_row['SMA21'])
    
    sar_bull = last_row['Close'] > last_row['SAR'] # Basit yaklaşım: Fiyat SAR üstünde mi?
    sar_bear = last_row['Close'] < last_row['SAR']
    
    adx_bull = last_row['DMP'] > last_row['DMN']
    adx_bear = last_row['DMN'] > last_row['DMP']
    
    wt_bull = last_row['WT1'] > last_row['WT2']
    wt_bear = last_row['WT1'] < last_row['WT2']
    
    # FTHLABZ SKORU
    score = 0
    if bull_trend: score += 25
    if sar_bull: score += 25
    if adx_bull: score += 25
    if wt_bull: score += 25
    
    if bear_trend: score -= 25
    if sar_bear: score -= 25
    if adx_bear: score -= 25
    if wt_bear: score -= 25

    # -----------------------------------------------------------------------------
    # 4. GÖRSEL PANEL (DASHBOARD)
    # -----------------------------------------------------------------------------
    
    # Ana Karar Kutusu
    st.markdown("### 📊 FTHLABZ KARAR MEKANİZMASI")
    
    decision_col1, decision_col2, decision_col3 = st.columns(3)
    
    with decision_col1:
        st.metric("Fiyat", f"{last_row['Close']:.2f}", f"{(last_row['Close'] - prev_row['Close']):.2f}")
    
    with decision_col2:
        trend_status = "YÜKSELİŞ" if score > 0 else "DÜŞÜŞ" if score < 0 else "YATAY"
        trend_color = "normal" if score == 0 else "off" # Streamlit native color limitation override via text below
        st.metric("Genel Trend", trend_status, f"Güç: {abs(score)}%")

    with decision_col3:
        signal_text = "BEKLE"
        if score == 100: signal_text = "🚀 GÜÇLÜ AL"
        elif score == -100: signal_text = "🩸 GÜÇLÜ SAT"
        elif score >= 50: signal_text = "✅ AL"
        elif score <= -50: signal_text = "🔻 SAT"
        
        st.metric("SİNYAL", signal_text)

    # Detaylı İndikatör Tablosu
    st.markdown("---")
    st.markdown("### 🛠 TEKNİK PARAMETRELER")
    
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    
    p_col1.metric("ZLSMA & SMA", "POZİTİF" if bull_trend else "NEGATİF", f"{last_row['ZLSMA']:.2f}")
    p_col2.metric("SAR Momentum", "ALICILI" if sar_bull else "SATICILI", f"{last_row['SAR']:.2f}")
    p_col3.metric("ADX Gücü", f"{last_row['ADX']:.1f}", "Güçlü" if last_row['ADX'] > 20 else "Zayıf")
    p_col4.metric("WaveTrend", "AL" if wt_bull else "SAT", f"{last_row['WT1']:.1f}")

    # -----------------------------------------------------------------------------
    # 5. PROFESYONEL GRAFİK (PLOTLY)
    # -----------------------------------------------------------------------------
    st.markdown("---")
    
    fig = go.Figure()

    # Mum Grafiği
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'],
                    name='Fiyat'))

    # İndikatör Çizgileri
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZLSMA 32'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='blue', width=1), name='SMA 21'))

    # Grafik Ayarları (Dark Theme)
    fig.update_layout(
        title=f"{ticker} - Fthlabz Teknik Analiz",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='#FFD700')
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Hisse bulunamadı veya veri çekilemedi. Lütfen sembolü kontrol edin (Örn: THYAO.IS)")

# Footer
st.markdown("---")
st.markdown("<center>FTHLABZ TECHNOLOGY & TRADING SYSTEMS © 2025</center>", unsafe_allow_html=True)
