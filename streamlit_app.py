import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

# --- ページ設定 ---
st.set_page_config(page_title="日本全国 気象 3D Map (Animated)", layout="wide")
st.title("☀️ 日本気象 3Dビジュアライザー (アニメーション版)")

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
            temp = res['current']['temperature_2m']
            
            # 色の計算
            norm_temp = max(0, min(1, (temp - 0) / 35))
            
            weather_info.append({
                'City': city, 'lat': coords[0], 'lon': coords[1],
                'Temperature': temp, 
                'Precipitation': res['current']['precipitation'],
                'WindSpeed': res['current']['wind_speed_10m'],
                'WindDir': res['current']['wind_direction_10m'],
                'color': [int(255 * norm_temp), 100, int(255 * (1 - norm_temp)), 220],
                # 札幌対策：氷点下でも柱が見えるよう、最低高さを設定 (例: temp+5度分を高さにする)
                'elevation': (temp + 10) * 3000, 
                'rain_radius': 5000 + (res['current']['precipitation'] * 5000)
            })
        except: continue
    return pd.DataFrame(weather_info)

region = st.sidebar.selectbox("表示エリア", ["全国", "九州"])
df = fetch_weather_data(region)

if not df.empty:
    # --- 3D カラムレイヤー (アニメーション付き) ---
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=18000,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
        # ここでアニメーションを設定 (高さが変わる時に1秒かける)
        transitions={
            "get_elevation": {"duration": 1000, "type": "interpolation"},
            "get_fill_color": {"duration": 1000, "type": "interpolation"}
        }
    )

    # 風向きテキストレイヤー
    df['icon'] = '↑'
    wind_layer = pdk.Layer(
        "TextLayer", data=df, get_position='[lon, lat]',
        get_text='icon', get_size='WindSpeed', size_scale=2,
        get_angle='180 - WindDir',
        get_color=[80, 80, 80, 255],
        get_pixel_offset=[0, -30],
        # 風向きもアニメーション
        transitions={"get_angle": 1000}
    )

    view_state = pdk.ViewState(
        latitude=df['lat'].mean(), longitude=df['lon'].mean(),
        zoom=4.5 if region == "全国" else 6.5, pitch=45
    )

    st.pydeck_chart(pdk.Deck(
        map_style="light",
        layers=[column_layer, wind_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{City}</b><br>気温: {Temperature}°C"}
    ))

if st.button('🔄 データを更新'):
    st.cache_data.clear()
    st.rerun()
