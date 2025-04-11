import streamlit as st
import googlemaps
import folium
from streamlit_folium import st_folium
from datetime import timedelta
from haversine import haversine

# Google Maps API Anahtarınızı girin
gmaps = googlemaps.Client(key="AIzaSyDwQVuPcON3rGSibcBrwhxQvz4HLTpF9Ws")

st.set_page_config("Montaj Rota Planlayıcı", layout="wide")
st.title("🛠️ Montaj Rota Planlayıcı")

# GLOBAL Sabitler
SAATLIK_ISCILIK = st.sidebar.number_input("Saatlik İşçilik Ücreti (TL)", value=500, min_value=100)
benzin_fiyati = st.sidebar.number_input("Benzin Fiyatı (TL/L)", 10.0)
km_basi_tuketim = st.sidebar.number_input("Km Başına Tüketim (L/km)", 0.1)
siralama_tipi = st.sidebar.radio("Rota Sıralama Tipi", ["Önem Derecesi", "En Kısa Rota"])

# Session Init
if "ekipler" not in st.session_state:
    st.session_state.ekipler = {}
if "aktif_ekip" not in st.session_state:
    st.session_state.aktif_ekip = None
if "sehirler" not in st.session_state:
    st.session_state.sehirler = []
if "baslangic_konum" not in st.session_state:
    st.session_state.baslangic_konum = None

# Ekip Yönetimi
st.sidebar.subheader("👷 Ekip Yönetimi")
ekip_adi = st.sidebar.text_input("Yeni Ekip Adı")
if st.sidebar.button("➕ Ekip Oluştur") and ekip_adi:
    if ekip_adi not in st.session_state.ekipler:
        st.session_state.ekipler[ekip_adi] = {"members": []}
        st.session_state.aktif_ekip = ekip_adi
aktif_secim = st.sidebar.selectbox("Aktif Ekip Seç", list(st.session_state.ekipler.keys()))
st.session_state.aktif_ekip = aktif_secim

# Üye Ekle
with st.sidebar.expander("👤 Ekip Üyeleri"):
    uye_adi = st.text_input("Yeni Üye Adı")
    if st.button("✅ Üye Ekle") and uye_adi:
        if st.session_state.aktif_ekip:
            st.session_state.ekipler[st.session_state.aktif_ekip]["members"].append(uye_adi)
        else:
            st.session_state.ekipler[st.session_state.aktif_ekip] = {"members": [uye_adi]}
    for i, uye in enumerate(st.session_state.ekipler[st.session_state.aktif_ekip].get("members", [])):
        st.markdown(f"- {uye}")

# Başlangıç Adresi Girişi
st.sidebar.subheader("📍 Başlangıç Noktası")
adres_input = st.sidebar.text_input("Başlangıç Noktasını Girin", st.session_state.baslangic_konum if st.session_state.baslangic_konum else "")
if st.sidebar.button("✅ Başlangıç Noktasını Güncelle"):
    if adres_input:
        try:
            sonuc = gmaps.geocode(adres_input)
            if sonuc:
                st.session_state.baslangic_konum = sonuc[0]["geometry"]["location"]
                st.sidebar.success("Başlangıç noktası başarıyla güncellendi.")
            else:
                st.sidebar.error("Adres bulunamadı.")
        except:
            st.sidebar.error("API Hatası.")
else:
    st.sidebar.warning("Başlangıç noktası henüz girilmedi.")

# Şehir/Bayi Ekleme
st.subheader("📌 Şehir Ekle")
with st.form("sehir_form"):
    sehir_adi = st.text_input("Şehir / Bayi Adı")
    onem = st.slider("Önem Derecesi", 1, 5, 3)
    is_suresi = st.number_input("Montaj Süresi (saat)", 1, 24, 2)
    ekle_btn = st.form_submit_button("➕ Şehir Ekle")
    if ekle_btn:
        sonuc = gmaps.geocode(sehir_adi)
        if sonuc:
            konum = sonuc[0]["geometry"]["location"]
            st.session_state.sehirler.append({
                "sehir": sehir_adi,
                "konum": konum,
                "onem": onem,
                "is_suresi": is_suresi
            })
            st.success(f"{sehir_adi} eklendi.")
        else:
            st.error("Konum bulunamadı.")

