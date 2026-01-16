import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 気象 3D Pro", layout="wide")

# --- 自動モード判定 (18時〜6時はダークモード) ---
current_hour = datetime.now().hour
is_night = current_hour >= 18 or current_hour < 6
default_map_style = "dark" if is_night else "light"
theme_icon = "🌙" if is_night else "☀️"

st.title(f"{theme_icon} 日本気象 3Dビジュアライザー (自動モード切替)")

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
            
            # 色の計算
            norm_temp = max(0, min(1, (temp - 0) / 35))
            r = int(255 * norm_temp)
            b = int(255 * (1 - norm_temp))
            
            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 
                'Precipitation': curr['precipitation'],
                'WindSpeed': curr['wind_speed_10m'],
                'WindDir': curr['wind_direction_10m'],
                'color': [r, 100, b, 200],
                'elevation': (temp + 15) * 2500, # 札幌等の氷点下対応
                'is_snow': temp < 0 and curr['precipitation'] > 0
            })
        except: continue
    return pd.DataFrame(weather_info)

region = st.sidebar.selectbox("表示エリア", ["全国", "九州"])
df = fetch_weather_data(region)

if not df.empty:
    # 1. 気温の柱 (アニメーション付)
    column_layer = pdk.Layer(
        "ColumnLayer", data=df, get_position='[lon, lat]',
        get_elevation='elevation', radius=18000, get_fill_color='color',
        pickable=True, auto_highlight=True,
        transitions={"get_elevation": 1000, "get_fill_color": 1000}
    )

    # 2. 雨/雪の表現 (Scatterplot)
    # 雪の場合は白、雨の場合は水色
    df['weather_color'] = df.apply(lambda x: [255, 255, 255, 200] if x['is_snow'] else [0, 150, 255, 150], axis=1)
    weather_layer = pdk.Layer(
        "ScatterplotLayer", data=df[df['Precipitation'] > 0],
        get_position='[lon, lat]', get_fill_color='weather_color',
        get_radius='5000 + Precipitation * 5000',
        transitions={"get_radius": 1000}
    )

    # 3. 風向き
    df['icon'] = '↑'
    wind_layer = pdk.Layer(
        "TextLayer", data=df, get_position='[lon, lat]',
        get_text='icon', get_size='WindSpeed', size_scale=2,
        get_angle='180 - WindDir',
        get_color=[200, 200, 200, 255] if is_night else [50, 50, 50, 255],
        get_pixel_offset=[0, -30],
        transitions={"get_angle": 1000}
    )

    view_state = pdk.ViewState(
        latitude=df['lat'].mean(), longitude=df['lon'].mean(),
        zoom=4.5 if region == "全国" else 6.5, pitch=45
    )

    st.pydeck_chart(pdk.Deck(
        map_style=default_map_style,
        layers=[column_layer, weather_layer, wind_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{City}</b><br>気温: {Temperature}°C<br>降水: {Precipitation}mm"}
    ))

st.sidebar.info(f"現在のモード: {'夜間モード' if is_night else '昼間モード'}\n(18時に自動切替)")

if st.button('🔄 データを最新に更新'):
    st.cache_data.clear()
    with st.spinner('更新中...'):
        time.sleep(0.5)
        st.rerun()
