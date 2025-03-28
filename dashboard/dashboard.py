import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import json
import requests
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from shapely.geometry import shape

# Load dataset 
url = 'https://raw.githubusercontent.com/alifinaaulia/proyek_analisis_data/refs/heads/main/dashboard/main_data.csv'
df = pd.read_csv(url)  


# Buat opsi dropdown state yang ada di dataset
selected_state = st.sidebar.selectbox("Pilih State", df["geolocation_state"].unique())

# Filter data berdasarkan kode state yang dipilih
df_filtered = df[df["geolocation_state"] == selected_state]


# Mengelompokkan data berdasarkan kota dan menghitung total revenue per kota
df_city_revenue = df_filtered.groupby("customer_city").agg({
    "price": "sum",  # Total revenue per kota
    "geolocation_lat": "first",  
    "geolocation_lng": "first"   
}).reset_index()

# Menentukan kota dengan revenue tertinggi
top_city = df_city_revenue.loc[df_city_revenue["price"].idxmax(), "customer_city"]

# Mengambil 10 kota teratas berdasarkan total revenue
df_top_cities = df_city_revenue.sort_values(by="price", ascending=False).head(10)

# Judul untuk dashboard Streamlit
st.title("Dashboard Analisis Penjualan dan Kategori Produk Terjual di E-Commerce Brazil")

# Menampilkan peta untuk total revenue per kota
st.subheader(f"Peta Penjualan per Kota di {selected_state}")
st.markdown("Peta ini menunjukkan total penjualan untuk 10 kota dengan revenue tertinggi di state yang dipilih.")
m = folium.Map(location=[-14.2350, -51.9253], zoom_start=5)

# Fungsi untuk menentukan warna berdasarkan level revenue
def get_color(revenue, max_revenue):
    if revenue > max_revenue * 0.75:
        return "darkgreen"
    elif revenue > max_revenue * 0.5:
        return "green"
    elif revenue > max_revenue * 0.25:
        return "yellow"
    else:
        return "orange"

max_revenue = df_top_cities["price"].max()

# Menambahkan marker untuk setiap kota
for _, row in df_top_cities.iterrows():
    folium.Marker(
        location=[row["geolocation_lat"], row["geolocation_lng"]],
        icon=folium.Icon(color=get_color(row["price"], max_revenue)),
        popup=f"{row['customer_city']}: BRL {row['price']:,.0f}"
    ).add_to(m)

# Menampilkan peta di Streamlit
folium_map = m
folium_static(m)


# Menyiapkan data waktu
df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
df["year_month"] = df["order_purchase_timestamp"].dt.to_period("M")

# Menambahkan filter kota di sidebar
city_options = df_filtered["customer_city"].unique()
selected_city = st.sidebar.selectbox("Pilih Kota", city_options, index=0)

# Menyiapkan data untuk MoM berdasarkan kota yang dipilih
df_mom = df[(df["customer_city"] == selected_city) & (df["order_purchase_timestamp"] < "2018-09-01")]
df_mom = df_mom.groupby("year_month")["price"].sum().reset_index()

# Menghitung Pertumbuhan MoM
df_mom["growth"] = df_mom["price"].pct_change() * 100
df_mom["year_month"] = df_mom["year_month"].astype(str)
df_mom_cleaned = df_mom.dropna(subset=["growth"]).reset_index(drop=True)

# Pastikan indeks tetap valid setelah filtering
df_mom_filtered = df_mom_cleaned[df_mom_cleaned["price"].shift(1) > 0].reset_index(drop=True)

# Menampilkan grafik Pertumbuhan MoM
st.subheader(f"Pertumbuhan Penjualan Bulanan (MoM) di {selected_city}")
st.markdown("Grafik ini menunjukkan pertumbuhan penjualan per bulan di kota yang dipilih.")
fig = plt.figure(figsize=(12, 6))
sns.lineplot(x="year_month", y="price", data=df_mom, marker="o", color="green")

# Menambahkan label untuk semua bulan
for idx in range(len(df_mom_filtered)):
    x_value = df_mom_filtered["year_month"].iloc[idx]  # Use actual x-axis value
    offset = 7000 if df_mom_filtered["growth"].iloc[idx] >= 0 else -7000  
    color = "blue" if df_mom_filtered["growth"].iloc[idx] >= 0 else "red"
    
    plt.text(x_value, df_mom_filtered["price"].iloc[idx] + offset, 
             f" {df_mom_filtered['growth'].iloc[idx]:.1f}%", 
             fontsize=10, ha="center", color=color, fontweight="bold")

plt.xticks(rotation=45)
plt.title(f"Pertumbuhan Penjualan MoM di {selected_city}", fontsize=14)
plt.xlabel("Bulan")
plt.ylabel("Total Revenue (BRL)")

# Menampilkan grafik di Streamlit
st.pyplot(fig)


# Menampilkan kategori produk terpopuler di kota yang dipilih selama periode pertumbuhan tertinggi
df_period = df[(df["customer_city"] == selected_city)]
top_categories = df_period.groupby("product_cat")["order_id"].nunique().reset_index()
top_categories = top_categories.sort_values(by="order_id", ascending=False)

