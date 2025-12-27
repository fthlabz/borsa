import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. AYARLAR & TASARIM (FTHLABZ GHOST MODE)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="⚜️")

st.markdown("""
<style>
    /* Ana Tema: Siyah & Gold */
    .stApp { background-color: #000000; color: #FFD700; }
    
    /* ------------------------------------------------------- */
    /* 🛑 GİZLEME BÖLÜMÜ 🛑 */
    /* ------------------------------------------------------- */
    header, footer {visibility: hidden !important; display: none !important; height: 0px !important;}
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    div[class*="viewerBadge"] {display: none !important;}
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
    
    h1, h2, h3, p, span, label, div { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    
    /* Metrik Kutuları */
    div[data-testid="metric-container"] { 
        background-color: #111111; 
        border: 1px solid #333; 
        color: #FFD700; 
        border-radius: 8px;
        text-align: center;
        padding: 5px;
    }
    
    /* Yasal Uyarı */
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
# 3. AKILLI VERİ MOTORU
# -----------------------------------------------------------------------------
def get_smart_data(raw_symbol):
    raw_symbol = raw_symbol.strip().upper()
    if "." in raw_symbol or "-" in raw_symbol:
        df = yf.download(raw_symbol, period="1y", interval="1d", progress=False)
        if df is not None and len(df) > 10: return df, raw_symbol, None
    
    crypto_list = ["BTC", "ETH", "XRP", "SOL", "AVAX", "DOGE", "SHIB", "USDT", "BNB", "ADA", "TRX"]
    if raw_symbol in crypto_list:
        try_sym = raw_symbol + "-USD"
        df = yf.download(try_sym, period="1y", interval="1d", progress=False)
        if df is not None and len(df) > 10: return df, try_sym, None

    try_sym = raw_symbol + ".IS"
    df = yf.download(try_sym, period="1y", interval="1d", progress=False)
    if df is not None and len(df) > 10: return df, try_sym, None

    try_sym = raw_symbol
    df = yf.download(try_sym, period="1y", interval="1d", progress=False)
    if df is not None and len(df) > 10: return df, try_sym, None

    try_sym = raw_symbol + "-USD"
    df = yf.download(try_sym, period="1y", interval="1d", progress=False)
    if df is not None and len(df) > 10: return df, try_sym, None

    return None, raw_symbol, "Bulunamadı"

# -----------------------------------------------------------------------------
# 4. TEKNİK ANALİZ
# -----------------------------------------------------------------------------
def analyze_stock_data(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
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
    return df

# -----------------------------------------------------------------------------
# 5. ARAYÜZ
# -----------------------------------------------------------------------------
col_in1, col_in2, col_in3 = st.columns([1, 2, 1])
with col_in2:
    user_input = st.text_input("", value="THYAO", placeholder="Hisse/Coin Gir").upper()

df, active_symbol, error = get_smart_data(user_input)

if error:
    st.error(f"⚠️ {user_input} bulunamadı.")
elif df is not None:
    df = analyze_stock_data(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    st.markdown(f"<div style='text-align:center; color:#888; font-size:0.8em; margin-bottom:10px;'>Analiz Edilen: <b>{active_symbol}</b></div>", unsafe_allow_html=True)
    
    # --- MANTIK ---
    zlsma_bull = last['Close'] > last['ZLSMA']
    sma_bull = last['Close'] > last['SMA21']
    sar_bull = last['Close'] > last['SAR']
    adx_bull = last['DMP_VAL'] > last['DMN_VAL']
    
    bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
    bear_count = 4 - bull_count
    
    # --- METİN VE RENK FONKSİYONLARI ---
    
    # 1. Ana Sinyal Metni
    main_val, main_col = "BEKLE", "off"
    if bull_count >= 3:
        main_val = "🟢 GÜÇLÜ"
        main_col = "normal" # Yeşil
    elif bear_count >= 3:
        main_val = "🔴 ZAYIF"
        main_col = "inverse" # Kırmızı

    # 2. İndikatör Metni (Yön)
    def get_ind_text(is_bull):
        if is_bull:
            return "⬆ YUKARI", "normal" # Yeşil
        else:
            return "⬇ AŞAĞI", "inverse" # Kırmızı

    # --- METRİKLER ---
    
    # 1. Satır: Fiyat ve SİNYAL
    m1, m2 = st.columns(2)
    with m1:
        st.metric("FİYAT", f"{last['Close']:.2f}", f"{(last['Close'] - prev['Close']):.2f}")
    with m2:
        # Ana Sinyal Kutusunda Güçlü/Zayıf yazar
        st.metric("SİNYAL", main_val, f"Güç: %{int((max(bull_count, bear_count)/4)*100)}", delta_color=main_col)

    st.write("") 

    # 2. Satır: ZL ve SM
    m3, m4 = st.columns(2)
    with m3:
        txt, col = get_ind_text(zlsma_bull)
        st.metric("ZL", txt, f"{last['ZLSMA']:.2f}", delta_color=col)
    with m4:
        txt, col = get_ind_text(sma_bull)
        st.metric("SM", txt, f"{last['SMA21']:.2f}", delta_color=col)

    st.write("") 

    # 3. Satır: SA ve AD
    m5, m6 = st.columns(2)
    with m5:
        txt, col = get_ind_text(sar_bull)
        st.metric("SA", txt, f"{last['SAR']:.2f}", delta_color=col)
    with m6:
        txt, col = get_ind_text(adx_bull)
        st.metric("AD", txt, f"{last['ADX_VAL']:.1f}", delta_color=col)

    # --- GRAFİK ---
    st.markdown("---")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZL'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SM'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SAR'], mode='markers', marker=dict(color='white', size=2), name='SA'))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark", height=400, paper_bgcolor='black', plot_bgcolor='black', font=dict(color='#FFD700'), legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Veriler yükleniyor...")

# Footer
st.markdown("""<div class="footer-box">⚠️ <b>YASAL UYARI:</b> Yatırım tavsiyesi değildir.<br>FTHLABZ TECHNOLOGY © 2025</div>""", unsafe_allow_html=True)
