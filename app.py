import streamlit as st
import pandas as pd
import yfinance as yf
import random

# --- 設定網頁配置 ---
st.set_page_config(page_title="台股AI選股系統 (即時版)", layout="wide")

# --- 1. 核心功能：抓取真實股價 & 生成連結 ---
@st.cache_data(ttl=600) # 設定快取 600秒 (10分鐘)，避免每次重新整理都要重抓很久
def get_real_stock_data():
    # 定義要觀察的真實台股清單 (這裡列出 30 檔熱門股作為範例)
    # 注意：yfinance 的台股代號後面要加 ".TW"
    tickers_list = [
        "2330.TW", "2454.TW", "2317.TW", "2603.TW", "2609.TW", "2303.TW", 
        "2881.TW", "2882.TW", "1605.TW", "3231.TW", "2382.TW", "2357.TW",
        "3008.TW", "1101.TW", "3034.TW", "6669.TW", "2379.TW", "3037.TW",
        "2345.TW", "2412.TW", "2308.TW", "5871.TW", "2395.TW", "1513.TW",
        "2912.TW", "1216.TW", "6505.TW", "1301.TW", "2002.TW", "2891.TW"
    ]
    
    data = []
    
    # 顯示載入中的訊息 (因為抓真實資料需要時間)
    progress_text = "正在連線 Yahoo Finance 抓取最新股價，請稍候..."
    my_bar = st.progress(0, text=progress_text)
    
    total = len(tickers_list)
    
    for i, ticker in enumerate(tickers_list):
        # 更新進度條
        my_bar.progress((i + 1) / total, text=f"正在分析: {ticker} ({i+1}/{total})")
        
        try:
            # 抓取該股票資料 (近一年 history)
            stock = yf.Ticker(ticker)
            # 抓取 1 年歷史資料來畫圖
            hist = stock.history(period="1y") 
            
            if hist.empty:
                continue

            # 取得最新價格與相關資訊
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            
            # 計算今日漲跌幅
            daily_change_pct = ((current_price - prev_price) / prev_price) * 100
            
            # 整理走勢圖數據 (轉成 list)
            history_trend = hist['Close'].tolist()
            
            # --- 模擬 AI 預測部分 (因為沒有 API 能預測未來) ---
            predicted_growth = round(random.uniform(-10, 30), 2)
            
            # 評級邏輯
            rating = "一般"
            if predicted_growth > 15:
                rating = "強力推薦"
            elif predicted_growth > 5:
                rating = "買進"
            
            # 移除 .TW 以顯示乾淨的代號
            clean_code = ticker.replace(".TW", "")
            
            # 建立 Yahoo 股市連結
            yahoo_url = f"https://tw.stock.yahoo.com/quote/{ticker}"

            data.append({
                "代號": clean_code, # 顯示用的文字
                "URL": yahoo_url,   # 隱藏用的連結
                "目前股價": round(current_price, 2),
                "今日漲跌": daily_change_pct,
                "AI預測月漲幅": predicted_growth,
                "評級": rating,
                "近一年走勢": history_trend
            })
            
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            continue
            
    my_bar.empty() # 抓完後清空進度條
    return pd.DataFrame(data)

# --- 2. 介面設計 ---

st.title("📈 台股 AI 飆股快篩 (即時連線版)")

# 上方控制區
col1, col2 = st.columns([1, 5])

with col1:
    show_strong_only = st.checkbox("只顯示強力推薦", value=False)

with col2:
    if show_strong_only:
        st.caption("🔥 篩選模式：僅顯示 AI 預測高爆發股")
    else:
        st.caption("📋 監控模式：顯示熱門觀察名單 (資料來源：Yahoo Finance)")

# 獲取資料
df = get_real_stock_data()

# --- 3. 篩選與排序 ---

if show_strong_only:
    display_df = df[df["評級"] == "強力推薦"]
else:
    display_df = df

display_df = display_df.sort_values(by="AI預測月漲幅", ascending=False)

# --- 4. 表格顯示 (含超連結設定) ---

# 顏色邏輯函數
def color_numbers(row):
    styles = []
    trend_color = 'red' if row['今日漲跌'] > 0 else 'green'
    
    for col in row.index:
        if col == '目前股價':
            styles.append(f'color: {trend_color}; font-weight: bold;')
        elif col == 'AI預測月漲幅':
            p_color = 'red' if row[col] > 0 else 'green'
            styles.append(f'color: {p_color}')
        elif col == '今日漲跌':
            styles.append(f'color: {trend_color}')
        else:
            styles.append('')
    return styles

# 顯示表格
st.dataframe(
    display_df.style.apply(color_numbers, axis=1),
    use_container_width=True,
    height=800,
    hide_index=True,
    column_config={
        # 這裡設定超連結！
        "代號": st.column_config.LinkColumn(
            "股票代號 (點擊前往)", 
            display_text="https://tw.stock.yahoo.com/quote/(.*?)\.TW", # 這裡用正則表達式太複雜，我們改用簡單映射
            help="點擊前往 Yahoo 股市",
            validate="^https://",
            width="small"
        ),
        # 我們把 URL 欄位隱藏，但把它的內容映射到 "代號" 欄位
        # 為了更簡單，我們直接使用 LinkColumn 顯示 URL，並把顯示文字設為代號
        # 修正：Streamlit 的 LinkColumn 最簡單用法是把 Dataframe 的那一欄直接放網址，然後 display_text 放代號
        # 但因為我們分成了兩個欄位，這裡用一個技巧：
        
        "URL": st.column_config.LinkColumn(
            "股票代號 (點擊看詳情)",
            display_text="代號", # 告訴它去讀取 "代號" 這一欄的文字來顯示
            width="medium" 
        ),
        
        "目前股價": st.column_config.NumberColumn("目前股價", format="$%.2f"),
        "今日漲跌": st.column_config.NumberColumn("今日漲跌", format="%.2f%%"),
        "AI預測月漲幅": st.column_config.NumberColumn("預測月漲幅", format="%.2f%%"),
        "近一年走勢": st.column_config.LineChartColumn("近一年走勢", y_min=0, y_max=None),
    },
    # 只顯示我們想要的欄位，注意順序
    column_order=("URL", "目前股價", "今日漲跌", "AI預測月漲幅", "評級", "近一年走勢") 
)

st.markdown("---")
st.caption("資料來源：Yahoo Finance API (延遲報價) | 預測漲幅為演算法模擬測試用")
