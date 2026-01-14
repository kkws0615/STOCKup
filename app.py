import streamlit as st
import pandas as pd
import yfinance as yf
import random

# --- 設定網頁配置 ---
st.set_page_config(page_title="台股AI標股神探 (HTML修復版)", layout="wide")

# --- 1. 核心功能：抓取資料 (與之前相同) ---
@st.cache_data(ttl=600)
def get_stock_data():
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
    
    reasons_bull = ["外資連五日買超", "季線翻揚向上", "營收創歷史新高", "主力吃貨明顯", "突破下降趨勢線", "KD黃金交叉"]
    reasons_bear = ["高檔爆量長黑", "跌破季線支撐", "法人連續調節", "乖離率過大", "營收不如預期", "MACD死叉"]

    tickers = list(stocks_map.keys())
    
    # 批量下載數據
    with st.spinner('AI 正在連線交易所取得即時報價...'):
        try:
            data_download = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
        except:
            return []
    
    rows = []
    
    for ticker in tickers:
        try:
            df_stock = data_download[ticker]
            if df_stock.empty or len(df_stock) < 2: continue
            
            # 處理數據
            # 注意：新版 yfinance 有時回傳 Series 有時回傳 DataFrame，這裡做個防呆
            closes = df_stock['Close']
            if isinstance(closes, pd.DataFrame):
                closes = closes.iloc[:, 0] # 取第一欄
            
            closes_list = closes.dropna().tolist()
            if len(closes_list) < 2: continue
            
            current_price = closes_list[-1]
            prev_price = closes_list[-2]
            daily_change_pct = ((current_price - prev_price) / prev_price) * 100
            
            predicted_growth = round(random.uniform(-10, 30), 2)
            
            # 評級邏輯
            if predicted_growth > 15:
                rating = "強力推薦"
                color_class = "tag-strong"
                reason = f"🔥 強力理由：{random.choice(reasons_bull)}，且{random.choice(reasons_bull)}。"
            elif predicted_growth > 5:
                rating = "買進"
                color_class = "tag-buy"
                reason = f"📈 買進理由：{random.choice(reasons_bull)}。"
            elif predicted_growth < -5:
                rating = "避開"
                color_class = "tag-sell"
                reason = f"⚠️ 風險提示：{random.choice(reasons_bear)}。"
            else:
                rating = "觀察"
                color_class = "tag-hold"
                reason = f"👀 觀察理由：{random.choice(reasons_bear)}。"

            rows.append({
                "code": ticker.replace(".TW", ""),
                "name": stocks_map[ticker],
                "url": f"https://tw.stock.yahoo.com/quote/{ticker}",
                "price": current_price,
                "change": daily_change_pct,
                "predict": predicted_growth,
                "rating": rating,
                "rating_class": color_class,
                "reason": reason,
                "trend": closes_list[-30:] # 取最近 30 天畫圖
            })
        except Exception as e:
            continue
            
    return sorted(rows, key=lambda x: x['predict'], reverse=True)

# --- 2. 輔助功能：畫 SVG 走勢圖 ---
def make_sparkline_svg(data):
    if not data: return ""
    width = 120
    height = 40
    min_val = min(data)
    max_val = max(data)
    if max_val == min_val: return ""
    
    points = []
    for i, val in enumerate(data):
        x = (i / (len(data) - 1)) * width
        y = height - ((val - min_val) / (max_val - min_val)) * (height - 4) - 2 # 留一點邊距
        points.append(f"{x},{y}")
    
    polyline = " ".join(points)
    color = "#dc3545" if data[-1] > data[0] else "#28a745" # 台股紅漲綠跌
    fill_color = "#ffe6e6" if data[-1] > data[0] else "#e6ffe6"
    
    # 這裡回傳 SVG 程式碼
    return f"""
    <svg width="{width}" height="{height}" style="overflow: visible; vertical-align: middle;">
        <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2" />
        <circle cx="{points[-1].split(',')[0]}" cy="{points[-1].split(',')[1]}" r="3" fill="{color}" />
    </svg>
    """

# --- 3. 介面與 HTML 生成 (關鍵修改處) ---

st.title("🚀 台股 AI 飆股快篩 (互動 HTML 版)")

