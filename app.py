import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. AYARLAR & TASARIM (FTHLABZ GHOST MODE - V7)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="⚜️")

st.markdown("""
<style>
    /* Ana Tema: Siyah & Gold */
    .stApp { background-color: #000000; color: #FFD700; }
    
    /* ------------------------------------------------------- */
    /* 🛑 GİZLEME BÖLÜMÜ (NÜKLEER MÜDAHALE) 🛑 */
    /* ------------------------------------------------------- */
    
    /* 1. Standart Header ve Footer'ları yok et */
    header, footer {visibility: hidden !important; display: none !important; height: 0px !important;}
    header[data-testid="stHeader"] {display: none !important;}
    
    /* 2. Toolbar ve Menüleri yok et */
    [data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    
    /* 3. JOKER MÜDAHALE: Alt kısımdaki o inatçı "Built with..." yazısını yakala */
    /* İsminin içinde 'viewerBadge' geçen her şeyi siler */
    div[class*="viewerBadge"] {display: none !important;}
    
    /* 4. Fullscreen butonunu hedef al ve yok et */
    button[title="View fullscreen"] {display: none !important;}
    
    /* ------------------------------------------------------- */

    /* Input Alanı */
    .stTextInput > div > div > input { 
        color: #FFD700; 
        background-color: #111111; 
        border: 1px solid #FFD700; 
        text-align: center; 
        font-weight: bold;
        border-radius: 10px;
    }
    
    /* Metinler */
    h1, h2, h3, p, span, label, div { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    
    /* Kartlar */
    div[data-testid="metric-container"] { 
        background-color: #111111; 
        border: 1px solid #333; 
        color: #FFD700; 
        border-radius: 8px;
        text-align: center;
        padding: 5px;
    }
    
    /* Footer Box */
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
# 2. BAŞLIK
# -----------------------------------------------------------------------------
st.markdown("""
<div style='text-align: center; padding-bottom: 20px; margin-top: -50px;'>
    <h1 style='font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px #000000;'>⚜️ FTHLABZ ⚜️</h1>
    <h3 style='font-size: 1.2em; margin: 0; letter-spacing: 3px; opacity: 0.9;'>PRO TRADER SYSTEM</h3>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HESAPLAMA MOTORU
# -----------------------------------------------------------------------------
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df is None or len(df) < 50: return None, "Veri yetersiz."
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)

        # İndikatörler
        df['SMA21'] = ta.sma(df['Close'], length=21)
        df['ZLSMA'] = ta.linreg(df['Close'], length=32, offset=0)
        df.ta.psar(af0=0.02, af=0.02, max_af=0.2, append=True)
        psar_cols = [c for c in df.columns if c.startswith('PSAR')]
        if psar_cols: df['SAR'] = df[psar_cols].bfill(axis=1).iloc[:, 0]
        else: df['SAR'] = df['Close']

        df.ta.adx(length=14, append=True)
        try:
            df['ADX_VAL'] = df[df.columns[df.columns.str.startswith('ADX_')][0]]
            df['DMP_VAL'] = df[df.columns[df.columns.str.startswith('DMP_')][0]]
            df['DMN_VAL'] = df[df.columns[df.columns.str.startswith('DMN_')][0]]
        except:
            df['ADX_VAL'] = 0; df['DMP_VAL'] = 0; df['DMN_VAL'] = 0

        return df, None
    except Exception as e: return None, str(e)

# -----------------------------------------------------------------------------
# 4. ARAYÜZ
# -----------------------------------------------------------------------------
col_in1, col_in2, col_in3 = st.columns([1, 2, 1])
with col_in2:
    ticker = st.text_input("", value="THYAO.IS", placeholder="Hisse Kodu").upper()

df, error = analyze_stock(ticker)

if error:
    st.error(f"Hata: {error}")
elif df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Logic
    zlsma_bull = last['Close'] > last['ZLSMA']
    sma_bull = last['Close'] > last['SMA21']
    sar_bull = last['Close'] > last['SAR']
    adx_bull = last['DMP_VAL'] > last['DMN_VAL']
    
    bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
    bear_count = 4 - bull_count
    
    signal_text = "NÖTR / BEKLE"
    if bull_count >= 3: signal_text = "🚀 AL" if bull_count == 3 else "🚀 GÜÇLÜ AL"
    elif bear_count >= 3: signal_text = "🔻 SAT" if bear_count == 3 else "🩸 GÜÇLÜ SAT"

    # Metrikler
    m1, m2 = st.columns(2)
    with m1:
        st.metric("FİYAT", f"{last['Close']:.2f}", f"{(last['Close'] - prev['Close']):.2f}")
    with m2:
        delta_color = "normal" if bull_count >=3 else "inverse" if bear_count >=3 else "off"
        st.metric("SİNYAL", signal_text, f"Güç: {int((max(bull_count, bear_count)/4)*100)}%", delta_color=delta_color)

    st.write("") 

    m3, m4 = st.columns(2)
    with m3:
        st.metric("ZLSMA", "🟢 YUKARI" if zlsma_bull else "🔴 AŞAĞI", f"{last['ZLSMA']:.2f}", delta_color="off")
    with m4:
        st.metric("SMA 21", "🟢 YUKARI" if sma_bull else "🔴 AŞAĞI", f"{last['SMA21']:.2f}", delta_color="off")

    st.write("") 

    m5, m6 = st.columns(2)
    with m5:
        st.metric("SAR", "🟢 ALICILI" if sar_bull else "🔴 SATICILI", f"{last['SAR']:.2f}", delta_color="off")
    with m6:
        st.metric("ADX", "🟢 BOĞA" if adx_bull else "🔴 AYI", f"{last['ADX_VAL']:.1f}", delta_color="off")

    # Grafik
    st.markdown("---")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZLSMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SMA 21'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SAR'], mode='markers', marker=dict(color='white', size=2), name='SAR'))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark", height=400, paper_bgcolor='black', plot_bgcolor='black', font=dict(color='#FFD700'), legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Veriler yükleniyor...")

# Footer
st.markdown("""<div class="footer-box">⚠️ <b>YASAL UYARI:</b> Yatırım tavsiyesi değildir.<br>FTHLABZ TECHNOLOGY © 2025</div>""", unsafe_allow_html=True)
