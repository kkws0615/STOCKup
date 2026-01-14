import streamlit as st
import pandas as pd
import yfinance as yf
import random

# --- 設定網頁配置 ---
st.set_page_config(page_title="台股AI標股神探", layout="wide")

# --- 1. 核心功能：高速抓取股價 & AI 分析 ---
@st.cache_data(ttl=600)
def get_stock_data():
    # 定義清單 (代號, 股名)
    # 我們這裡列出 30 檔指標股，你可以自行擴充
    stocks_map = {
        "2330.TW": "台積電", "2454.TW": "聯發科", "2317.TW": "鴻海", "2603.TW": "長榮",
        "2609.TW": "陽明",   "2303.TW": "聯電",   "2881.TW": "富邦金", "2882.TW": "國泰金",
        "1605.TW": "華新",   "3231.TW": "緯創",   "2382.TW": "廣達",   "2357.TW": "華碩",
        "3008.TW": "大立光", "1101.TW": "台泥",   "3034.TW": "聯詠",   "6669.TW": "緯穎",
        "2379.TW": "瑞昱",   "3037.TW": "欣興",   "2345.TW": "智邦",   "2412.TW": "中華電",
        "2308.TW": "台達電", "5871.TW": "中租-KY", "2395.TW": "研華",  "1513.TW": "中興電",
        "2912.TW": "統一超", "1216.TW": "統一",   "6505.TW": "台塑化", "1301.TW": "台塑",
        "2002.TW": "中鋼",   "2891.TW": "中信金"
    }
    
    # AI 推薦理由庫 (模擬)
    reasons_bull = [
        "外資連五日買超，籌碼安定", 
        "季線翻揚向上，均線多頭排列", 
        "營收創歷史新高，動能強勁", 
        "主力吃貨明顯，量能溫和放大", 
        "突破下降趨勢線，打底完成"
    ]
    reasons_bear = [
        "高檔爆量長黑，主力出貨", 
        "跌破季線支撐，趨勢轉空", 
        "法人連續調節，籌碼鬆動", 
        "乖離率過大，面臨修正壓力", 
        "營收不如預期，短線利空"
    ]

    # === 高速批量下載 (Batch Download) ===
    # 這比迴圈快非常多，比較不會「沒反應」
    tickers = list(stocks_map.keys())
    
    # 顯示載入狀態
    with st.spinner('正在高速連線 Yahoo Finance 取得 30 檔即時報價...'):
        # 一次抓取所有股票的 1 年歷史資料
        data_download = yf.download(tickers, period="1y", group_by='ticker', progress=False)
    
    rows = []
    
    for ticker in tickers:
        try:
            # 取得該股票的 DataFrame
            df_stock = data_download[ticker]
            
            # 如果資料是空的 (可能是下市或代號錯誤)
            if df_stock.empty or len(df_stock) < 2:
                continue
            
            # 整理數據
            current_price = df_stock['Close'].iloc[-1]
            prev_price = df_stock['Close'].iloc[-2]
            
            # 處理 NaN 的情況
            if pd.isna(current_price) or pd.isna(prev_price):
                continue
                
            daily_change_pct = ((current_price - prev_price) / prev_price) * 100
            
            # 走勢圖數據 (處理 NaN 並轉為 list)
            trend_data = df_stock['Close'].dropna().tolist()
            
            # --- 模擬 AI 預測 ---
            predicted_growth = round(random.uniform(-10, 30), 2)
            
            # 決定評級與理由
            rating = "一般"
            reason_text = ""
            
            if predicted_growth > 15:
                rating = "強力推薦"
                # 理由加上 icon 讓畫面好看
                reason_text = f"🔥 強力訊號：{random.choice(reasons_bull)}，建議積極佈局。"
            elif predicted_growth > 5:
                rating = "買進"
                reason_text = f"📈 多方訊號：{random.choice(reasons_bull)}。"
            elif predicted_growth < -5:
                rating = "避開"
                reason_text = f"⚠️ 風險訊號：{random.choice(reasons_bear)}，建議觀望。"
            else:
                rating = "觀察"
                reason_text = f"👀 盤整訊號：區間震盪整理中，等待方向浮現。"

            # 準備連結
            yahoo_link = f"https://tw.stock.yahoo.com/quote/{ticker}"
            
            rows.append({
                "代號連結": yahoo_link, # 隱藏的連結
                "股名": stocks_map[ticker],
                "現價": current_price,
                "漲跌(%)": daily_change_pct,
                "預測漲幅": predicted_growth,
                "評級": rating,
                "AI分析詳情": reason_text, # 這欄位如果太長，瀏覽器會自動變成 hover 顯示
                "走勢圖": trend_data
            })
            
        except Exception as e:
            # 容錯處理，避免單一股票錯誤導致整個程式掛掉
            continue
            
    return pd.DataFrame(rows)

