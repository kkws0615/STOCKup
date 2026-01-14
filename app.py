import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import re  # 引入正規表示法，用來抓網頁標題

st.set_page_config(page_title="台股AI標股神探 (全能補完版)", layout="wide")

# --- 0. 初始化 ---
if 'watch_list' not in st.session_state:
    st.session_state.watch_list = {
        "2330.TW": "台積電", "2454.TW": "聯發科", "2317.TW": "鴻海", "2603.TW": "長榮",
        "2609.TW": "陽明",   "2303.TW": "聯電",   "2881.TW": "富邦金", "2882.TW": "國泰金",
        "1605.TW": "華新",   "3231.TW": "緯創",   "2382.TW": "廣達",   "2357.TW": "華碩",
        "3008.TW": "大立光", "1101.TW": "台泥",   "3034.TW": "聯詠",   "6669.TW": "緯穎",
        "2379.TW": "瑞昱",   "3037.TW": "欣興",   "2345.TW": "智邦",   "2412.TW": "中華電",
        "2308.TW": "台達電", "5871.TW": "中租-KY", "2395.TW": "研華",  "1513.TW": "中興電",
        "2912.TW": "統一超", "1216.TW": "統一",   "6505.TW": "台塑化", "1301.TW": "台塑",
        "2002.TW": "中鋼",   "2891.TW": "中信金"
    }

if 'last_added' not in st.session_state:
    st.session_state.last_added = ""

# --- 1. 內建字典 (常用股快速查) ---
tw_stock_dict = {
    "台積電": "2330", "鴻海": "2317", "聯發科": "2454", "廣達": "2382", "富邦金": "2881",
    "國泰金": "2882", "中華電": "2412", "台達電": "2308", "聯電": "2303", "中信金": "2891",
    "長榮": "2603", "兆豐金": "2886", "日月光投控": "3711", "統一": "1216", "玉山金": "2884",
    "元大金": "2885", "華碩": "2357", "緯創": "3231", "大立光": "3008", "台塑": "1301",
    "南亞": "1303", "第一金": "2892", "合庫金": "5880", "台新金": "2887", "永豐金": "2890",
    "台化": "1326", "中鋼": "2002", "統一超": "2912", "和泰車": "2207", "上海商銀": "5876",
    "研華": "2395", "智邦": "2345", "光寶科": "2301", "台泥": "1101", "華城": "1519",
    "緯穎": "6669", "聯詠": "3034", "瑞昱": "2379", "台塑化": "6505", "長榮航": "2618",
    "華航": "2610", "陽明": "2609", "萬海": "2615", "亞泥": "1102", "遠東新": "1402",
    "遠傳": "4904", "台灣大": "3045", "中租-KY": "5871", "矽力*-KY": "6415", "欣興": "3037",
    "南亞科": "2408", "華新": "1605", "大聯大": "3702", "新光金": "2888", "彰銀": "2801",
    "開發金": "2883", "華南金": "2880", "臺企銀": "2834", "仁寶": "2324", "英業達": "2356",
    "宏碁": "2353", "微星": "2377", "技嘉": "2376", "佳世達": "2352", "京元電子": "2449",
    "奇鋐": "3017", "雙鴻": "3324", "士電": "1503", "中興電": "1513", "亞力": "1514",
    "東元": "1504", "大同": "2371", "億泰": "1616", "大亞": "1609", "宏達電": "2498",
    "友達": "2409", "群創": "3481", "彩晶": "6116", "威盛": "2388", "力積電": "6770"
}

# 產業資料庫
ticker_sector_map = {
    "2330": "Semi", "2454": "Semi", "2303": "Semi", "3034": "Semi", "2379": "Semi",
    "2317": "AI_Hw", "3231": "AI_Hw", "2382": "AI_Hw", "6669": "AI_Hw", "2357": "AI_Hw",
    "2603": "Ship", "2609": "Ship", "2615": "Ship", "2618": "Trans", "2610": "Trans",
    "2881": "Fin", "2882": "Fin", "5871": "Fin", "2891": "Fin", "2887": "Fin",
    "1605": "Wire", "1513": "Power", "2308": "Power", "1616": "Wire",
    "2412": "Tel", "4904": "Tel"
}

