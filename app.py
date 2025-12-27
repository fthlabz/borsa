import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. AYARLAR & TASARIM (FTHLABZ BLACK/GOLD)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Fthlabz Trader", page_icon="📈")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #FFD700; }
    .stTextInput > div > div > input { color: #FFD700; background-color: #1a1a1a; border: 1px solid #FFD700; text-align: center; }
    h1, h2, h3, h4, p, span, label { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    div[data-testid="metric-container"] { background-color: #111111; border: 1px solid #333; color: #FFD700; }
    .warning-box { background-color: #220000; border: 1px solid #FF0000; padding: 10px; border-radius: 5px; text-align: center; font-size: 0.8em; color: #FFcccc; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ÜST BÖLÜM (BAŞLIK & YASAL UYARI)
# -----------------------------------------------------------------------------
# Şirket İsmi Ortalanmış
st.markdown("<h1 style='text-align: center; color: #FFD700;'>⚜️ FTHLABZ PRO TRADER ⚜️</h1>", unsafe_allow_html=True)

# Yasal Uyarı & Gecikme Bilgisi
st.markdown("""
<div class="warning-box">
    ⚠️ <b>YASAL UYARI:</b> Burada yer alan bilgi, yorum ve tavsiyeler <b>YATIRIM DANIŞMANLIĞI KAPSAMINDA DEĞİLDİR.</b> 
    Kişisel görüşlere dayanmaktadır. <br>
    🕒 <b>BİLGİ:</b> Borsa İstanbul verileri 15 dakika gecikmeli olabilir. Kripto paralar anlıktır.
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
        
        # SAR (Append True ile güvenli hesaplama)
        df.ta.psar(af0=0.02, af=0.02, max_af=0.2, append=True)
        psar_cols = [c for c in df.columns if c.startswith('PSAR')]
        if psar_cols: df['SAR'] = df[psar_cols].bfill(axis=1).iloc[:, 0]
        else: df['SAR'] = df['Close']

        # ADX
        df.ta.adx(length=14, append=True)
        adx_col = [c for c in df.columns if c.startswith('ADX')][0]
        dmp_col = [c for c in df.columns if c.startswith('DMP')][0]
        dmn_col = [c for c in df.columns if c.startswith('DMN')][0]
        df['ADX_VAL'] = df[adx_col]
        df['DMP_VAL'] = df[dmp_col]
        df['DMN_VAL'] = df[dmn_col]

        # WaveTrend
        n1, n2 = 10, 21
        ap = (df['High'] + df['Low'] + df['Close']) / 3
        esa = ta.ema(ap, length=n1)
        d = ta.ema((ap - esa).abs(), length=n1)
        ci = (ap - esa) / (0.015 * d)
        tci = ta.ema(ci, length=n2)
        df['WT1'] = tci
        df['WT2'] = ta.sma(df['WT1'], length=4)

        return df, None
    except Exception as e: return None, str(e)

# -----------------------------------------------------------------------------
# 4. ARAYÜZ AKIŞI
# -----------------------------------------------------------------------------
col_input, col_dummy = st.columns([1, 0.1]) # Sadece ortalamak için dummy
ticker = st.text_input("Hisse Sembolü (Örn: THYAO.IS)", value="THYAO.IS").upper()

df, error = analyze_stock(ticker)

if error:
    st.error(f"Hata: {error}")
elif df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Skorlama
    score = 0
    bull_trend = (last['Close'] > last['ZLSMA']) and (last['Close'] > last['SMA21'])
    bear_trend = (last['Close'] < last['ZLSMA']) and (last['Close'] < last['SMA21'])
    if bull_trend: score += 25
    if bear_trend: score -= 25
    if last['Close'] > last['SAR']: score += 25
    else: score -= 25
    if last['DMP_VAL'] > last['DMN_VAL']: score += 25
    else: score -= 25
    if last['WT1'] > last['WT2']: score += 25
    else: score -= 25

    # --- METRİKLER (Dashboard) ---
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("Fiyat", f"{last['Close']:.2f}", f"{(last['Close'] - prev['Close']):.2f}")
    
    # Sinyal Renklendirme
    status_text = "NÖTR"
    if score >= 50: status_text = "✅ AL"
    if score >= 75: status_text = "🚀 GÜÇLÜ AL"
    if score <= -50: status_text = "🔻 SAT"
    if score <= -75: status_text = "🩸 GÜÇLÜ SAT"
    
    m2.metric("SİNYAL", status_text, f"Güç: %{abs(score)}")
    m3.metric("Trend (ZLSMA)", "YUKARI" if bull_trend else "AŞAĞI", delta_color="normal")
    m4.metric("ADX Gücü", f"{last['ADX_VAL']:.1f}", "Güçlü" if last['ADX_VAL'] > 20 else "Zayıf")

    # --- GRAFİK ---
    st.write("") # Boşluk
    fig = go.Figure()
    
    # 1. Mumlar
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    
    # 2. ZLSMA & SMA
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZLSMA 32'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='blue', width=1), name='SMA 21'))
    
    # 3. SAR (Noktalar) - İsteğin üzerine eklendi
    fig.add_trace(go.Scatter(x=df.index, y=df['SAR'], mode='markers', marker=dict(color='white', size=3), name='SAR'))

    fig.update_layout(
        title=dict(text=f"{ticker} TEKNİK ANALİZİ", x=0.5, font=dict(color='#FFD700')), # Grafik başlığı ortada
        template="plotly_dark", height=550, 
        paper_bgcolor='black', plot_bgcolor='black', 
        font=dict(color='#FFD700'),
        legend=dict(orientation="h", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Veriler yükleniyor...")

st.markdown("<center style='color: #444; font-size: 0.8em;'>FTHLABZ TECHNOLOGY © 2025</center>", unsafe_allow_html=True)