# --- 2. 介面設計 ---

st.title("🚀 台股 AI 飆股快篩")

col1, col2 = st.columns([1, 5])
with col1:
    # 大按鈕
    filter_strong = st.checkbox("🔥 只顯示強力推薦", value=False)
with col2:
    if filter_strong:
        st.info("已篩選出 AI 預測漲幅 > 15% 的強勢股！")
    else:
        st.info("顯示所有監控個股，滑鼠移至「AI 分析詳情」可看完整理由。")

# 讀取資料
df = get_stock_data()

# --- 3. 篩選與排序 ---

if filter_strong:
    final_df = df[df["評級"] == "強力推薦"]
else:
    final_df = df

# 排序
final_df = final_df.sort_values(by="預測漲幅", ascending=False)

# --- 4. 表格顯示 (使用最穩定的 dataframe) ---

# 顏色邏輯
def highlight_vals(row):
    styles = []
    # 根據漲跌變色
    color = 'red' if row['漲跌(%)'] > 0 else 'green'
    
    for col in row.index:
        if col in ['現價', '漲跌(%)', '預測漲幅']:
            styles.append(f'color: {color}; font-weight: bold;')
        elif col == 'AI分析詳情':
            styles.append('color: #555;') # 分析文字用深灰色
        else:
            styles.append('')
    return styles

st.dataframe(
    final_df.style.apply(highlight_vals, axis=1),
    use_container_width=True,
    height=800,
    hide_index=True,
    column_config={
        "代號連結": st.column_config.LinkColumn(
            "代號", 
            # 抓取網址中的數字顯示
            display_text="https://tw\.stock\.yahoo\.com/quote/(.*?)\.TW",
            width="small",
            help="點擊開啟 Yahoo 股市"
        ),
        "股名": st.column_config.TextColumn("股名", width="small"),
        "現價": st.column_config.NumberColumn("現價", format="$%.1f"),
        "漲跌(%)": st.column_config.NumberColumn("漲跌", format="%.2f%%"),
        "預測漲幅": st.column_config.NumberColumn("預測漲幅", format="%.2f%%"),
        "評級": st.column_config.TextColumn("評級", width="small"),
        
        # === 技巧在這裡 ===
        # 我們設定一個較小的寬度，這樣長文字就會變成 "..."
        # 使用者滑鼠移上去時，Streamlit/瀏覽器會自動顯示完整文字
        "AI分析詳情": st.column_config.TextColumn(
            "AI 分析理由 (滑鼠查看)", 
            width="medium", 
            help="AI 綜合技術面與籌碼面的簡評"
        ),
        
        "走勢圖": st.column_config.LineChartColumn(
            "近一年走勢", 
            width="medium",
            y_min=0
        )
    },
    # 設定欄位順序
    column_order=("代號連結", "股名", "現價", "漲跌(%)", "預測漲幅", "評級", "AI分析詳情", "走勢圖")
)

st.markdown("---")
st.caption("資料來源：Yahoo Finance API (即時連線)")