sector_trends = {
    "Semi": {"bull": "AI 晶片需求強勁，先進製程產能滿載。", "bear": "消費性電子復甦緩慢，成熟製程競爭加劇。"},
    "AI_Hw": {"bull": "雲端伺服器資本支出擴大，出貨動能強勁。", "bear": "缺料問題緩解後，市場擔憂毛利遭到壓縮。"},
    "Ship": {"bull": "紅海危機推升運價，SCFI 指數維持高檔。", "bear": "全球新船運力大量投放，供需失衡壓力大。"},
    "Trans": {"bull": "客運復甦強勁，票價維持高檔，獲利創新高。", "bear": "燃油成本上升，且新機交付延遲影響運能。"},
    "Fin": {"bull": "投資收益回升，銀行利差維持穩健。", "bear": "避險成本居高不下，降息預期反覆干擾。"},
    "Power": {"bull": "強韌電網計畫持續釋單，綠能需求長線看好。", "bear": "原物料價格波動，短線漲多面臨估值修正。"},
    "Wire": {"bull": "台電強韌電網與銅價上漲雙重利多。", "bear": "銅價回檔，庫存跌價損失風險增加。"},
    "Default": {"bull": "資金輪動健康，具備題材吸引法人進駐。", "bear": "產業前景不明朗，資金撤出，面臨修正壓力。"}
}

# --- 2. 關鍵功能：網路爬蟲抓真名 ---
def scrape_yahoo_title(symbol):
    """
    這是一個爬蟲機器人，它會去 Yahoo 股市網頁看標題。
    網頁標題通常長這樣： "億泰(1616) - 個股走勢 - Yahoo奇摩股市"
    我們只要抓括號前面的字，就是正確中文名！
    """
    url = f"https://tw.stock.yahoo.com/quote/{symbol}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            # 尋找 <title>標籤
            match = re.search(r'<title>(.*?)\(', r.text)
            if match:
                return match.group(1).strip() # 回傳 "億泰"
    except:
        pass
    return None

def search_stock_robust(query):
    # 策略 1: 查內建字典 (秒殺台新金、長榮航)
    for name, code in tw_stock_dict.items():
        if query in name or name in query:
            return f"{code}.TW", name
            
    # 策略 2: 輸入的是數字 (處理 1616)
    if query.isdigit():
        symbol = f"{query}.TW"
        
        # A. 先確認這支股票存在
        try:
            ticker = yf.Ticker(symbol)
            if ticker.history(period='1d').empty:
                # 試試看上櫃 (.TWO)
                symbol = f"{query}.TWO"
                ticker = yf.Ticker(symbol)
                if ticker.history(period='1d').empty:
                    return None, None
        except:
            return None, None
            
        # B. 股票存在，開始抓中文名
        # 先試圖從字典找 (也許有遺漏)
        # 再用爬蟲去 Yahoo 網頁抓 (必殺技)
        chinese_name = scrape_yahoo_title(symbol)
        
        if chinese_name:
            return symbol, chinese_name
        else:
            return symbol, f"自選股-{query}" # 真的抓不到才用這個

    return None, None

# --- 3. 核心邏輯 (分析策略) ---
def analyze_stock_strategy(ticker_code, current_price, ma20, ma60, trend_list):
    bias_20 = ((current_price - ma20) / ma20) * 100
    rating, color_class, predict_score, reason = "觀察", "tag-hold", 50, ""
    
    sector_key = ticker_sector_map.get(ticker_code, "Default")
    
    if current_price > ma20 and current_price > ma60 and bias_20 > 5:
        rating, color_class, predict_score = "強力推薦", "tag-strong", 90
        trend_desc = sector_trends.get(sector_key, sector_trends["Default"])["bull"]
        reason = f"🔥 <b>技術面：</b>強勢站穩月線({ma20:.1f})，乖離率 {bias_20:.1f}%。<br>🌍 <b>產業面：</b>{trend_desc}"
    elif current_price > ma20 and bias_20 > 0:
        rating, color_class, predict_score = "買進", "tag-buy", 70
        trend_desc = sector_trends.get(sector_key, sector_trends["Default"])["bull"]
        reason = f"📈 <b>技術面：</b>站上月線支撐({ma20:.1f})，短線轉強。<br>🌍 <b>產業面：</b>{trend_desc}"
    elif current_price < ma20 and current_price < ma60:
        rating, color_class, predict_score = "避開", "tag-sell", 10
        trend_desc = sector_trends.get(sector_key, sector_trends["Default"])["bear"]
        reason = f"⚠️ <b>技術面：</b>跌破月季線，上方壓力大。<br>🌍 <b>產業面：</b>{trend_desc}"
    elif current_price < ma20:
        rating, color_class, predict_score = "賣出", "tag-sell", 30
        trend_desc = sector_trends.get(sector_key, sector_trends["Default"])["bear"]
        reason = f"📉 <b>技術面：</b>跌破月線({ma20:.1f})，動能轉弱。<br>🌍 <b>產業面：</b>{trend_desc}"
    else:
        reason = f"👀 <b>技術面：</b>月線({ma20:.1f})附近震盪。<br>🌍 <b>產業面：</b>多空消息紛雜，等待方向。"
    return rating, color_class, reason, predict_score

