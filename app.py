import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import timedelta

# -----------------------------------------------------------------------------
# 1. AYARLAR & CSS
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="⚜️")

st.markdown("""
<style>
    /* Ana Tema */
    .stApp { background-color: #000000; color: #FFD700; }
    
    /* GİZLEME */
    header, footer {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    
    /* INPUT ALANI */
    .stTextInput > div > div > input { 
        color: #FFD700 !important; 
        background-color: #050505 !important; 
        border: 2px solid #FFD700 !important; 
        text-align: center; 
        font-weight: bold;
        border-radius: 4px;
        font-size: 1.1em;
        padding: 5px;
    }

    /* LOGO & BAŞLIKLAR */
    .company-name {
        font-size: 2.2em;
        font-weight: 900;
        text-align: center;
        margin-top: -60px;
        margin-bottom: 0px;
        text-shadow: 2px 2px 4px #000000;
        color: #FFD700;
        letter-spacing: 2px;
    }
    .sub-header {
        font-size: 0.9em;
        text-align: center;
        color: #888;
        letter-spacing: 4px;
        margin-bottom: 15px;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* ÜST BAR */
    .top-bar-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding-bottom: 5px;
        font-family: 'Arial', sans-serif;
    }
    .price-text { font-size: 1.4em; font-weight: bold; color: white; }
    .signal-text { font-size: 1.1em; font-weight: bold; text-align: right; }

    /* İNDİKATÖR KUTULARI */
    .ind-card {
        background-color: #111;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 8px;
        margin-bottom: 5px;
        text-align: center;
    }
    .ind-title { font-size: 0.9em; font-weight: bold; color: #FFD700; display: block; }
    .ind-status { font-size: 0.8em; font-weight: bold; margin: 2px 0; display: block; }
    .ind-val { font-size: 0.7em; color: #666; font-family: monospace; display: block; }

    /* GRAFİK İÇİN ÖZEL ÇERÇEVE (CSS İLE) */
    /* Streamlit'in grafik kapsayıcısını hedefleyip çerçeve ekliyoruz */
    div[data-testid="stPlotlyChart"] {
        border: 1px solid #333;
        border-radius: 6px;
        padding: 5px;
        background-color: #080808; /* Grafiğin arkasına hafif ton */
        margin-top: 10px;
    }

    /* RENKLER */
    .c-green { color: #00FF00; text-shadow: 0 0 5px #003300; }
    .c-red { color: #FF0000; text-shadow: 0 0 5px #330000; }
    .c-gray { color: #888; }
    
    /* Footer */
    .footer-box { 
        background-color: #1a0000; border-top: 1px solid #FF0000; 
        padding: 10px; text-align: center; font-size: 0.6em; color: #aa4444; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGO
# -----------------------------------------------------------------------------
st.markdown("""
<div class="company-name">⚜️ FTHLABZ ⚜️</div>
<div class="sub-header">PRO TRADER SYSTEM</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. VERİ MOTORU
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

    return None, raw_symbol, "Bulunamadı"

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
# 4. ARAYÜZ
# -----------------------------------------------------------------------------
c_left, c_center, c_right = st.columns([1, 2, 1])

with c_center:
    if 'symbol' not in st.session_state: st.session_state.symbol = "THYAO"
    
    top_placeholder = st.empty()
    user_input = st.text_input("", value="THYAO", placeholder="Hisse Gir").upper()
    ind_placeholder = st.container()
    chart_placeholder = st.empty()

    df, active_symbol, error = get_smart_data(user_input)

    if error:
        top_placeholder.error("Sembol Bulunamadı")
    elif df is not None:
        df = analyze_stock_data(df)
        last = df.iloc[-1]
        
        # MANTIK
        zlsma_bull = last['Close'] > last['ZLSMA']
        sma_bull = last['Close'] > last['SMA21']
        sar_bull = last['Close'] > last['SAR']
        adx_bull = last['DMP_VAL'] > last['DMN_VAL']
        
        bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
        bear_count = 4 - bull_count
        
        if bull_count >= 3:
            sig_txt = "GÜÇLÜ AL"
            sig_cls = "c-green"
        elif bear_count >= 3:
            sig_txt = "GÜÇLÜ SAT"
            sig_cls = "c-red"
        else:
            sig_txt = "NÖTR"
            sig_cls = "c-gray"

        # A) FİYAT VE SİNYAL
        top_html = f"""
        <div class="top-bar-container">
            <div class="price-text">{last['Close']:.2f} ₺</div>
            <div class="signal-text {sig_cls}">{sig_txt}</div>
        </div>
        """
        top_placeholder.markdown(top_html, unsafe_allow_html=True)

        # B) İNDİKATÖRLER
        def make_card(label, val, is_bull):
            if is_bull:
                icon = "▲"
                st_text = "GÜÇLÜ"
                cls = "c-green"
            else:
                icon = "▼"
                st_text = "ZAYIF"
                cls = "c-red"
            
            return f"""
            <div class="ind-card">
                <span class="ind-title">{label}</span>
                <span class="ind-status {cls}">{icon} {st_text}</span>
                <span class="ind-val">{val:.2f}</span>
            </div>
            """

        with ind_placeholder:
            st.markdown(f"<div style='text-align:center; color:#444; font-size:0.6em; margin-bottom:5px;'>{active_symbol}</div>", unsafe_allow_html=True)
            r1c1, r1c2 = st.columns(2)
            with r1c1: st.markdown(make_card("ZL", last['ZLSMA'], zlsma_bull), unsafe_allow_html=True)
            with r1c2: st.markdown(make_card("SM", last['SMA21'], sma_bull), unsafe_allow_html=True)
            r2c1, r2c2 = st.columns(2)
            with r2c1: st.markdown(make_card("SA", last['SAR'], sar_bull), unsafe_allow_html=True)
            with r2c2: st.markdown(make_card("AD", last['ADX_VAL'], adx_bull), unsafe_allow_html=True)

        # C) GRAFİK (ÇERÇEVELİ & SON MUM AYARLI)
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=30)
        
        # Son mumun görünmesi için sağa boşluk ekliyoruz (Buffer)
        buffer_date = end_date + timedelta(days=3) # +3 gün ekledik ki sağda boşluk kalsın
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
        fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZL'))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SM'))
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            template="plotly_dark", 
            height=300, 
            paper_bgcolor='black', 
            plot_bgcolor='black', 
            showlegend=False,
            # X Ekseninde Bitiş Tarihini (end_date) değil, tamponlu tarihi (buffer_date) kullanıyoruz
            xaxis=dict(range=[start_date, buffer_date], fixedrange=True, visible=False),
            yaxis=dict(fixedrange=True, visible=False),
            dragmode=False
        )
        chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False})

st.markdown("""<div class="footer-box">⚠️ YATIRIM TAVSİYESİ DEĞİLDİR.<br>FTHLABZ TECHNOLOGY © 2025</div>""", unsafe_allow_html=True)
