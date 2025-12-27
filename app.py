import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import timedelta

# -----------------------------------------------------------------------------
# 1. AYARLAR & CSS (MİLYMETRİK TASARIM)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="⚜️")

st.markdown("""
<style>
    /* Ana Tema */
    .stApp { background-color: #000000; color: #FFD700; }
    
    /* GİZLEME BÖLÜMÜ (Header, Footer, Toolbar Yok) */
    header, footer {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    
    /* INPUT ALANI (SARI ÇİZGİLİ & ORTALI) */
    .stTextInput > div > div > input { 
        color: #FFD700 !important; 
        background-color: #000000 !important; 
        border: 2px solid #FFD700 !important; /* İstenilen Sarı Çizgi */
        text-align: center; 
        font-weight: bold;
        border-radius: 8px;
        font-size: 1.2em;
    }

    /* MİNYON METRİKLER İÇİN ÖZEL CSS SINIFLARI */
    .info-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding-bottom: 2px;
        font-family: 'Helvetica', sans-serif;
    }
    
    .price-tag {
        font-size: 1.1em;
        font-weight: bold;
        color: #FFFFFF;
    }
    
    .signal-tag {
        font-size: 1.0em;
        font-weight: bold;
        text-align: right;
    }
    
    .indicator-grid {
        display: grid;
        grid-template-columns: 1fr 1fr; /* İki sütun */
        gap: 5px;
        margin-top: 5px;
        font-family: 'Helvetica', sans-serif;
        font-size: 0.9em;
    }
    
    .ind-box-left { text-align: left; color: #CCC; }
    .ind-box-right { text-align: right; color: #CCC; }

    /* Renkler */
    .txt-green { color: #00FF00; }
    .txt-red { color: #FF0000; }
    
    /* Yasal Uyarı */
    .footer-box { 
        background-color: #1a0000; 
        border-top: 1px solid #FF0000; 
        padding: 15px; 
        text-align: center; 
        font-size: 0.7em; 
        color: #aa4444; 
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ŞİRKET LOGOSU
# -----------------------------------------------------------------------------
st.markdown("""
<div style='text-align: center; padding-bottom: 10px; margin-top: -60px;'>
    <h1 style='font-size: 2.2em; margin: 0; text-shadow: 2px 2px 4px #000000;'>⚜️ FTHLABZ ⚜️</h1>
</div>
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

    try_sym = raw_symbol + "-USD"
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
# 4. ARAYÜZ (COMPACT DESIGN)
# -----------------------------------------------------------------------------

# Ekranı daraltıyoruz ki her şey ortada toplansın (Mobil görünüm için kritik)
c_left, c_center, c_right = st.columns([1, 2, 1])

with c_center:
    # Kullanıcı Input'u (Session State yerine doğrudan widget kullanıyoruz, daha hızlı tepki için)
    # Önce varsayılan değer
    if 'symbol' not in st.session_state: st.session_state.symbol = "THYAO"
    
    # --- 1. HESAPLAMA (Input'tan önce yapıyoruz ki veriyi Input'un üstüne yazabilelim) ---
    # Streamlit'te input widget'ı en başta tanımlanmalı, ama biz veriyi üstüne yazacağız.
    # Bu yüzden önce "Placeholder" (Yer tutucu) koyuyoruz.
    
    top_info_placeholder = st.empty() # Fiyat ve Sinyal buraya gelecek
    
    user_input = st.text_input("", value="THYAO", placeholder="Hisse Gir").upper()
    
    bottom_info_placeholder = st.empty() # İndikatörler buraya gelecek
    chart_placeholder = st.empty()       # Grafik buraya gelecek

    # Hesaplama Başlasın
    df, active_symbol, error = get_smart_data(user_input)

    if error:
        top_info_placeholder.error("Bulunamadı")
    elif df is not None:
        df = analyze_stock_data(df)
        last = df.iloc[-1]
        
        # --- MANTIK ---
        zlsma_bull = last['Close'] > last['ZLSMA']
        sma_bull = last['Close'] > last['SMA21']
        sar_bull = last['Close'] > last['SAR']
        adx_bull = last['DMP_VAL'] > last['DMN_VAL']
        
        bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
        bear_count = 4 - bull_count
        
        # --- HTML GÖRSELLEŞTİRME ---
        
        # 1. SİNYAL METNİ VE RENGİ
        if bull_count >= 3:
            sig_txt = "GÜÇLÜ AL"
            sig_class = "txt-green"
        elif bear_count >= 3:
            sig_txt = "GÜÇLÜ SAT"
            sig_class = "txt-red"
        else:
            sig_txt = "NÖTR"
            sig_class = ""

        # 2. OKLAR VE RENKLER (ZL, SM, SA, AD)
        def get_arrow_html(is_bull):
            if is_bull: return "<span class='txt-green'>⬆</span>"
            else: return "<span class='txt-red'>⬇</span>"

        zl_arrow = get_arrow_html(zlsma_bull)
        sm_arrow = get_arrow_html(sma_bull)
        sa_arrow = get_arrow_html(sar_bull)
        ad_arrow = get_arrow_html(adx_bull)

        # --- YERLEŞTİRME ---

        # A) FİYAT VE ANA SİNYAL (Input'un Üstü)
        top_info_placeholder.markdown(f"""
        <div class="info-container">
            <div class="price-tag">{last['Close']:.2f}</div>
            <div class="signal-tag {sig_class}">{sig_txt}</div>
        </div>
        """, unsafe_allow_html=True)

        # B) İNDİKATÖRLER (Input'un Altı)
        bottom_info_placeholder.markdown(f"""
        <div style='text-align:center; color:#555; font-size:0.7em; margin-top:2px;'>{active_symbol}</div>
        <div class="indicator-grid">
            <div class="ind-box-left">ZL {zl_arrow}</div>
            <div class="ind-box-right">SM {sm_arrow}</div>
            <div class="ind-box-left">SA {sa_arrow}</div>
            <div class="ind-box-right">AD {ad_arrow}</div>
        </div>
        """, unsafe_allow_html=True)

        # C) GRAFİK (Sabit 1 Aylık)
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=30)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
        fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZL'))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SM'))
        
        fig.update_layout(
            margin=dict(l=5, r=5, t=10, b=10),
            template="plotly_dark", 
            height=300, # Daha minyon grafik
            paper_bgcolor='black', 
            plot_bgcolor='black', 
            showlegend=False,
            xaxis=dict(range=[start_date, end_date], fixedrange=True, rangeslider=dict(visible=False)),
            yaxis=dict(fixedrange=True),
            dragmode=False
        )
        chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False})

# Yasal Uyarı
st.markdown("""<div class="footer-box">⚠️ YATIRIM TAVSİYESİ DEĞİLDİR.<br>FTHLABZ TECHNOLOGY © 2025</div>""", unsafe_allow_html=True)
