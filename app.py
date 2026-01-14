import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yfinance as yf
import requests
import re

st.set_page_config(page_title="台股AI標股神探 (排序增強版)", layout="wide")

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

# --- 1. 擴充內建字典 (包含長榮航、聯成、康舒) ---
tw_stock_dict = {
    "台積電": "2330", "鴻海": "2317", "聯發科": "2454", "廣達": "2382", "富邦金": "2881",
    "國泰金": "2882", "中華電": "2412", "台達電": "2308", "聯電": "2303", "中信金": "2891",
    "長榮": "2603", "兆豐金": "2886", "日月光投控": "3711", "統一": "1216", "玉山金": "2884",
    "元大金": "2885", "華碩": "2357", "緯創": "3231", "大立光": "3008", "台塑": "1301",
    "南亞": "1303", "第一金": "2892", "合庫金": "5880", "台新金": "2887", "永豐金": "2890",
    "台化": "1326", "中鋼": "2002", "統一超": "2912", "和泰車": "2207", "上海商銀": "5876",
    "研華": "2395", "智邦": "2345", "光寶科": "2301", "台泥": "1101", "華城": "1519",
    "緯穎": "6669", "聯詠": "3034", "瑞昱": "2379", "台塑化": "6505", "長榮航": "2618", # 加入長榮航
    "華航": "2610", "陽明": "2609", "萬海": "2615", "亞泥": "1102", "遠東新": "1402",
    "遠傳": "4904", "台灣大": "3045", "中租-KY": "5871", "矽力*-KY": "6415", "欣興": "3037",
    "南亞科": "2408", "華新": "1605", "大聯大": "3702", "新光金": "2888", "彰銀": "2801",
    "開發金": "2883", "華南金": "2880", "臺企銀": "2834", "仁寶": "2324", "英業達": "2356",
    "宏碁": "2353", "微星": "2377", "技嘉": "2376", "佳世達": "2352", "京元電子": "2449",
    "奇鋐": "3017", "雙鴻": "3324", "士電": "1503", "中興電": "1513", "亞力": "1514",
    "東元": "1504", "大同": "2371", "億泰": "1616", "大亞": "1609", "宏達電": "2498",
    "友達": "2409", "群創": "3481", "聯成": "1313", "康舒": "6282", "鴻輝": "7769"
}

# 產業與趨勢資料 (省略部分以節省空間)
ticker_sector_map = {"2330": "Semi", "2603": "Ship", "2618": "Trans"} 
sector_trends = {
    "Semi": {"bull": "AI 晶片需求強勁。", "bear": "消費電子復甦慢。"},
    "Ship": {"bull": "紅海危機推升運價。", "bear": "新船運力投放過剩。"},
    "Trans": {"bull": "客運復甦票價高檔。", "bear": "燃油成本上升。"},
    "Default": {"bull": "資金輪動健康，法人進駐。", "bear": "產業前景不明，面臨修正。"}
}

# --- 2. 搜尋與驗證邏輯 (重大修正) ---

