import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from haversine import haversine

st.set_page_config(page_title="Montaj Rota Planlayıcı", layout="wide")
st.title("🛠️ Montaj Rota Planlayıcı")

# Sidebar ayarları
st.sidebar.header("🔧 Ayarlar")

baslangic_noktasi = st.sidebar.text_input("Başlangıç Noktası (Şehir)", "Gebze")
SAATLIK_ISCILIK = st.sidebar.number_input("Saatlik İşçilik Ücreti (TL)", min_value=100, value=500)
benzin_fiyati = st.sidebar.number_input("Benzin Fiyatı (TL/Litre)", min_value=1.0, value=43.0)
km_basi_tuketim = st.sidebar.number_input("Araç Tüketimi (Litre/km)", min_value=0.01, value=0.10)

st.sidebar.markdown("---")
st.sidebar.subheader("🧩 Şehir Ekle")

if "sehir_listesi" not in st.session_state:
    st.session_state.sehir_listesi = []

sehir_adi = st.sidebar.text_input("Şehir Adı")
is_suresi = st.sidebar.number_input("İş Süresi (saat)", min_value=0.0, value=2.0)
onem = st.sidebar.slider("Önem Derecesi", 1, 10, 5)
latitude = st.sidebar.number_input("Enlem (lat)", value=0.0)
longitude = st.sidebar.number_input("Boylam (lon)", value=0.0)

if st.sidebar.button("➕ Şehir Ekle"):
    if sehir_adi and latitude and longitude:
        st.session_state.sehir_listesi.append({
            "name": sehir_adi,
            "lat": latitude,
            "lon": longitude,
            "is_suresi": is_suresi,
            "onem": onem
        })

# Rota türü seçimi
rota_turu = st.radio("Rota Sıralama Kriteri", ["En Kısa Yol", "Önem Sırasına Göre"])

# Başlangıç konumu koordinatını bul
import requests
import urllib.parse

def adres_to_koordinat(adres):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(adres)}&format=json&limit=1"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        return 0.0, 0.0

baslangic_lat, baslangic_lon = adres_to_koordinat(baslangic_noktasi)

# Rota hesaplama
sehirler = st.session_state.sehir_listesi.copy()
rota = []
visited = set()
konum = (baslangic_lat, baslangic_lon)

def rota_optimize(sehirler, konum, kriter):
    rota = []
    ziyaret_edilen = set()
    while len(rota) < len(sehirler):
        kalanlar = [s for s in sehirler if s['name'] not in ziyaret_edilen]
        if not kalanlar:
            break

        if kriter == "En Kısa Yol":
            secilen = min(kalanlar, key=lambda s: haversine(konum, (s['lat'], s['lon'])))
        else:
            secilen = max(kalanlar, key=lambda s: s['onem'])

        rota.append(secilen)
        ziyaret_edilen.add(secilen['name'])
        konum = (secilen['lat'], secilen['lon'])

    return rota

rota = rota_optimize(sehirler, konum, rota_turu)

# Harita oluşturma
m = folium.Map(location=[baslangic_lat, baslangic_lon], zoom_start=6)
folium.Marker([baslangic_lat, baslangic_lon], tooltip="Başlangıç", icon=folium.Icon(color="green")).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

toplam_km = 0
toplam_yakit = 0
toplam_iscilik = 0
sehir_ozet_listesi = []

onceki_konum = (baslangic_lat, baslangic_lon)

for idx, sehir in enumerate(rota, start=1):
    konum = (sehir['lat'], sehir['lon'])
    km = haversine(onceki_konum, konum)
    sure = km / 80  # ortalama hız varsayımı

    yakit_maliyeti = km * km_basi_tuketim * benzin_fiyati
    iscilik_maliyeti = sehir['is_suresi'] * SAATLIK_ISCILIK
    toplam_maliyet = yakit_maliyeti + iscilik_maliyeti

    toplam_km += km
    toplam_yakit += yakit_maliyeti
    toplam_iscilik += iscilik_maliyeti

    folium.Marker(
        location=konum,
        tooltip=f"{idx}. {sehir['name']}",
        popup=f"{sehir['name']}<br>Süre: {round(sure, 2)} saat<br>Mesafe: {round(km, 1)} km<br>İşçilik: {round(iscilik_maliyeti)} TL<br>Yakıt: {round(yakit_maliyeti)} TL",
        icon=folium.DivIcon(html=f"<div style='font-size: 12pt; color: red'><b>{idx}</b></div>")
    ).add_to(marker_cluster)

    folium.PolyLine([onceki_konum, konum], color="blue", weight=2.5, tooltip=f"{round(km, 1)} km / {round(sure, 2)} saat").add_to(m)

    sehir_ozet_listesi.append({
        "Şehir": sehir['name'],
        "Mesafe (km)": round(km, 1),
        "Süre (saat)": round(sure, 2),
        "İşçilik (TL)": round(iscilik_maliyeti),
        "Yakıt (TL)": round(yakit_maliyeti),
        "Toplam Maliyet (TL)": round(toplam_maliyet)
    })

    onceki_konum = konum

# Geri dönüş
km_donus = haversine(onceki_konum, (baslangic_lat, baslangic_lon))
sure_donus = km_donus / 80
yakit_donus = km_donus * km_basi_tuketim * benzin_fiyati
toplam_km += km_donus
toplam_yakit += yakit_donus

folium.PolyLine([onceki_konum, (baslangic_lat, baslangic_lon)], color="gray", dash_array="5,5").add_to(m)

st.subheader("🗺️ Harita ve Rota")
st_data = st_folium(m, width=1000, height=600)

st.subheader("📋 Şehir Bazlı Maliyet Detayları")
st.table(sehir_ozet_listesi)

st.subheader("📊 Toplam Rota Özeti")
st.markdown(f"**Toplam Mesafe:** {round(toplam_km, 1)} km")
st.markdown(f"**Toplam Yakıt Maliyeti:** {round(toplam_yakit)} TL")
st.markdown(f"**Toplam İşçilik Maliyeti:** {round(toplam_iscilik)} TL")
st.markdown(f"**Toplam Maliyet:** {round(toplam_iscilik + toplam_yakit)} TL")
