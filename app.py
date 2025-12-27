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
    /* Hata mesajlarını gizle/güzelleştir */
    .stAlert {
        background-color: #330000;
        color: #FFD700;
        border: 1px solid red;
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
        # Progress bar ekleyelim ki donmuş sanmasınlar
        with st.spinner('Veriler Fthlabz sunucularından çekiliyor...'):
            data = yf.download(symbol, period="1y", interval="1d", progress=False)
        
        if data is None or len(data) < 50:
            st.error("Veri alınamadı veya hisse sembolü hatalı.")
            return None
        
        # Sütun isimlerini düzelt (MultiIndex sorunu için)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        return data
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        return None

df = get_data(ticker)

if df is not None:
    # --- İNDİKATÖR HESAPLAMALARI (TRY-EXCEPT İLE KORUMALI) ---
    try:
        # 1. SMA 21
        df['SMA21'] = ta.sma(df['Close'], length=21)
        
        # 2. ZLSMA 32 (Linreg)
        df['ZLSMA'] = ta.linreg(df['Close'], length=32, offset=0)
        
        # 3. SAR (Fix: Daha güvenli hesaplama)
        # psar sonucu bazen nan dönebilir, kontrol ediyoruz
        sar_df = df.ta.psar(af0=0.02, af=0.02, max_af=0.2)
        if sar_df is not None and not sar_df.empty:
            # PSAR çıktısı genelde 2 sütundur (Long/Short), bunları birleştiriyoruz
            # İsimlere takılmadan 1. ve 2. sütunu alıp birleştiriyoruz (.iloc)
            df['SAR'] = sar_df.iloc[:, 0].combine_first(sar_df.iloc[:, 1])
        else:
            # Eğer hesaplanamazsa Close fiyatını ata (Çökmemesi için)
            df['SAR'] = df['Close']
        
        # 4. ADX (14)
        adx_df = df.ta.adx(length=14)
        if adx_df is not None and not adx_df.empty:
            # Sütun isimleri genelde ADX_14, DMP_14, DMN_14 olur ama garanti olsun diye iloc kullanıyoruz
            df['ADX'] = adx_df.iloc[:, 0]
            df['DMP'] = adx_df.iloc[:, 1]
            df['DMN'] = adx_df.iloc[:, 2]
        else:
            df['ADX'] = 0
            df['DMP'] = 0
            df['DMN'] = 0
        
        # 5. WaveTrend (Manuel Hesaplama - En garantisi)
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
        
        # Mantıksal Kontroller (Boş veri yoksa)
        bull_trend = (last_row['Close'] > last_row['ZLSMA']) and (last_row['Close'] > last_row['SMA21'])
        bear_trend = (last_row['Close'] < last_row['ZLSMA']) and (last_row['Close'] < last_row['SMA21'])
        
        sar_bull = last_row['Close'] > last_row['SAR']
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
        
        # SAR Noktaları (Görselleştirmek istersek)
        # fig.add_trace(go.Scatter(x=df.index, y=df['SAR'], mode='markers', marker=dict(color='white', size=2), name='SAR'))

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
    
    except Exception as e:
        st.error(f"Hesaplama Hatası: {e}")
        st.warning("Veriler anlık olarak işlenemedi, lütfen başka bir hisse deneyin veya sayfayı yenileyin.")

else:
    st.error("Hisse bulunamadı veya veri çekilemedi. Lütfen sembolü kontrol edin (Örn: THYAO.IS)")

# Footer
st.markdown("---")
st.markdown("<center>FTHLABZ TECHNOLOGY & TRADING SYSTEMS © 2025</center>", unsafe_allow_html=True)
