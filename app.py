import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, send_file, jsonify
import logging
import re
import csv
from datetime import datetime

app = Flask(__name__)

TOKEN_FORMAT = re.compile(r"d\.authenticityToken[\s+]=[\s+]['\"]([0-9a-zA-Z]+)['\"];", re.DOTALL)

def parse_token(page):
    token = TOKEN_FORMAT.findall(page)

    if token:
        return token[0]

    return

"""# URL LPSE
url = "https://lpse.pu.go.id/eproc4"
"""

# Headers untuk menghindari pemblokiran
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# Fungsi untuk membaca daftar URL dari CSV
def read_csv(file_path):
    urls = []
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:  # Pastikan baris tidak kosong
                    urls.append(row[0])  # Ambil URL dari kolom pertama
    except Exception as e:
        logging.error(f"Gagal membaca file CSV: {str(e)}")
    return urls

# Fungsi untuk scraping data LPSE      
def scrape_lpse(url):
    """Fungsi untuk scraping data dari LPSE"""
    data = []  # List untuk menyimpan data lelang
    try:
        logging.info(f"Mengakses {url}...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Menemukan tabel lelang (sesuaikan dengan struktur HTML)
            table = soup.find('table', class_='table table-sm') # Sesuaikan selector dengan struktur tabel LPSE
            
            if table:
                for row in table.find_all('tr')[1:]:  # Lewati header
                    columns = row.find_all('td')

                    # Mengabaikan baris dengan 'colspan="4"' atau kelas yang tidak diinginkan
                    """if any(cls in row.get('class', []) for cls in [
                        'Pengadaan_Barang', 'Pekerjaan_Konstruksi', 'Jasa_Lainnya',
                        'Jasa_Konsultansi_Perorangan_Non_Konstruksi', 'Jasa_Konsultansi_Perorangan_Konstruksi',
                        'Pekerjaan_Konstruksi_Terintegrasi']):
                        continue"""

                    # Hapus elemen dengan class 'badge' dari setiap kolom
                    for column in columns:
                        badge = column.find_all('span', class_='badge')  # Mencari elemen dengan class "badge"
                        for b in badge:
                            b.decompose()  # Hapus elemen "badge"
                        
                        # Mengganti kolom dengan style text-align: center; dengan URL
                        if 'text-align: center;' in column.get('style', ''):
                            column.string = url  # Gantikan konten kolom dengan URL

                    if len(columns) >= 4:  # Pastikan ada cukup kolom
                        link_lpse = columns[0].text.strip() # Mendapatkan link LPSE
                        nama_paket = columns[1].text.strip()
                        nilai_hps = clean_nilai_hps(columns[2].text.strip())  # Bersihkan Nilai HPS dan ubah menjadi float
                        tgl_akhir = columns[3].text.strip()

                        data.append([link_lpse, nama_paket, nilai_hps, tgl_akhir])

                logging.info(f"Berhasil mendapatkan {len(data)} data lelang dari {url}.")
            else:
                logging.warning(f"Tabel tidak ditemukan di {url}.")
        else:
            logging.error(f"Gagal mengakses halaman {url}. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error saat mengakses {url}: {str(e)}")

    return data

# Fungsi untuk membersihkan dan memformat Nilai HPS
def clean_nilai_hps(nilai):
    # Menghapus simbol mata uang "Rp." dan memformat angka
    cleaned_value = re.sub(r'[^\d,]', '', nilai)  # Menghapus simbol selain angka dan koma
    cleaned_value = cleaned_value.replace(',', '.')  # Mengganti koma dengan titik sebagai desimal
    cleaned_value = cleaned_value.replace('.', '', cleaned_value.count('.') - 1)  # Menghapus titik sebagai pemisah ribuan
    try:
        return float(cleaned_value)  # Mengonversi menjadi angka
    except ValueError:
        return 0.0  # Jika gagal, kembalikan 0.0

# Route untuk halaman utama
@app.route('/')
def home():
    """Tampilkan data LPSE dari berbagai sumber"""
    csv_file = "daftarlpse.csv"
    urls = read_csv(csv_file)

    all_data = []
    for url in urls:
        all_data.extend(scrape_lpse(url)) # Gabungkan hasil scraping dari semua URL

    last_updated = datetime.now().strftime('%d-%m-%Y %H:%M') if all_data else "Gagal mengambil data"
    # Tambahkan nomor urut menggunakan enumerate
    data_with_index = [(index + 1, row) for index, row in enumerate(all_data)]  # Menambahkan index
    return render_template("index.html", data=data_with_index, last_updated=last_updated)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