col1, col2 = st.columns([1, 5])
with col1:
    filter_strong = st.checkbox("🔥 只看強力推薦", value=False)
with col2:
    st.caption("操作說明：滑鼠移到 **「評級」** 上方可查看詳細原因 | 點擊 **代號** 可開啟 Yahoo 股市")

data_rows = get_stock_data()
if filter_strong:
    data_rows = [d for d in data_rows if d['rating'] == "強力推薦"]

# === 4. 建立完整的 HTML 字串 ===
# 我們把 CSS 和 HTML 放在一起，確保載入順序正確

# 1. 定義 CSS
html_code = """
<style>
    /* 讓表格好看的 CSS */
    .stock-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 14px;
    }
    .stock-table th {
        background-color: #f8f9fa;
        color: #495057;
        font-weight: 600;
        text-align: left;
        padding: 12px;
        border-bottom: 2px solid #dee2e6;
    }
    .stock-table td {
        padding: 12px;
        vertical-align: middle;
        border-bottom: 1px solid #dee2e6;
    }
    .stock-table tr:hover {
        background-color: #f1f3f5;
    }
    
    /* 漲跌顏色 */
    .text-up { color: #dc3545; font-weight: bold; }
    .text-down { color: #28a745; font-weight: bold; }
    
    /* 連結 */
    .stock-link {
        color: #007bff;
        text-decoration: none;
        font-weight: bold;
    }
    .stock-link:hover { text-decoration: underline; }

    /* === 這是你要的 Tooltip (懸停視窗) === */
    .tooltip-container {
        position: relative;
        display: inline-block;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    
    /* 浮出來的視窗 */
    .tooltip-container .tooltip-text {
        visibility: hidden;
        width: 200px;
        background-color: #333;
        color: #fff;
        text-align: left;
        border-radius: 6px;
        padding: 8px 12px;
        position: absolute;
        z-index: 100; /* 確保在最上層 */
        bottom: 125%; /* 顯示在上方 */
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
        font-weight: normal;
        line-height: 1.5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 小箭頭 */
    .tooltip-container .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
    
    /* 滑鼠移上去時顯示 */
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    
    /* 標籤顏色樣式 */
    .tag-strong { background-color: #ffe3e3; color: #c92a2a; border: 1px solid #ffa8a8; }
    .tag-buy { background-color: #eebefa; color: #862e9c; border: 1px solid #e599f7; } /* 買進改紫色區分 */
    .tag-sell { background-color: #d3f9d8; color: #2b8a3e; border: 1px solid #b2f2bb; }
    .tag-hold { background-color: #f8f9fa; color: #868e96; border: 1px solid #dee2e6; }

</style>

<table class="stock-table">
    <thead>
        <tr>
            <th>代號</th>
            <th>股名</th>
            <th>現價</th>
            <th>漲跌</th>
            <th>預測漲幅</th>
            <th>AI 評級 (懸停看原因)</th>
            <th>近30日走勢</th>
        </tr>
    </thead>
    <tbody>
"""

# 3. 用 Python 迴圈把資料填進 HTML
for row in data_rows:
    price_cls = "text-up" if row['change'] > 0 else "text-down"
    predict_cls = "text-up" if row['predict'] > 0 else "text-down"
    
    # 組合每一列
    html_code += f"""
        <tr>
            <td><a href="{row['url']}" target="_blank" class="stock-link">{row['code']}</a></td>
            <td>{row['name']}</td>
            <td class="{price_cls}">{row['price']:.1f}</td>
            <td class="{price_cls}">{row['change']:.2f}%</td>
            <td class="{predict_cls}">{row['predict']:.2f}%</td>
            <td>
                <div class="tooltip-container {row['rating_class']}">
                    {row['rating']}
                    <span class="tooltip-text">{row['reason']}</span>
                </div>
            </td>
            <td>{make_sparkline_svg(row['trend'])}</td>
        </tr>
    """

html_code += """
    </tbody>
</table>
"""

# === 5. 渲染輸出 (最重要的部分) ===
# unsafe_allow_html=True 是關鍵，一定要有
st.markdown(html_code, unsafe_allow_html=True)

st.write("")
st.markdown("---")
st.caption("資料來源：Yahoo Finance (延遲報價) | 技術架構：Raw HTML + SVG Rendering")
