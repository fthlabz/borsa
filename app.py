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
    .stTextInput > div > div > input { color: #FFD700; background-color: #1a1a1a; border: 1px solid #FFD700; }
    h1, h2, h3, h4, p, span, label { color: #FFD700 !important; font-family: 'Helvetica', sans-serif; }
    div[data-testid="metric-container"] { background-color: #111111; border: 1px solid #333; color: #FFD700; }
    .stAlert { background-color: #330000; color: #FFD700; border: 1px solid red; }
</style>
""", unsafe_allow_html=True)

st.title("⚜️ FTHLABZ PRO TRADER ⚜️")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. HESAPLAMA MOTORU (BASİTLEŞTİRİLMİŞ & GÜÇLENDİRİLMİŞ)
# -----------------------------------------------------------------------------
def analyze_stock(symbol):
    try:
        # Veri Çekme
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        
        if df is None or len(df) < 50:
            return None, "Veri yetersiz veya sembol hatalı."

        # YFinance MultiIndex düzeltmesi (Çok önemli)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # --- İNDİKATÖRLER ---
        
        # 1. SMA 21
        df['SMA21'] = ta.sma(df['Close'], length=21)
        
        # 2. ZLSMA (Linreg)
        df['ZLSMA'] = ta.linreg(df['Close'], length=32, offset=0)
        
        # 3. SAR (En Güvenli Yöntem: Append True)
        # Bu yöntem hata vermez, sütunları otomatik ekler
        df.ta.psar(af0=0.02, af=0.02, max_af=0.2, append=True)
        # Sütun isimleri dinamik oluşur (PSARl_... ve PSARs_...), bunları bulup birleştiriyoruz
        psar_cols = [c for c in df.columns if c.startswith('PSAR')]
        if psar_cols:
            # Long ve Short sütunlarını tek bir SAR sütununda birleştir
            df['SAR'] = df[psar_cols].bfill(axis=1).iloc[:, 0]
        else:
            df['SAR'] = df['Close'] # Yedek plan

        # 4. ADX
        df.ta.adx(length=14, append=True)
        # Sütunları bul (ADX_14, DMP_14, DMN_14 gibi isimleri vardır)
        adx_col = [c for c in df.columns if c.startswith('ADX')][0]
        dmp_col = [c for c in df.columns if c.startswith('DMP')][0]
        dmn_col = [c for c in df.columns if c.startswith('DMN')][0]
        
        df['ADX_VAL'] = df[adx_col]
        df['DMP_VAL'] = df[dmp_col]
        df['DMN_VAL'] = df[dmn_col]

        # 5. WaveTrend
        n1, n2 = 10, 21
        ap = (df['High'] + df['Low'] + df['Close']) / 3
        esa = ta.ema(ap, length=n1)
        d = ta.ema((ap - esa).abs(), length=n1)
        ci = (ap - esa) / (0.015 * d)
        tci = ta.ema(ci, length=n2)
        df['WT1'] = tci
        df['WT2'] = ta.sma(df['WT1'], length=4)

        return df, None

    except Exception as e:
        return None, str(e)

# -----------------------------------------------------------------------------
# 3. ARAYÜZ AKIŞI
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Hisse Sembolü", value="THYAO.IS").upper()

df, error = analyze_stock(ticker)

if error:
    st.error(f"Hata: {error}")
elif df is not None:
    # Son veriler
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Skorlama
    score = 0
    # Trend Yönü
    bull_trend = (last['Close'] > last['ZLSMA']) and (last['Close'] > last['SMA21'])
    bear_trend = (last['Close'] < last['ZLSMA']) and (last['Close'] < last['SMA21'])
    if bull_trend: score += 25
    if bear_trend: score -= 25
    
    # SAR
    if last['Close'] > last['SAR']: score += 25
    else: score -= 25
    
    # ADX
    if last['DMP_VAL'] > last['DMN_VAL']: score += 25
    else: score -= 25
    
    # WT
    if last['WT1'] > last['WT2']: score += 25
    else: score -= 25

    # GÖRSELLEŞTİRME
    st.info(f"💡 {ticker} Analizi Tamamlandı")
    
    # Metrikler
    m1, m2, m3 = st.columns(3)
    m1.metric("Fiyat", f"{last['Close']:.2f}", f"{(last['Close'] - prev['Close']):.2f}")
    
    status_text = "NÖTR"
    if score >= 50: status_text = "✅ AL"
    if score >= 75: status_text = "🚀 GÜÇLÜ AL"
    if score <= -50: status_text = "🔻 SAT"
    if score <= -75: status_text = "🩸 GÜÇLÜ SAT"
    
    m2.metric("Sinyal", status_text, f"Güç: %{abs(score)}")
    m3.metric("Trend (ZLSMA)", "POZİTİF" if bull_trend else "NEGATİF")

    # Grafik
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ZLSMA'], line=dict(color='yellow', width=2), name='ZLSMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA21'], line=dict(color='blue', width=1), name='SMA 21'))
    
    fig.update_layout(template="plotly_dark", height=500, paper_bgcolor='black', plot_bgcolor='black', font=dict(color='#FFD700'))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Veri bekleniyor...")

st.markdown("<center>FTHLABZ TECHNOLOGY © 2025</center>", unsafe_allow_html=True)
