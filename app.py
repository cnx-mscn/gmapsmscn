import streamlit as st
import pandas as pd
import folium
import googlemaps
from streamlit_folium import st_folium
from geopy.distance import geodesic
from folium.plugins import AntPath


st.set_page_config("Montaj Rota Planlayıcı", layout="wide")
st.title("🛠️ Montaj Rota Planlayıcı ve Maliyet Hesaplayıcı")

# Google Maps API Anahtarınızı buraya girin
api_key = "AIzaSyDwQVuPcON3rGSibcBrwhxQvz4HLTpF9Ws"  # API Anahtarınızı buraya ekleyin
gmaps = googlemaps.Client(key=api_key)

sehir_koordinatlari = {
    "Gebze": (40.8028, 29.4307),
    "İstanbul": (41.0082, 28.9784),
    "Ankara": (39.9208, 32.8541),
    "İzmir": (38.4192, 27.1287),
    "Konya": (37.8746, 32.4932),
    "Bursa": (40.1956, 29.0601),
    "Adana": (37.0000, 35.3213),
    "Antalya": (36.8969, 30.7133),
    "Samsun": (41.2867, 36.33),
    "Gaziantep": (37.0662, 37.3833),
}

sehir_listesi = list(sehir_koordinatlari.keys())

if "girisler" not in st.session_state:
    st.session_state.girisler = []

with st.sidebar:
    st.header("⚙️ Genel Ayarlar")
    ekip_sayisi = st.number_input("Ekip Sayısı", 1, 10, 2)
    yakit_tuketim = st.number_input("Araç Yakıt Tüketimi (L/100km)", 4.0, 20.0, 8.0)
    benzin_fiyati = st.number_input("Benzin Litre Fiyatı (TL)", 10.0, 100.0, 43.50)
    iscilik_saat_ucreti = st.number_input("İşçilik Saatlik Ücreti (TL)", 50, 1000, 150)
    baslangic_sehri = st.selectbox("Yola Çıkılacak Şehir", options=sehir_listesi, index=sehir_listesi.index("Gebze"))

st.subheader("➕ Şehir ve İş Ekleme")
with st.form("sehir_form"):
    col1, col2 = st.columns(2)
    with col1:
        secilen_sehir = st.selectbox("📍 Şehir Seç", options=sehir_listesi)
        secilen_ekip = st.selectbox("👷 Ekip Seç", [f"Ekip {i+1}" for i in range(ekip_sayisi)] )
        montaj_suresi = st.number_input("Montaj Süresi (saat)", 1, 72, 4)
    with col2:
        bayi_adi = st.text_input("🏢 Bayi Adı", placeholder="Örn: Konya Merkez")
        is_tanimi = st.text_area("📝 İş Tanımı", height=100)
        ek_maliyet = st.number_input("Ekstra Maliyet (TL)", 0, 100000, 0)

    gonder_btn = st.form_submit_button("✅ Şehri Ekle")

    if gonder_btn:
        if secilen_sehir and secilen_ekip:
            veri = {
                "Ekip": secilen_ekip,
                "Şehir": secilen_sehir,
                "Montaj Süresi": montaj_suresi,
                "Bayi": bayi_adi,
                "İş Tanımı": is_tanimi,
                "Ek Maliyet": ek_maliyet
            }
            st.session_state.girisler.append(veri)
            st.success(f"{secilen_sehir} şehri {secilen_ekip} için eklendi.")

st.divider()

if st.session_state.girisler:
    st.subheader("📋 Montaj Planı")
    df = pd.DataFrame(st.session_state.girisler)

    ekipler = df["Ekip"].unique()
    for ekip in ekipler:
        st.markdown(f"### 👷 {ekip}")
        ekip_df = df[df["Ekip"] == ekip].reset_index(drop=True)

        rota = [baslangic_sehri] + ekip_df["Şehir"].tolist()
        toplam_mesafe = 0
        yakit_maliyeti = 0
        mesafe_listesi = []

        for i in range(len(rota)-1):
            konum1 = sehir_koordinatlari[rota[i]]
            konum2 = sehir_koordinatlari[rota[i+1]]

            # Google Maps API ile mesafe ve rota bilgisi alalım
            directions = gmaps.directions(konum1, konum2, mode="driving", alternatives=False)
            if directions:
                mesafe = directions[0]['legs'][0]['distance']['value'] / 1000  # mesafeyi kilometre cinsinden alıyoruz
                mesafe_listesi.append(f"{rota[i]} → {rota[i+1]} = {mesafe:.1f} km")
                toplam_mesafe += mesafe
                yakit_maliyeti += (mesafe * yakit_tuketim / 100) * benzin_fiyati

        toplam_sure = ekip_df["Montaj Süresi"].sum()
        diger_maliyet = ekip_df["Ek Maliyet"].sum()
        iscilik_maliyeti = toplam_sure * iscilik_saat_ucreti
        toplam_maliyet = iscilik_maliyeti + yakit_maliyeti + diger_maliyet

        ekip_df["İşçilik Maliyeti"] = ekip_df["Montaj Süresi"] * iscilik_saat_ucreti
        ekip_df["Toplam Satır Maliyeti"] = ekip_df["İşçilik Maliyeti"] + ekip_df["Ek Maliyet"]

        st.dataframe(ekip_df.drop(columns=["İş Tanımı"]), use_container_width=True)

        with st.expander("📍 Mesafeler Arası Detaylar"):
            for m in mesafe_listesi:
                st.markdown(f"- {m}")

        st.markdown(f"**🧭 Toplam Mesafe:** {toplam_mesafe:.1f} km")
        st.markdown(f"**⛽ Yakıt Maliyeti:** {yakit_maliyeti:,.2f} TL")
        st.markdown(f"**🛠️ İşçilik Maliyeti:** {iscilik_maliyeti:,.2f} TL")
        st.markdown(f"**💰 Toplam Maliyet:** {toplam_maliyet:,.2f} TL")

        st.markdown("📍 Rota Haritası")
        m = folium.Map(location=sehir_koordinatlari[baslangic_sehri], zoom_start=6)
        koordinatlar = [sehir_koordinatlari[s] for s in rota]
        AntPath(locations=koordinatlar, color="blue").add_to(m)
        for i, sehir in enumerate(rota):
            folium.Marker(
                sehir_koordinatlari[sehir],
                popup=sehir,
                tooltip=f"{i+1}. {sehir}"
            ).add_to(m)
        st_folium(m, width=700, height=400)

else:
    st.info("Henüz şehir girilmedi.")
    try:
    directions = gmaps.directions(konum1, konum2, mode="driving", alternatives=False)
    if directions:
        st.write(directions)  # Yanıtı yazdırarak görsel çıktı alabilirsiniz
    else:
        st.error("Rota bulunamadı.")
except googlemaps.exceptions.ApiError as e:
    st.error(f"API Hatası: {e}")
except Exception as ex:
    st.error(f"Beklenmeyen bir hata oluştu: {ex}")