# Rota ve Hesaplama
if st.session_state.baslangic_konum and st.session_state.sehirler:
    baslangic = st.session_state.baslangic_konum
    sehirler = st.session_state.sehirler.copy()

    # En Düşük Maliyetli Rota Hesaplama
    rota = [{"lat": baslangic["lat"], "lng": baslangic["lng"], "name": "Başlangıç"}]
    toplam_km = 0
    toplam_sure = 0
    toplam_iscilik = 0
    toplam_yakit = 0
    toplam_maliyet = 0

    # En kısa rota veya önem derecesine göre sıralama
    if siralama_tipi == "En Kısa Rota":
        # En yakın şehirleri sıralamak
        while sehirler:
            en_yakin_sehir = min(sehirler, key=lambda s: haversine(
                (rota[-1]["lat"], rota[-1]["lng"]), (s["konum"]["lat"], s["konum"]["lng"])))
            
            # Gidiş yolu mesafesi ve süre
            yol = gmaps.directions(
                (rota[-1]["lat"], rota[-1]["lng"]),
                (en_yakin_sehir["konum"]["lat"], en_yakin_sehir["konum"]["lng"]),
                mode="driving"
            )
            if yol:
                km = yol[0]["legs"][0]["distance"]["value"] / 1000
                sure_dk = yol[0]["legs"][0]["duration"]["value"] / 60
                yakit_maliyeti = km * km_basi_tuketim * benzin_fiyati
                montaj_suresi = en_yakin_sehir["is_suresi"] * SAATLIK_ISCILIK

                toplam_km += km
                toplam_sure += sure_dk
                toplam_yakit += yakit_maliyeti
                toplam_iscilik += montaj_suresi

                rota.append({
                    "lat": en_yakin_sehir["konum"]["lat"], 
                    "lng": en_yakin_sehir["konum"]["lng"], 
                    "name": en_yakin_sehir["sehir"]
                })  # Şehri rotaya ekle
                sehirler.remove(en_yakin_sehir)

    elif siralama_tipi == "Önem Derecesi":
        # Öncelikli şehirleri sıralamak
        sehirler = sorted(sehirler, key=lambda s: s["onem"])

        for sehir in sehirler:
            yol = gmaps.directions(
                (rota[-1]["lat"], rota[-1]["lng"]),
                (sehir["konum"]["lat"], sehir["konum"]["lng"]),
                mode="driving"
            )
            if yol:
                km = yol[0]["legs"][0]["distance"]["value"] / 1000
                sure_dk = yol[0]["legs"][0]["duration"]["value"] / 60
                yakit_maliyeti = km * km_basi_tuketim * benzin_fiyati
                montaj_suresi = sehir["is_suresi"] * SAATLIK_ISCILIK

                toplam_km += km
                toplam_sure += sure_dk
                toplam_yakit += yakit_maliyeti
                toplam_iscilik += montaj_suresi

                rota.append({
                    "lat": sehir["konum"]["lat"], 
                    "lng": sehir["konum"]["lng"], 
                    "name": sehir["sehir"]
                })  # Şehri rotaya ekle

    # Dönüş yolunu ekle
    yol = gmaps.directions(
        (rota[-1]["lat"], rota[-1]["lng"]),
        (baslangic["lat"], baslangic["lng"]),
        mode="driving"
    )
    if yol:
        km = yol[0]["legs"][0]["distance"]["value"] / 1000
        sure_dk = yol[0]["legs"][0]["duration"]["value"] / 60
        yakit_maliyeti = km * km_basi_tuketim * benzin_fiyati
        montaj_suresi = SAATLIK_ISCILIK  # Başlangıca dönüş için işçilik

        toplam_km += km
        toplam_sure += sure_dk
        toplam_yakit += yakit_maliyeti
        toplam_iscilik += montaj_suresi

    toplam_sure_td = timedelta(minutes=toplam_sure)
    toplam_maliyet = toplam_yakit + toplam_iscilik

    # Harita
    harita = folium.Map(location=[baslangic["lat"], baslangic["lng"]], zoom_start=6)
    for i in range(len(rota) - 1):
        folium.PolyLine(
            locations=[(rota[i]["lat"], rota[i]["lng"]), (rota[i + 1]["lat"], rota[i + 1]["lng"])],
            color="blue", weight=2.5, opacity=1
        ).add_to(harita)

    # Başlangıç noktasına işaretçi ekle
    folium.Marker(
        location=[baslangic["lat"], baslangic["lng"]],
        popup="Başlangıç Noktası",
        icon=folium.Icon(color="green")
    ).add_to(harita)

    # Her şehir için marker ekle ve maliyet bilgisi göster
    for sehir in rota[1:]:  # Başlangıç noktasını hariç tutarak ekliyoruz
        folium.Marker(
            location=[sehir["lat"], sehir["lng"]],
            popup=f"{sehir['name']}<br>İşçilik: {round(sehir['is_suresi'] * SAATLIK_ISCILIK, 2)} TL<br>Yakıt: {round(km * km_basi_tuketim * benzin_fiyati, 2)} TL"
        ).add_to(harita)

    st.subheader("🗺️ Rota Haritası")
    st_folium(harita, width=1000, height=600)

    st.markdown("---")
    st.subheader("📊 Rota Özeti")
    st.markdown(f"**Toplam Mesafe**: {round(toplam_km, 1)} km")
    st.markdown(f"**Toplam Süre**: {toplam_sure_td}")
    st.markdown(f"**Toplam Yakıt Maliyeti**: {round(toplam_yakit)} TL")
    st.markdown(f"**Toplam İşçilik Maliyeti**: {round(toplam_iscilik)} TL")
    st.markdown(f"**Toplam Maliyet**: {round(toplam_maliyet)} TL")

else:
    st.info("Lütfen başlangıç adresi ve en az 1 şehir girin.")
