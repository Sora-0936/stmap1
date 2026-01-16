import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 気象 3D Map (Light)", layout="wide")
st.title("☀️ 日本気象 3Dビジュアライザー (ライトモード)")

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
            'current': ['temperature_2m', 'precipitation', 'wind_speed_10m', 'wind_direction_10m'],
            'timezone': 'Asia/Tokyo'
        }
        try:
            res = requests.get(BASE_URL, params=params).json()
            curr = res['current']
            temp = curr['temperature_2m']
            
            # 明るい背景で映えるように色の彩度を調整
            norm_temp = max(0, min(1, (temp - 0) / 35))
            r = int(255 * norm_temp)
            g = int(50 + 100 * (1 - abs(norm_temp - 0.5) * 2)) # 少し鮮やかに
            b = int(255 * (1 - norm_temp))
            
            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 
                'Precipitation': curr['precipitation'],
                'WindSpeed': curr['wind_speed_10m'],
                'WindDir': curr['wind_direction_10m'],
                'color': [r, g, b, 220], # 透明度を少し下げてくっきりさせる
                'elevation': temp * 5000,
                'rain_radius': 5000 + (curr['precipitation'] * 5000)
            })
        except: continue
    return pd.DataFrame(weather_info)

# --- メイン処理 ---
region = st.sidebar.selectbox("表示エリア", ["全国", "九州"])
df = fetch_weather_data(region)

if not df.empty:
    # 1. 気温の柱
    column_layer = pdk.Layer(
        "ColumnLayer", data=df, get_position='[lon, lat]',
        get_elevation='elevation', radius=15000, get_fill_color='color', pickable=True
    )

    # 2. 雨の波紋（少し濃いめの青に変更）
    rain_layer = pdk.Layer(
        "ScatterplotLayer", data=df[df['Precipitation'] > 0],
        get_position='[lon, lat]', get_fill_color=[0, 100, 255, 120],
        get_radius='rain_radius'
    )

    # 3. 風向きの矢印（暗い色にして視認性を向上）
    df['icon'] = '↑' 
    wind_layer = pdk.Layer(
        "TextLayer", data=df, get_position='[lon, lat]',
        get_text='icon', get_size='WindSpeed', size_scale=2,
        get_angle='180 - WindDir',
        get_color=[50, 50, 50, 255], # グレー/黒系の矢印
        get_pixel_offset=[0, -30]
    )

    view_state = pdk.ViewState(
        latitude=df['lat'].mean(), longitude=df['lon'].mean(),
        zoom=4.5 if region == "全国" else 6.5, pitch=45
    )

    # マップスタイルを 'light' に変更
    st.pydeck_chart(pdk.Deck(
        map_style="light", 
        layers=[column_layer, rain_layer, wind_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{City}</b><br>気温: {Temperature}°C<br>降水: {Precipitation}mm"}
    ))

    st.write("### 観測データ一覧")
    st.dataframe(df[['City', 'Temperature', 'Precipitation', 'WindSpeed']], hide_index=True)

if st.button('🔄 データを更新'):
    st.cache_data.clear()
    st.rerun()