# --- 4. 資料處理 ---
@st.cache_data(ttl=300) 
def fetch_stock_data_wrapper(tickers):
    if not tickers: return None
    return yf.download(tickers, period="6mo", group_by='ticker', progress=False)

def process_stock_data():
    current_map = st.session_state.watch_list
    tickers = list(current_map.keys())
    with st.spinner(f'AI 正在計算 {len(tickers)} 檔個股數據...'):
        data_download = fetch_stock_data_wrapper(tickers)
    
    rows = []
    if data_download is None or len(tickers) == 0: return []
    for ticker in tickers:
        try:
            if len(tickers) == 1: df_stock = data_download
            else: df_stock = data_download[ticker]
            closes = df_stock['Close']
            if isinstance(closes, pd.DataFrame): closes = closes.iloc[:, 0]
            closes_list = closes.dropna().tolist()
            if len(closes_list) < 60: continue
            
            current_price = closes_list[-1]
            prev_price = closes_list[-2]
            daily_change_pct = ((current_price - prev_price) / prev_price) * 100
            ma20 = sum(closes_list[-20:]) / 20
            ma60 = sum(closes_list[-60:]) / 60
            clean_code = ticker.replace(".TW", "").replace(".TWO", "")
            
            rating, color_class, reason, score = analyze_stock_strategy(
                clean_code, current_price, ma20, ma60, closes_list[-10:]
            )
            
            is_new = (ticker == st.session_state.last_added)
            final_sort_key = 9999 if is_new else score 

            rows.append({
                "code": clean_code, "name": current_map[ticker],
                "url": f"https://tw.stock.yahoo.com/quote/{ticker}",
                "price": current_price, "change": daily_change_pct, 
                "score": final_sort_key,
                "ma20": ma20, "rating": rating, "rating_class": color_class,
                "reason": reason, "trend": closes_list[-30:]
            })
        except: continue
    return sorted(rows, key=lambda x: x['score'], reverse=True)

# --- 5. 畫圖 ---
def make_sparkline(data):
    if not data: return ""
    width, height = 100, 30
    min_val, max_val = min(data), max(data)
    if max_val == min_val: return ""
    points = []
    for i, val in enumerate(data):
        x = (i / (len(data) - 1)) * width
        y = height - ((val - min_val) / (max_val - min_val)) * (height - 4) - 2
        points.append(f"{x},{y}")
    color = "#dc3545" if data[-1] > data[0] else "#28a745"
    return f'<svg width="{width}" height="{height}" style="overflow:visible"><polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/><circle cx="{points[-1].split(",")[0]}" cy="{points[-1].split(",")[1]}" r="3" fill="{color}"/></svg>'

# --- 6. 介面 ---
st.title("🚀 台股 AI 飆股神探")