def search_yahoo_tw_native(query):
    """直接問 Yahoo 奇摩股市，最準確"""
    url = "https://tw.stock.yahoo.com/_td-stock/api/resource/AutocompleteService"
    try:
        r = requests.get(url, params={"query": query, "limit": 5}, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        data = r.json()
        results = data.get('data', {}).get('result', [])
        
        # 優先尋找完全匹配的名稱
        for res in results:
            if res.get('name') == query and res.get('exchange') in ['TAI', 'TWO']:
                suffix = ".TW" if res['exchange'] == 'TAI' else ".TWO"
                return f"{res['symbol']}{suffix}", res['name']

        # 如果沒有完全匹配，回傳第一個相關的台股
        for res in results:
            if res.get('exchange') in ['TAI', 'TWO']:
                suffix = ".TW" if res['exchange'] == 'TAI' else ".TWO"
                return f"{res['symbol']}{suffix}", res['name']
    except:
        pass
    return None, None

def validate_and_search(query):
    query = query.strip()
    
    # 1. 處理純數字 (代號)
    if query.isdigit():
        # 簡單過濾：台股代號通常是 4 碼 (上市櫃) 或 4-6 碼 (興櫃)
        if len(query) < 3: 
            return None, None, "代號太短"
            
        symbol = f"{query}.TW"
        # 驗證是否存在
        try:
            t = yf.Ticker(symbol)
            if not t.history(period='1d').empty:
                # 嘗試抓中文名
                name = tw_stock_dict.get(query) # 先查字典
                if not name:
                    # 沒名字就顯示代號
                    name = f"自選股-{query}" 
                return symbol, name, None
            
            # 試試上櫃
            symbol = f"{query}.TWO"
            t = yf.Ticker(symbol)
            if not t.history(period='1d').empty:
                name = tw_stock_dict.get(query, f"自選股-{query}")
                return symbol, name, None
                
            return None, None, "找不到此代號 (請確認是否上市櫃/興櫃)"
        except:
             return None, None, "連線錯誤"

    # 2. 處理文字 (股名) - 解決 "長榮航" 變 "長榮" 的問題
    
    # A. 優先：字典 "精確" 匹配 (Exact Match)
    if query in tw_stock_dict:
        return f"{tw_stock_dict[query]}.TW", query, None
        
    # B. 次要：Yahoo API 搜尋 (聯成、康舒 靠這個)
    symbol, name = search_yahoo_tw_native(query)
    if symbol:
        return symbol, name, None
        
    # C. 最後：字典 "模糊" 匹配 (只有當上面都找不到時才用)
    for name, code in tw_stock_dict.items():
        if query in name:
            return f"{code}.TW", name, None
            
    return None, None, "找不到此股票名稱"

# --- 3. 核心分析邏輯 ---
def analyze_stock_strategy(ticker_code, current_price, ma20, ma60):
    rating, color_class, predict_score = "觀察", "tag-hold", 50
    sector_key = ticker_sector_map.get(ticker_code, "Default")
    
    # 處理新股
    if ma60 is None:
        if ma20 and current_price > ma20: return "短多", "tag-buy", 60, f"🚀 <b>新股：</b>站上月線({ma20:.1f})，動能強。<br>⚠️ 波動大注意風險。"
        else: return "觀察", "tag-hold", 40, "👀 <b>新股：</b>資料不足算季線，建議觀察。"

    bias_20 = ((current_price - ma20) / ma20) * 100
    
    if current_price > ma20 and current_price > ma60 and bias_20 > 5:
        rating, color_class, predict_score = "強力推薦", "tag-strong", 90
        trend = sector_trends.get(sector_key, sector_trends["Default"])["bull"]
        reason = f"🔥 <b>技術：</b>站穩月季線，乖離 {bias_20:.1f}%。<br>🌍 <b>產業：</b>{trend}"
    elif current_price > ma20 and bias_20 > 0:
        rating, color_class, predict_score = "買進", "tag-buy", 70
        trend = sector_trends.get(sector_key, sector_trends["Default"])["bull"]
        reason = f"📈 <b>技術：</b>站上月線({ma20:.1f})，轉強。<br>🌍 <b>產業：</b>{trend}"
    elif current_price < ma20 and current_price < ma60:
        rating, color_class, predict_score = "避開", "tag-sell", 10
        trend = sector_trends.get(sector_key, sector_trends["Default"])["bear"]
        reason = f"⚠️ <b>技術：</b>跌破月季線，壓力大。<br>🌍 <b>產業：</b>{trend}"
    elif current_price < ma20:
        rating, color_class, predict_score = "賣出", "tag-sell", 30
        trend = sector_trends.get(sector_key, sector_trends["Default"])["bear"]
        reason = f"📉 <b>技術：</b>跌破月線({ma20:.1f})。<br>🌍 <b>產業：</b>{trend}"
    else:
        reason = "👀 <b>技術：</b>月線附近震盪。<br>🌍 <b>產業：</b>方向未明。"
        
    return rating, color_class, predict_score, reason

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
            if len(closes_list) < 5: continue
            
            current_price = closes_list[-1]
            prev_price = closes_list[-2]
            change_pct = ((current_price - prev_price) / prev_price) * 100
            ma20 = sum(closes_list[-20:]) / 20 if len(closes_list) >= 20 else None
            ma60 = sum(closes_list[-60:]) / 60 if len(closes_list) >= 60 else None
            clean_code = ticker.replace(".TW", "").replace(".TWO", "")
            
            rating, color_class, score, reason = analyze_stock_strategy(clean_code, current_price, ma20, ma60)
            
            # 置頂邏輯
            is_new = (ticker == st.session_state.last_added)
            final_sort_key = 9999 if is_new else score 
            ma20_disp = f"{ma20:.1f}" if ma20 else "-"

            rows.append({
                "code": clean_code, "name": current_map[ticker],
                "url": f"https://tw.stock.yahoo.com/quote/{ticker}",
                "price": current_price, "change": change_pct, "score": final_sort_key,
                "ma20_disp": ma20_disp, "rating": rating, "rating_class": color_class,
                "reason": reason, "trend": closes_list[-30:]
            })
        except: continue
    
    # 預設排序 (置頂優先，接著按分數)
    return sorted(rows, key=lambda x: x['score'], reverse=True)

# --- 5. 畫圖與介面 ---
def make_sparkline(data):
    if not data: return ""
    w, h = 100, 30
    min_v, max_v = min(data), max(data)
    if max_v == min_v: return ""
    pts = []
    for i, val in enumerate(data):
        x = (i / (len(data) - 1)) * w
        y = h - ((val - min_v) / (max_v - min_v)) * (h - 4) - 2
        pts.append(f"{x},{y}")
    c = "#dc3545" if data[-1] > data[0] else "#28a745"
    return f'<svg width="{w}" height="{h}" style="overflow:visible"><polyline points="{" ".join(pts)}" fill="none" stroke="{c}" stroke-width="2"/><circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="3" fill="{c}"/></svg>'

st.title("🚀 台股 AI 飆股神探")

with st.container():
    col_add, col_info = st.columns([2, 3])
    with col_add:
        with st.form(key='add_stock_form', clear_on_submit=True):
            col_in, col_btn = st.columns([3, 1])
            with col_in: query = st.text_input("新增監控", placeholder="輸入代號(3260)或名稱(長榮航)")
            with col_btn: submitted = st.form_submit_button("新增")
            
            if submitted and query:
                # 驗證輸入是否有包含無效字元 (例如 '3260O')
                if not query.isdigit() and re.search(r'\d+[a-zA-Z]', query):
                     st.error("代號格式錯誤 (請輸入純數字或中文名稱)")
                else:
                    symbol, name, err = validate_and_search(query)
                    if symbol:
                        if symbol in st.session_state.watch_list:
                            st.warning(f"{name} 已在清單中")
                        else:
                            st.session_state.watch_list[symbol] = name
                            st.session_state.last_added = symbol
                            st.success(f"已加入：{name}")
                            st.rerun()
                    else:
                        st.error(f"加入失敗：{err}")

    with col_info:
        st.info("💡 **功能更新**：支援點擊表頭排序！修正「長榮航」搜尋與「聯成/康舒」查找問題。")
        filter_strong = st.checkbox("🔥 只看強力推薦", value=False)

data_rows = process_stock_data()
if filter_strong: data_rows = [d for d in data_rows if d['rating'] == "強力推薦"]

# --- 6. HTML/JS 渲染 (含點擊排序功能) ---
html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: "Microsoft JhengHei", sans-serif; margin: 0; padding-bottom: 50px; }
    table { width: 100%; border-collapse: collapse; font-size: 15px; }
    
    /* 表頭樣式：加上游標手勢 */
    th { background: #f2f2f2; padding: 12px; text-align: left; position: sticky; top: 0; z-index: 10; border-bottom: 2px solid #ddd; cursor: pointer; user-select: none; }
    th:hover { background: #e6e6e6; }
    
    td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: middle; }
    tr { position: relative; z-index: 1; }
    tr:hover { background: #f8f9fa; z-index: 100; position: relative; }
    
    .up { color: #d62728; font-weight: bold; }
    .down { color: #2ca02c; font-weight: bold; }
    a { text-decoration: none; color: #0066cc; font-weight: bold; background: #f0f7ff; padding: 2px 6px; border-radius: 4px; }
    
    /* Tooltip */
    .tooltip-container { position: relative; display: inline-block; cursor: help; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 13px; transition: all 0.2s; }
    .tooltip-text { 
        visibility: hidden; width: 350px; background-color: #2c3e50; color: #fff; text-align: left; 
        border-radius: 8px; padding: 15px; position: absolute; z-index: 9999; 
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

<script>
function sortTable(n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("stockTable");
  switching = true;
  dir = "asc"; 
  while (switching) {
    switching = false;
    rows = table.rows;
    for (i = 1; i < (rows.length - 1); i++) {
      shouldSwitch = false;
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      
      // 獲取純文字內容 (去除 HTML 標籤)
      var xContent = x.textContent || x.innerText;
      var yContent = y.textContent || y.innerText;
      
      // 嘗試轉為數字比較 (針對價格、漲跌幅)
      var xNum = parseFloat(xContent.replace(/[^0-9.-]/g, ''));
      var yNum = parseFloat(yContent.replace(/[^0-9.-]/g, ''));

      if (dir == "asc") {
        if (!isNaN(xNum) && !isNaN(yNum)) {
            if (xNum > yNum) { shouldSwitch = true; break; }
        } else {
            if (xContent.toLowerCase() > yContent.toLowerCase()) { shouldSwitch = true; break; }
        }
      } else if (dir == "desc") {
        if (!isNaN(xNum) && !isNaN(yNum)) {
            if (xNum < yNum) { shouldSwitch = true; break; }
        } else {
            if (xContent.toLowerCase() < yContent.toLowerCase()) { shouldSwitch = true; break; }
        }
      }
    }
    if (shouldSwitch) {
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount ++;      
    } else {
      if (switchcount == 0 && dir == "asc") {
        dir = "desc";
        switching = true;
      }
    }
  }
}
</script>
</head>
<body>
<table id="stockTable">
    <thead>
        <tr>
            <th onclick="sortTable(0)">代號 ⬍</th>
            <th onclick="sortTable(1)">股名 ⬍</th>
            <th onclick="sortTable(2)">現價 ⬍</th>
            <th onclick="sortTable(3)">漲跌 ⬍</th>
            <th onclick="sortTable(4)">AI 評級 ⬍</th>
            <th>近三月走勢</th>
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
            <td class="{p_cls}">{row['price']:.1f} <span class="sub-text">({row['ma20_disp']})</span></td>
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
st.caption("資料來源：Yahoo Finance API | 點擊表頭可進行排序")
