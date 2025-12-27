import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import timedelta

# -----------------------------------------------------------------------------
# 1. AYARLAR & TASARIM (GİZLİ & KAMUFLAJ MODU)
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

    /* Input Alanı (Ortalı) */
    .stTextInput > div > div > input { 
        color: #FFD700; 
        background-color: #111111; 
        border: 1px solid #FFD700; 
        text-align: center; 
        font-weight: bold;
        border-radius: 10px;
        margin-top: -15px; /* Metriklerle arasını kapatmak için */
    }
    
    h1, h2, h3, p, span, label, div { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    
    /* Metrik Kutuları (Daha kompakt) */
    div[data-testid="metric-container"] { 
        background-color: #000000; 
        border: 0px solid #333; 
        color: #FFD700; 
        text-align: center;
        padding: 0px;
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
<div style='text-align: center; padding-bottom: 10px; margin-top: -60px;'>
    <h1 style='font-size: 2.2em; margin: 0; text-shadow: 2px 2px 4px #000000;'>⚜️ FTHLABZ ⚜️</h1>
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
# 5. ARAYÜZ MANTIĞI (ÖNCE HESAPLA SONRA GÖSTER)
# -----------------------------------------------------------------------------

# Streamlit akışı yukarıdan aşağı olduğu için, önce input'u "Session State" ile almamız lazım
# ki veriyi yukarıya (inputun üstüne) yazabilelim. Ancak basit olması için
# "Container" yapısı kullanacağız.

# 1. Önce Veriyi Çekelim (Varsayılan THYAO)
if 'symbol' not in st.session_state:
    st.session_state.symbol = "THYAO"

# Arayüz Düzeni: 3 Konteyner
top_metrics = st.container() # Fiyat ve Sinyal Buraya
input_area = st.container()  # Arama Kutusu Buraya
indicators = st.container()  # İndikatörler Buraya
charts = st.container()      # Grafik Buraya

# --- INPUT ALANI (ORTA) ---
with input_area:
    col_dummy1, col_inp, col_dummy2 = st.columns([1, 2, 1])
    with col_inp:
        # Kullanıcı buraya yazınca sayfa yenilenir
        user_input = st.text_input("", value="THYAO", placeholder="Hisse/Coin").upper()

# Veriyi İşle
df, active_symbol, error = get_smart_data(user_input)

if error:
    with top_metrics:
        st.error("Bulunamadı")
elif df is not None:
    df = analyze_stock_data(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- MANTIK ---
    zlsma_bull = last['Close'] > last['ZLSMA']
    sma_bull = last['Close'] > last['SMA21']
    sar_bull = last['Close'] > last['SAR']
    adx_bull = last['DMP_VAL'] > last['DMN_VAL']
    
    bull_count = sum([zlsma_bull, sma_bull, sar_bull, adx_bull])
    bear_count = 4 - bull_count
    
    # Ana Sinyal Metni
    main_val, main_col = "BEKLE", "off"
    if bull_count >= 3:
        main_val = "🟢 GÜÇLÜ"
        main_col = "normal"
    elif bear_count >= 3:
        main_val = "🔴 ZAYIF"
        main_col = "inverse"

    # İndikatör Metni (ÜÇGENLER)
    def get_tri_icon(is_bull):
        if is_bull: return "▲", "normal" # Yeşil Üçgen
        else: return "▼", "inverse"      # Kırmızı Ters Üçgen

    # --- 1. ÜST KATMAN (FİYAT VE SİNYAL) ---
    with top_metrics:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("FİYAT", f"{last['Close']:.2f}", f"{(last['Close'] - prev['Close']):.2f}")
        with c2:
            st.metric("SİNYAL", main_val, f"Güç: %{int((max(bull_count, bear_count)/4)*100)}", delta_color=main_col)
    
    # --- 2. INPUT ALTI BİLGİ ---
    with input_area:
         st.markdown(f"<div style='text-align:center; color:#666; font-size:0.8em; margin-bottom:5px;'>Analiz Edilen: <b>{active_symbol}</b></div>", unsafe_allow_html=True)

    # --- 3. İNDİKATÖRLER (ZL, SM, SA, AD) ---
    with indicators:
        # Satır 1: ZL ve SM
        i1, i2 = st.columns(2)
        with i1:
            ico, col = get_tri_icon(zlsma_bull)
            st.metric("ZL", ico, f"{last['ZLSMA']:.2f}", delta_color=col)
        with i2:
            ico, col = get_tri_icon(sma_bull)
            st.metric("SM", ico, f"{last['SMA21']:.2f}", delta_color=col)
        
        # Satır 2: SA ve AD
        i3, i4 = st.columns(2)
        with i3:
            ico, col = get_tri_icon(sar_bull)
            st.metric("SA", ico, f"{last['SAR']:.2f}", delta_color=col)
        with i4:
            ico, col = get_tri_icon(adx_bull)
            st.metric("AD", ico, f"{last['ADX_VAL']:.1f}", delta_color=col)

    # --- 4. GRAFİK (SABİT 1 AYLIK) ---
    with charts:
        st.write("")
        st.write("")
        fig = go.Figure()
        
        # Tarih Aralığı Hesapla (Son 30 Gün)
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=30)
        
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
        fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZL'))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='#00BFFF', width=1), name='SM'))
        
        # Grafik Ayarları (SABİT, ZOOM YOK, PAN YOK)
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            template="plotly_dark", 
            height=350, 
            paper_bgcolor='black', 
            plot_bgcolor='black', 
            font=dict(color='#FFD700'),
            showlegend=False, # Grafik daha sade olsun diye legend kapattım
            xaxis=dict(
                range=[start_date, end_date], # Sadece son 1 ayı göster
                fixedrange=True, # X ekseni kilitli (Zoom yok)
                rangeslider=dict(visible=False) # Alt slider yok
            ),
            yaxis=dict(
                fixedrange=True # Y ekseni kilitli (Zoom yok)
            ),
            dragmode=False # Sürükleme kapalı
        )
        # Modbar'ı tamamen gizle (Tepedeki zoom butonları vs.)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False})

else:
    st.warning("Veri yükleniyor...")

# Footer
st.markdown("""<div class="footer-box">⚠️ <b>YASAL UYARI:</b> Yatırım tavsiyesi değildir.<br>FTHLABZ TECHNOLOGY © 2025</div>""", unsafe_allow_html=True)