with st.container():
    col_add, col_info = st.columns([2, 3])
    with col_add:
        with st.form(key='add_stock_form', clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            with col_input: 
                search_query = st.text_input("新增監控", placeholder="輸入：台新金 或 1616")
            with col_btn: 
                submitted = st.form_submit_button("搜尋加入")
            
            if submitted and search_query:
                # 呼叫全能搜尋
                symbol, name = search_stock_robust(search_query)
                
                if symbol:
                    if symbol in st.session_state.watch_list:
                        st.warning(f"{name} ({symbol}) 已經在清單中了！")
                    else:
                        st.session_state.watch_list[symbol] = name
                        st.session_state.last_added = symbol
                        st.success(f"已加入：{name} ({symbol})")
                        st.rerun()
                else:
                    st.error(f"找不到「{search_query}」，請確認是否為有效台股。")

    with col_info:
        st.info("💡 **全能搜尋**：輸入 **「台新金」** 會查字典，輸入 **「1616」** 會自動爬蟲抓取中文名「億泰」！")
        filter_strong = st.checkbox("🔥 只看強力推薦", value=False)

data_rows = process_stock_data()
if filter_strong: data_rows = [d for d in data_rows if d['rating'] == "強力推薦"]

# --- 7. HTML 渲染 ---
html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: "Microsoft JhengHei", sans-serif; margin: 0; padding-bottom: 50px; }
    table { width: 100%; border-collapse: collapse; font-size: 15px; }
    th { background: #f2f2f2; padding: 12px; text-align: left; position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #ddd; }
    td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: middle; }
    tr { position: relative; z-index: 1; }
    tr:hover { background: #f8f9fa; z-index: 100; position: relative; }
    
    .up { color: #d62728; font-weight: bold; }
    .down { color: #2ca02c; font-weight: bold; }
    a { text-decoration: none; color: #0066cc; font-weight: bold; background: #f0f7ff; padding: 2px 6px; border-radius: 4px; }
    
    .tooltip-container { position: relative; display: inline-block; cursor: help; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 13px; transition: all 0.2s; }
    .tooltip-container:hover { transform: scale(1.05); }
    .tooltip-text { 
        visibility: hidden; width: 350px; background-color: #2c3e50; color: #fff; 
        text-align: left; border-radius: 8px; padding: 15px; position: absolute; z-index: 9999; 
        bottom: 140%; left: 50%; margin-left: -175px; opacity: 0; transition: opacity 0.3s; 
        font-weight: normal; font-size: 14px; line-height: 1.6; pointer-events: none; 
        box-shadow: 0 5px 15px rgba(0,0,0,0.5);
    }
    .tooltip-text::after { content: ""; position: absolute; top: 100%; left: 50%; margin-left: -6px; border-width: 6px; border-style: solid; border-color: #2c3e50 transparent transparent transparent; }
    .tooltip-container:hover .tooltip-text { visibility: visible; opacity: 1; }

    tr:nth-child(-n+3) .tooltip-text { bottom: auto; top: 140%; }
    tr:nth-child(-n+3) .tooltip-text::after { top: auto; bottom: 100%; border-color: transparent transparent #2c3e50 transparent; }

    .tag-strong { background: #ffebeb; color: #d62728; border: 1px solid #ffcccc; }
    .tag-buy { background: #e6ffe6; color: #2ca02c; border: 1px solid #ccffcc; }
    .tag-sell { background: #f1f3f5; color: #495057; border: 1px solid #dee2e6; }
    .tag-hold { background: #fff; color: #868e96; border: 1px solid #eee; }
    .sub-text { font-size: 12px; color: #888; margin-left: 5px; font-weight: normal; }
</style>
</head>
<body>
<table>
    <thead>
        <tr>
            <th>代號</th><th>股名</th><th>現價 <span style="font-size:12px;color:#888">(月線)</span></th><th>漲跌</th><th>AI 評級 (懸停)</th><th>近三月走勢</th>
        </tr>
    </thead>
    <tbody>
"""

for row in data_rows:
    p_cls = "up" if row['change'] > 0 else "down"
    html_content += f"""
        <tr>
            <td><a href="{row['url']}" target="_blank">{row['code']}</a></td>
            <td>{row['name']}</td>
            <td class="{p_cls}">{row['price']:.1f} <span class="sub-text">({row['ma20']:.1f})</span></td>
            <td class="{p_cls}">{row['change']:.2f}%</td>
            <td>
                <div class="tooltip-container {row['rating_class']}">
                    {row['rating']}
                    <span class="tooltip-text">{row['reason']}</span>
                </div>
            </td>
            <td>{make_sparkline(row['trend'])}</td>
        </tr>
    """

html_content += "</tbody></table></body></html>"
components.html(html_content, height=800, scrolling=True)

st.markdown("---")
st.caption("資料來源：Yahoo Finance API")
