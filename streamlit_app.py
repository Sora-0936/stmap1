import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 リアルタイム気温 3D Map", layout="wide")

st.title("🌡️ 日本主要都市の現在気温 3Dビジュアライザー")

# --- 都市データ定義 ---
CITIES = {
    '全国': {
        'Sapporo': [43.0642, 141.3468], 'Sendai': [38.2682, 140.8694],
        'Tokyo': [35.6895, 139.6917], 'Nagoya': [35.1815, 136.9066],
        'Osaka': [34.6937, 135.5023], 'Hiroshima': [34.3853, 132.4553],
        'Fukuoka': [33.5904, 130.4017], 'Naha': [26.2124, 127.6809]
    },
    '九州': {
        'Fukuoka': [33.5904, 130.4017], 'Saga': [33.2494, 130.2974],
        'Nagasaki': [32.7450, 129.8739], 'Kumamoto': [32.7900, 130.7420],
        'Oita': [33.2381, 131.6119], 'Miyazaki': [31.9110, 131.4240],
        'Kagoshima': [31.5600, 130.5580]
    }
}

# --- サイドバー設定 ---
st.sidebar.header("表示設定")
target_region = st.sidebar.selectbox("表示エリアを選択", ["全国", "九州"])
# 地図スタイルを標準的なものに変更
map_style_choice = st.sidebar.selectbox("地図スタイル", ["Dark", "Light", "Road"])
style_dict = {
    "Dark": "dark",
    "Light": "light",
    "Road": "road"
}

# --- データ取得関数 ---
@st.cache_data(ttl=600)
def fetch_weather_data(region):
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    selected_cities = CITIES[region]
    
    for city, coords in selected_cities.items():
        params = {
            'latitude': coords[0],
            'longitude': coords[1],
            'current': 'temperature_2m',
            'timezone': 'Asia/Tokyo'
        }
        try:
            res = requests.get(BASE_URL, params=params).json()
            temp = res['current']['temperature_2m']
            
            # 色の計算 (0-35度で青〜赤にグラデーション)
            norm_temp = max(0, min(1, (temp - 0) / 35))
            r = int(255 * norm_temp)
            g = int(100 * (1 - abs(norm_temp - 0.5) * 2))
            b = int(255 * (1 - norm_temp))
            
            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 'Time': res['current']['time'],
                'color': [r, g, b, 200], 'elevation': temp * 5000 
            })
        except:
            continue
    return pd.DataFrame(weather_info)

# --- メイン処理 ---
df = fetch_weather_data(target_region)

if not df.empty:
    last_updated = datetime.fromisoformat(df['Time'].iloc[0]).strftime('%Y/%m/%d %H:%M')
    st.caption(f"最終更新: {last_updated}")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.write("### 🌡️ 気温順")
        st.dataframe(df[['City', 'Temperature']].sort_values('Temperature', ascending=False), hide_index=True)
        if st.button('🔄 データを更新'):
            st.cache_data.clear()
            st.rerun()

    with col2:
        view_state = pdk.ViewState(
            latitude=df['lat'].mean(),
            longitude=df['lon'].mean(),
            zoom=4.5 if target_region == "全国" else 6.5,
            pitch=50,
            bearing=0
        )

        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position='[lon, lat]',
            get_elevation='elevation',
            radius=15000 if target_region == "全国" else 10000,
            get_fill_color='color',
            pickable=True,
            auto_highlight=True,
        )

        # map_style を単純な文字列指定に変更
        st.pydeck_chart(pdk.Deck(
            map_style=style_dict[map_style_choice], 
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"html": "<b>{City}</b><br>気温: {Temperature}°C", "style": {"color": "white"}}
        ))
