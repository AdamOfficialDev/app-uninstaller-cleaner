# Pembersih dan Penghapus Aplikasi Lanjutan

Alat yang kuat untuk menghapus aplikasi Windows secara menyeluruh dan membersihkan data yang tersisa.

## Fitur

- **Deteksi Otomatis**: Secara otomatis mendeteksi semua aplikasi terinstal untuk pemilihan yang mudah
- **Penghapusan Batch**: Menghapus beberapa aplikasi sekaligus
- **Pemilihan Mode Interaktif**: Memilih mode penghapusan secara interaktif saat menjalankan program
- **Penghapusan Menyeluruh**: Menghapus aplikasi dan semua data terkait
- **Pembersihan Registry**: Memindai dan menghapus entri registry yang berhubungan dengan aplikasi
- **Pembersihan Sistem File**: Menemukan dan menghapus file dan direktori yang tersisa
- **Pembuatan Cadangan**: Membuat cadangan kunci registry dan file sebelum penghapusan
- **Mode Simulasi**: Melihat perubahan tanpa melakukan modifikasi sebenarnya
- **Pelaporan Terperinci**: Menghasilkan laporan komprehensif tentang proses penghapusan
- **Mode Admin**: Secara otomatis meminta izin yang diperlukan

## Persyaratan

- Sistem operasi Windows
- Python 3.6 atau lebih tinggi
- Hak administrator

## Instalasi

Tidak diperlukan instalasi. Cukup unduh skrip dan jalankan dengan Python.

```bash
git clone https://github.com/AdamOfficialDev/app-uninstaller-cleaner.git
cd app-uninstaller-cleaner
```

## Penggunaan

```bash
# Luncurkan mode interaktif untuk memilih aplikasi yang akan dihapus
python uninstaller.py

# Tampilkan semua aplikasi terinstal tanpa menghapus
python uninstaller.py --list-only

# Hapus aplikasi tertentu berdasarkan nama
python uninstaller.py --app-name "Nama Aplikasi"
```

### Opsi Baris Perintah

- `--app-name "Nama Aplikasi"`: Tentukan aplikasi yang akan dihapus (opsional)
- `--list-only` atau `-l`: Hanya menampilkan aplikasi terinstal tanpa menghapus
- `--thorough` atau `-t`: Aktifkan mode pembersihan menyeluruh (memindai semua jejak aplikasi)
- `--dry-run` atau `-d`: Pratinjau perubahan tanpa benar-benar menghapus apapun
- `--no-backup` atau `-n`: Nonaktifkan pembuatan cadangan

### Contoh

```bash
# Luncurkan menu pemilihan interaktif untuk memilih aplikasi yang akan dihapus
python uninstaller.py

# Tampilkan semua aplikasi terinstal
python uninstaller.py --list-only

# Penghapusan dasar aplikasi tertentu
python uninstaller.py --app-name "Google Chrome"

# Penghapusan menyeluruh dengan cadangan
python uninstaller.py --app-name "Adobe Photoshop" --thorough

# Pratinjau apa yang akan dihapus tanpa melakukan perubahan
python uninstaller.py --app-name "Microsoft Office" --dry-run

# Penghapusan tanpa membuat cadangan
python uninstaller.py --app-name "Spotify" --no-backup

# Penghapusan menyeluruh tanpa cadangan
python uninstaller.py --app-name "Dropbox" --thorough --no-backup
```

## Cara Kerja

1. **Deteksi Aplikasi**: Memindai registry Windows untuk mendeteksi semua aplikasi terinstal
2. **Pemilihan Pengguna**: Menampilkan daftar aplikasi terdeteksi untuk dipilih pengguna
3. **Pemindaian Registry**: Mencari entri penghapusan di registry Windows
4. **Eksekusi Uninstaller**: Menjalankan uninstaller resmi aplikasi jika tersedia
5. **Pembersihan Registry**: Menghapus entri registry yang berhubungan dengan aplikasi
6. **Penghapusan Direktori**: Mengidentifikasi dan menghapus direktori aplikasi
7. **Pembersihan File**: Menemukan dan menghapus file yang tersisa (dalam mode menyeluruh)
8. **Pemindaian Registry Mendalam**: Memindai registry untuk referensi aplikasi tambahan (dalam mode menyeluruh)
9. **Pelaporan**: Menghasilkan laporan terperinci tentang proses penghapusan

## Fitur Keamanan

- **Pembuatan Cadangan**: Membuat cadangan kunci registry dan file sebelum penghapusan
- **Mode Simulasi**: Pratinjau perubahan tanpa melakukan modifikasi apa pun
- **Konfirmasi**: Memerlukan konfirmasi pengguna sebelum melanjutkan penghapusan
- **Penanganan Kesalahan**: Menangani kesalahan dengan baik dan memberikan logging terperinci

## Peringatan

Gunakan alat ini dengan risiko Anda sendiri. Meskipun alat ini memiliki fitur keamanan seperti cadangan dan mode simulasi, penggunaan yang tidak tepat dapat berpotensi menyebabkan masalah sistem. Selalu jalankan dengan `--dry-run` terlebih dahulu untuk melihat perubahan yang akan dilakukan.

## Lisensi

Lisensi MIT

## Kontribusi

Kontribusi dipersilakan! Jangan ragu untuk mengirimkan Pull Request. 