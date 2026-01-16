import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 気温・降水量 3D Map", layout="wide")
st.title("🌡️× 💧 気温と降水量の複合ビジュアライザー")

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

# --- データ取得関数 ---
@st.cache_data(ttl=600)
def fetch_weather_data(region):
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in CITIES[region].items():
        params = {
            'latitude': coords[0], 'longitude': coords[1],
            'current': ['temperature_2m', 'precipitation'], # 降水量を追加
            'timezone': 'Asia/Tokyo'
        }
        try:
            res = requests.get(BASE_URL, params=params).json()
            temp = res['current']['temperature_2m']
            rain = res['current']['precipitation'] # mm単位
            
            # 色の計算 (気温)
            norm_temp = max(0, min(1, (temp - 0) / 35))
            r = int(255 * norm_temp)
            g = int(100 * (1 - abs(norm_temp - 0.5) * 2))
            b = int(255 * (1 - norm_temp))
            
            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 
                'Precipitation': rain,
                'Time': res['current']['time'],
                'color': [r, g, b, 200],
                'elevation': temp * 5000,
                # 雨量に応じた半径（最低5000、雨が降るほど大きく）
                'rain_radius': 5000 + (rain * 5000) 
            })
        except: continue
    return pd.DataFrame(weather_info)

# --- メイン処理 ---
df = fetch_weather_data(st.sidebar.selectbox("表示エリア", ["全国", "九州"]))

if not df.empty:
    st.sidebar.markdown(f"**最終更新:** \n{df['Time'].iloc[0]}")
    
    # --- レイヤー作成 ---
    # 1. 気温の3D柱
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=15000,
        get_fill_color='color',
        pickable=True,
    )

    # 2. 雨量の波紋（雨が降っている地点のみ表示）
    rain_df = df[df['Precipitation'] > 0]
    scatterplot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=rain_df,
        get_position='[lon, lat]',
        get_fill_color=[0, 191, 255, 150], # 水色
        get_radius='rain_radius',
        pickable=False,
    )

    # --- 描画 ---
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(), longitude=df['lon'].mean(),
        zoom=4.5 if len(df) > 10 else 6.5, pitch=50
    )

    st.pydeck_chart(pdk.Deck(
        map_style="dark",
        layers=[column_layer, scatterplot_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{City}</b><br>気温: {Temperature}°C<br>降水量: {Precipitation}mm",
            "style": {"color": "white"}
        }
    ))
    
    # データテーブルの表示
    st.write("### 現在の観測値詳細")
    st.table(df[['City', 'Temperature', 'Precipitation']])

if st.button('🔄 データを更新'):
    st.cache_data.clear()
    st.rerun()
