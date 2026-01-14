import streamlit as st
import pandas as pd
import random

# --- 設定網頁標題與排版 ---
st.set_page_config(page_title="台股 AI 預測神探", layout="wide")

# --- 1. 核心功能：製造模擬數據 (假裝這是 AI 算出來的) ---
# 為了教學，我們先用隨機亂數，之後可以換成真實股市資料
@st.cache_data
def get_stock_data():
    data = []
    # 定義一些常見的台股產業
    sectors = ['半導體', 'AI 概念', '航運股', '金融股', '生技醫療', '重電綠能']
    
    for i in range(100):
        # 模擬台股代碼 (例如 23xx, 30xx)
        stock_id = random.choice([23, 30, 49, 62, 99]) * 100 + random.randint(1, 99)
        stock_name = f"模擬個股-{stock_id}"
        
        # 模擬股價 (10元 ~ 1000元)
        price = round(random.uniform(10, 1000), 1)
        
        # 模擬 AI 預測的未來漲幅 (-10% 到 +30%)
        predicted_growth = round(random.uniform(-10, 30), 2)
        
        # 定義評級邏輯
        # 如果預測漲幅 > 15%，我們就標記為 "強力推薦"
        tag = "觀察"
        if predicted_growth > 15:
            tag = "🔥 強力推薦"
        elif predicted_growth > 5:
            tag = "💰 買進"
            
        data.append({
            "代號": str(stock_id),
            "名稱": stock_name,
            "產業": random.choice(sectors),
            "目前股價": price,
            "AI 預測月漲幅": predicted_growth, # 數字是用來排序的
            "評級": tag
        })
    
    # 轉成 DataFrame 表格格式
    return pd.DataFrame(data)

# --- 2. 介面設計開始 ---

st.title("🚀 台股 AI 飆股快篩系統")
st.markdown("### 預測未來 30 天強勢上漲名單")

# 讀取數據
df = get_stock_data()

# --- 3. 側邊欄與按鈕邏輯 ---
st.sidebar.header("控制台")

# 這裡是一個關鍵技巧：使用 session_state 記住按鈕有沒有被按過
if 'filter_on' not in st.session_state:
    st.session_state.filter_on = False

def toggle():
    st.session_state.filter_on = not st.session_state.filter_on

# 顯示按鈕
btn_label = "🔥 只看強力推薦股" if not st.session_state.filter_on else "🔄 顯示全部股票"
st.sidebar.button(btn_label, on_click=toggle, type="primary")

# --- 4. 篩選與顯示邏輯 ---

if st.session_state.filter_on:
    # 如果按鈕被按下，只篩選出評級是 "強力推薦" 的
    final_df = df[df["評級"] == "🔥 強力推薦"]
    st.sidebar.success(f"篩選完成！共找到 {len(final_df)} 檔飆股")
else:
    # 否則顯示全部
    final_df = df
    st.sidebar.info(f"目前顯示全部 {len(final_df)} 檔股票")

# 依照漲幅由大到小排序
final_df = final_df.sort_values(by="AI 預測月漲幅", ascending=False)

# --- 5. 美化表格顯示 ---
# 把漲幅那一欄變色：大於 0 紅色(漲)，小於 0 綠色(跌)
def color_surprise(val):
    color = 'red' if val > 0 else 'green'
    return f'color: {color}; font-weight: bold;'

st.dataframe(
    final_df.style.applymap(color_surprise, subset=['AI 預測月漲幅'])
    .format({"目前股價": "{:.1f}", "AI 預測月漲幅": "{:.2f}%"}),
    use_container_width=True,
    height=600
)
