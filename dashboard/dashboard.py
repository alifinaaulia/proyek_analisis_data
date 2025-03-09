import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import json
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from shapely.geometry import shape

# Load dataset 
url = 'https://raw.githubusercontent.com/alifinaaulia/proyek_analisis_data/refs/heads/main/dashboard/main_data.csv'
geojson_url = 'https://github.com/alifinaaulia/proyek_analisis_data/blob/main/dashboard/brazil_states.geojson'
df = pd.read_csv(url)  
response = requests.get(geojson_url)
geojson_data = response.json()

# Mengelompokkan data berdasarkan kota dan menghitung total revenue per kota
df_city_revenue = df.groupby("customer_city").agg({
    "price": "sum",  # Total revenue per kota
    "geolocation_lat": "first",  
    "geolocation_lng": "first"   
}).reset_index()

# Menentukan kota dengan revenue tertinggi
top_city = df_city_revenue.loc[df_city_revenue["price"].idxmax(), "customer_city"]

# Mengambil 10 kota teratas berdasarkan total revenue
df_top_cities = df_city_revenue.sort_values(by="price", ascending=False).head(10)

# Judul untuk dashboard Streamlit
st.title("Dashboard Analisis Revenue dan Kategori Produk di E-Commerce Brazil")

# Menampilkan peta untuk total revenue per kota
st.subheader("Peta Revenue per Kota")
st.markdown("Peta ini menunjukkan total revenue untuk 10 kota dengan revenue tertinggi di Brazil dan menampilkan warna berdasarkan level revenue.")
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

with st.expander('Klik untuk melihat Insight lebih lanjut'):
    st.caption("""
    **Insight:**
            
    Berdasarkan peta di atas, terlihat bahwa semakin hijau warna marker pada peta, semakin tinggi total pendapatan di kota tersebut.
    Di antara 10 kota dengan total pendapatan tertinggi di Brasil, **Sao Paulo** memiliki total pendapatan tertinggi, yakni **BRL 1.914.600**. 
    Hal ini mungkin disebabkan oleh fakta bahwa kota Sao Paulo merupakan kota terbesar di Brazil, yang berkontribusi pada tingginya total pendapatan.
    """)

st.write('Selanjutnya, akan dilihat performa penjualan pada kota Sao Paulo dari bulan ke bulan untuk menganalisis tren pertumbuhan penjualan (Month-over-Month) serta memahami pola peningkatan atau penurunan revenue di kota tersebut.')

# Menyiapkan data untuk Pertumbuhan Bulan ke Bulan (MoM) untuk kota dengan revenue tertinggi
df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
df["year_month"] = df["order_purchase_timestamp"].dt.to_period("M")
df_mom = df[(df["customer_city"] == top_city) & (df["order_purchase_timestamp"] < "2018-09-01")]
df_mom = df_mom.groupby("year_month")["price"].sum().reset_index()

# Menghitung Pertumbuhan MoM
df_mom["growth"] = df_mom["price"].pct_change() * 100
df_mom["year_month"] = df_mom["year_month"].astype(str)
df_mom_cleaned = df_mom.dropna(subset=["growth"]).reset_index(drop=True)
df_mom_filtered = df_mom_cleaned[df_mom_cleaned["price"].shift(1) > 0]

# Mengambil 3 bulan dengan pertumbuhan tertinggi dan terendah
top_3_growth = df_mom_filtered.nlargest(3, "growth").index  
bottom_3_growth = df_mom_filtered.nsmallest(3, "growth").index 

# Menampilkan grafik Pertumbuhan MoM
st.subheader(f"Pertumbuhan Penjualan Bulanan (MoM) di {top_city}")
st.markdown("Grafik ini menunjukkan pertumbuhan penjualan per bulan di kota dengan revenue tertinggi.")
fig = plt.figure(figsize=(12, 6))
sns.lineplot(x="year_month", y="price", data=df_mom, marker="o", color="green")

# Menyoroti 3 bulan dengan pertumbuhan tertinggi dan terendah
for idx in top_3_growth:
    plt.text(idx, df_mom_filtered["price"][idx] + 7000, 
             f" {df_mom_filtered['growth'][idx]:.1f}%", 
             fontsize=12, ha="center", color="blue", fontweight="bold")

for idx in bottom_3_growth:
    plt.text(idx, df_mom_filtered["price"][idx] - 7000, 
             f" {df_mom_filtered['growth'][idx]:.1f}%", 
             fontsize=12, ha="center", color="red", fontweight="bold")

plt.xticks(rotation=45)
plt.title(f"Pertumbuhan Penjualan MoM di {top_city}", fontsize=14)
plt.xlabel("Bulan")
plt.ylabel("Total Revenue (BRL)")

# Menampilkan grafik di Streamlit
st.pyplot(fig)

with st.expander('Klik untuk melihat Insight lebih lanjut'):
    st.caption("""
    **Insight:**

    Pada pertumbuhan penjualan bulanan (Month-over-Month) untuk kota Sao Paulo menunjukkan kenaikan tertinggi terjadi antara bulan Februari 2017 hingga Maret 2017 yakni sebesar 95,1%. Kenaikan penjualan bulanan pada bulan tersebut kemungkinan disebabkan oleh peningkatan permintaan musiman, perayaan hari besar, atau faktor eksternal seperti kebijakan pemerintah dan tren pasar yang sedang berlangsung.
    Sebaliknya, penurunan terbesar bulanan di kota Sao Paulo yang terjadi di antara bulan November 2017 dan Desember 2017 yakni sebesar 28,3%.  Penurunan penjualan bulanan pada bulan-bulan tersebut kemungkinan disebabkan oleh berakhirnya periode promosi, penurunan permintaan musiman, atau faktor eksternal seperti kondisi ekonomi yang melemah dan perubahan regulasi.
    """)

