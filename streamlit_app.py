import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 気温 3D Map", layout="wide")
st.title("日本の現在の気温 3Dカラムマップ")

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
    fetch_time = None
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in CITIES[region].items():
        params = {
            'latitude': coords[0], 'longitude': coords[1],
            'current': ['temperature_2m', 'precipitation', 'wind_speed_10m'],
            'timezone': 'Asia/Tokyo'
        }
        try:
            res = requests.get(BASE_URL, params=params).json()
            curr = res['current']
            temp = curr['temperature_2m']
            
            if fetch_time is None:
                fetch_time = datetime.fromisoformat(curr['time']).strftime('%Y/%m/%d %H:%M')

            # --- 気温による色分け ---
            if temp >= 30:
                color = [128, 0, 128, 200]  # 紫
            elif temp >= 20:
                color = [255, 165, 0, 200]  # オレンジ
            elif temp >= 10:
                color = [154, 205, 50, 200] # 黄緑
            elif temp > 0:
                color = [0, 191, 255, 200]  # 水色
            else:
                color = [0, 0, 255, 200]    # 青 (0度以下)

            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 
                'Precipitation': curr['precipitation'],
                'WindSpeed': curr['wind_speed_10m'],
                'color': color,
                'elevation': max(0, temp * 5000) # 0度以下は高さ0
            })
        except: continue
    return pd.DataFrame(weather_info), fetch_time

# --- メイン処理 ---
region = st.sidebar.selectbox("表示エリア", ["全国", "九州"])
df, last_updated = fetch_weather_data(region)

if not df.empty:
    st.caption(f"計測時刻: {last_updated}")

    # データを気温（0度超 / 0度以下）で分割
    warm_df = df[df['Temperature'] > 0]
    cold_df = df[df['Temperature'] <= 0]

    layers = []

    # 1. 気温が0度より高い場合：3Dの柱
    if not warm_df.empty:
        layers.append(pdk.Layer(
            "ColumnLayer", 
            data=warm_df, 
            get_position='[lon, lat]',
            get_elevation='elevation', 
            radius=15000, 
            get_fill_color='color', 
            pickable=True
        ))

    # 2. 気温が0度以下の場合：平らな青い円
    if not cold_df.empty:
        layers.append(pdk.Layer(
            "ScatterplotLayer", 
            data=cold_df, 
            get_position='[lon, lat]',
            get_fill_color='color', 
            get_radius=15000, 
            pickable=True
        ))

    st.subheader("3D カラムマップ")
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(), longitude=df['lon'].mean(),
        zoom=4.5 if region == "全国" else 6.5, pitch=45
    )

    # ツールチップに風速(WindSpeed)を追加
    st.pydeck_chart(pdk.Deck(
        map_style="light", 
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": """
                <b>{City}</b><br>
                気温: {Temperature}°C<br>
                降水: {Precipitation}mm<br>
                風速: {WindSpeed}km/h
            """,
            "style": {"color": "white"}
        }
    ))

    st.write("### 取得したデータ")
    st.dataframe(df[['City', 'Temperature', 'Precipitation', 'WindSpeed']], hide_index=True)

if st.button('データを更新'):
    st.cache_data.clear()
    st.rerun()