# Grafik kategori produk
st.subheader(f"Kategori Produk Paling Banyak Dipesan di {selected_city}")
st.markdown("Grafik ini menunjukkan kategori produk yang paling banyak dipesan di kota yang dipilih.")
fig = plt.figure(figsize=(10, 5))
ax = sns.barplot(x=top_categories["order_id"].head(10), 
                 y=top_categories["product_cat"].head(10))

# Menambahkan label untuk setiap kategori produk
for p in ax.patches:
    ax.annotate(f'{int(p.get_width())}', 
                (p.get_width(), p.get_y() + p.get_height() / 2), 
                ha='left', va='center', fontsize=10, color='black', fontweight="bold")

st.pyplot(fig)


# Menampilkan peta produk terpopuler per negara bagian di Brasil
st.subheader("Peta Produk Paling Populer di Setiap Negara Bagian")
st.markdown("Peta ini menunjukkan produk dengan jumlah transaksi terbanyak di setiap negara bagian Brazil.")


# Mengelompokkan Data Berdasarkan Negara Bagian dan Kategori Produk
product_state_counts = df.groupby(['geolocation_state', 'product_cat'])['order_id'].nunique().reset_index(name='transaction_count')

# Menentukan produk dengan jumlah transaksi terbanyak untuk setiap negara bagian
top_product_per_state = product_state_counts.loc[product_state_counts.groupby('geolocation_state')['transaction_count'].idxmax()]

# Membuat peta dasar (peta Brazil)
m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4)  # Lokasi tengah Brazil

# Mendapatkan daftar kategori produk unik
unique_categories = top_product_per_state['product_cat'].unique()

# Menghasilkan warna unik untuk setiap kategori menggunakan colormap
colormap = plt.cm.get_cmap('viridis', len(unique_categories)) 
product_cat_colors = {cat: f'#{int(colormap(i)[0]*255):02x}{int(colormap(i)[1]*255):02x}{int(colormap(i)[2]*255):02x}' for i, cat in enumerate(unique_categories)}

geojson_url = 'https://raw.githubusercontent.com/alifinaaulia/proyek_analisis_data/main/dashboard/brazil_states.geojson'

# Mengunduh file GeoJSON
try:
    response = requests.get(geojson_url)
    response.raise_for_status()  # Memeriksa apakah ada error saat mengunduh
    geojson_data = response.json()  # Mengonversi respons JSON ke objek Python
except requests.exceptions.RequestException as e:
    st.error(f"Gagal mengunduh file GeoJSON: {e}")
    st.stop()

for feature in geojson_data['features']:
    state_code = feature['properties']['sigla'] 
    top_product = top_product_per_state[top_product_per_state['geolocation_state'] == state_code]
    
    if not top_product.empty:
        product_cat = top_product['product_cat'].values[0]
        transaction_count = top_product['transaction_count'].values[0]
        color = product_cat_colors.get(product_cat, 'grey') 

        # Menambahkan Choropleth layer
        folium.GeoJson(
            feature,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'fillOpacity': 0.7,
                'weight': 0.2,
                'color': 'black'
            },
            tooltip=folium.Tooltip(
                f"<strong>{state_code}</strong><br>"
                f"<i>Produk Terpopuler:</i> {product_cat}<br>"
                f"<i>Jumlah Transaksi:</i> {transaction_count} <br>"
            )
        ).add_to(m)

# Menyusun legenda dinamis
legend_html = '''
     <div style="position: absolute; 
                 bottom: 20px; left: 20px; width: 200px; height: auto; 
                 background-color: white; border:2px solid grey; 
                 z-index:50; font-size:12px;
                 padding: 10px;">
        <b>Product Category Legend</b><br>
'''

for cat, color in product_cat_colors.items():
    legend_html += f'<i style="background: {color}; width: 20px; height: 20px; display: inline-block;"></i> {cat}<br>'

legend_html += '</div>'

# Menambahkan legenda di dalam peta 
folium.Marker(
    location=[-31.0786614616483, -36.77559617047896],  # Posisi marker di peta, bisa disesuaikan
    icon=folium.DivIcon(html=legend_html)  # Menambahkan HTML ke marker sebagai legenda
).add_to(m)

# Menampilkan peta choropleth
folium_map = m
folium_static(m)

with st.expander('Klik untuk melihat Insight lebih lanjut'):
    st.caption("""
    **Insight:**

    Berdasarkan choropleth map diatas, produk dengan kategori Health Beauty merupakan produk paling populer di lebih dari 10 negara bagian. Kategori produk paling populer selanjutnya adalah Bed Bath Table yang populer di 5 negara bagian dan kategori produk Sport Leisure adalah kategori produk yang paling populer di 4 negara bagian.
    Tingginya jumlah pesanan/transaksi untuk kategori produk Health Beauty menunjukkan tren belanja yang cukup tinggi, terutama di wilayah dengan tingkat urbanisasi yang lebih besar, yang mungkin menunjukkan tingginya permintaan untuk produk perawatan pribadi. Sedangkan, untuk kategori produk Bed Bath Table mungkin cukup populer di 5 negara bagian karena adanya permintaan yang signifikan untuk produk rumah tangga dan perawatan rumah di wilayah-wilayah tersebut. Begitu juga untuk kategori produk Sports Leisure yang populer di 4 negara bagian menunjukkan minat yang tinggi terhadap aktivitas fisik dan hiburan luar ruangan di negara bagian tersebut.
    """)