st.write('Setelah didapatkan periode kenaikan penjualan tertinggi di kota Sao Paulo yakni pada Februari 2017 hingga Maret 2017, selanjutnya akan dianalisis mengenai kategori produk yang paling banyak dipesan pada periode tersebut untuk memahami tren permintaan dan faktor yang mungkin berkontribusi terhadap peningkatan penjualan.')

# Menampilkan kategori produk terpopuler di Sao Paulo selama periode pertumbuhan tertinggi
df_period = df[(df["customer_city"] == "sao paulo") & 
               (df["order_purchase_timestamp"].between("2017-02-01", "2017-03-31"))]
top_categories = df_period.groupby("product_cat")["order_id"].nunique().reset_index()
top_categories = top_categories.sort_values(by="order_id", ascending=False)

# Grafik kategori produk
st.subheader(f"Kategori Produk Paling Banyak Dipesan di {top_city} (Feb-Mar 2017)")
st.markdown("Grafik ini menunjukkan kategori produk yang paling banyak dipesan di Sao Paulo pada periode peningkatan tertinggi.")
fig = plt.figure(figsize=(10, 5))
ax = sns.barplot(x=top_categories["order_id"].head(10), 
                 y=top_categories["product_cat"].head(10))

# Menambahkan label untuk setiap kategori produk
for p in ax.patches:
    ax.annotate(f'{int(p.get_width())}', 
                (p.get_width(), p.get_y() + p.get_height() / 2), 
                ha='left', va='center', fontsize=10, color='black', fontweight="bold")

st.pyplot(fig)

with st.expander('Klik untuk melihat Insight lebih lanjut'):
    st.caption("""
        **Insight:**

        Berdasarkan chart di atas, terlihat bahwa produk dengan kategori Furniture Decor paling banyak dipesan pada periode tersebut dengan jumlah pesanannya mencapai 89. Kategori produk selanjutnya yang paling banyak dipesan yaitu Bed Bath Table sebanyak 59 pesanan, Sports Leisure sebanyak 49 pesanan, Health Beauty sebanyak 47 pesanan, dan Housewares sebanyak 40 pesanan.
        Kategori produk yang paling banyak dipesan ini menunjukkan bahwa pada periode Februari 2017 hingga Maret 2017, terdapat peningkatan minat pelanggan terhadap produk-produk yang berkaitan dengan kebutuhan rumah tangga, kesehatan, serta aktivitas rekreasi.

        """)

# Menampilkan peta produk terpopuler per negara bagian di Brasil
st.subheader("Peta Produk Paling Populer di Setiap Negara Bagian")
st.markdown("Peta ini menunjukkan produk dengan jumlah transaksi terbanyak di setiap negara bagian Brasil.")


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

# Mencocokkan antara geojson_data dan produk dengan transaksi terbanyak di setiap negara bagian
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

st.header("Kesimpulan:", divider='rainbow')
st.markdown("1. Di antara 10 kota dengan total pendapatan tertinggi di Brazil, kota Sao Paulo memiliki total pendapatan tertinggi yakni BRL 1.914.600. Hal ini mungkin dikarenakan kota Sao Paulo juga memiliki jumlah pesanan yang tertinggi karena merupakan kota terbesar di Brazil sehingga membuat total pendapatannya juga tinggi.")
st.markdown("2. Pada pertumbuhan penjualan bulanan (Month-over-Month) untuk kota Sao Paulo menunjukkan kenaikan tertinggi terjadi antara bulan Februari 2017 hingga Maret 2017 yakni sebesar 95,1%. Kenaikan penjualan bulanan pada bulan tersebut kemungkinan disebabkan oleh peningkatan permintaan musiman, perayaan hari besar, atau faktor eksternal seperti kebijakan pemerintah dan tren pasar yang sedang berlangsung. Sebaliknya, penurunan terbesar bulanan di kota Sao Paulo yang terjadi di antara bulan November 2017 dan Desember 2017 yakni sebesar 28,3%. Penurunan penjualan bulanan pada bulan-bulan tersebut kemungkinan disebabkan oleh berakhirnya periode promosi, penurunan permintaan musiman, atau faktor eksternal seperti kondisi ekonomi yang melemah dan perubahan regulasi.")
st.markdown("3. Produk dengan kategori Furniture Decor paling banyak dipesan pada periode kenaikan tertinggi penjualan bulanan (Februari-Maret 2017) dengan jumlah pesanannya mencapai 89. Kategori produk selanjutnya yang paling banyak dipesan yaitu Bed Bath Table sebanyak 59 pesanan, Sports Leisure sebanyak 49 pesanan, Health Beauty sebanyak 47 pesanan, dan Housewares sebanyak 40 pesanan. Kategori produk yang paling banyak dipesan ini menunjukkan bahwa pada periode Februari 2017 hingga Maret 2017, terdapat peningkatan minat pelanggan terhadap produk-produk yang berkaitan dengan kebutuhan rumah tangga, kesehatan, serta aktivitas rekreasi. Oleh karena itu, diharapkan strategi pemasaran dapat lebih dioptimalkan seperti dengan meningkatkan promosi pada kategori produk yang sedang diminati/tren atau menawarkan bundling produk untuk meningkatkan penjualan lebih lanjut.")
