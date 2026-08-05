# iCloud HME Toolkit — Manajemen Alamat Hide My Email

Toolkit untuk membuat dan mengelola alamat **Hide My Email (HME)** `@icloud.com` secara massal, berbasis protokol iCloud Hide My Email Apple. Mendukung multi-akun, penjadwalan otomatis, dan Web UI.

- 👥 **Multi-akun** — kelola banyak akun iCloud sekaligus, setiap akun tersimpan & ber-sesi terpisah
- 🔗 **Pemetaan akun-ke-alias** — ekstraksi Apple ID otomatis, setiap alamat dicatat ke akun pemiliknya
- ⏱ **Penjadwalan** — trigger otomatis per jam, rotasi antar akun, otomatis pindah akun saat kena batas
- 🌐 **Web UI** — panel hangat: dashboard + daftar akun + manajemen alias + pembuatan massal lintas akun

## Prasyarat

- Langganan **iCloud+** (Hide My Email butuh iCloud+)
- Python 3.10+
- Windows / macOS / Linux

## Memulai

```bash
# 1. Install dependensi
pip install -r requirements.txt

# 2. Jalankan Web UI
python web_ui.py

# 3. Buka http://127.0.0.1:5050
#    Klik "Import Cookie" di pojok kiri bawah untuk menambahkan akun pertama
#    Mendukung Header String atau JSON dari Cookie Editor
```

## Cara Pakai

### Web UI (disarankan)

```bash
python web_ui.py                    # jalankan antarmuka web
python web_ui.py --port 8080        # tentukan port
python web_ui.py --scheduler        # aktifkan scheduler otomatis saat start
```

Fitur antarmuka:

| Modul | Fungsi |
|------|------|
| **Manajemen Akun** | Tambah/ganti/hapus akun, tiap akun punya Cookie + sesi terpisah |
| **Dashboard** | Total akun, total alias, jumlah dibuat hari ini, kartu status per akun |
| **Daftar Alias** | Menarik semua alias secara real-time, ditandai akun pemilik + email asli |
| **Buat Massal** | Centang akun target → isi jumlah → pembuatan rotasi lintas akun |
| **Scheduler** | Start/stop sekali klik, setiap jam memproses semua akun aktif sampai batas |

### Scheduler Baris Perintah

```bash
# Penjadwalan multi-akun (tambahkan akun dulu melalui Web UI)
python scheduler.py

# Tentukan interval antar akun
python scheduler.py --interval 5

# Jalankan sebagai daemon di background
python scheduler.py -d
```

### Operasi Manual via CLI

```bash
# Daftarkan semua alias
python icloud_hme.py list --cookies cookies.json

# Buat alias
python icloud_hme.py create -n 5 --cookies cookies.json

# Hapus alias
python icloud_hme.py delete --email xxx@icloud.com --cookies cookies.json
```

## Mendapatkan Cookie

| Cara | Keterangan |
|------|------|
| Import Web UI | Klik tombol pojok kiri bawah, tempel Header String dari Cookie Editor |
| Ekstrak Chrome | Windows: `python icloud_hme.py export-cookies` |
| CLI `--cookies` | Tentukan path file JSON |

Mendukung dua format input:
- **Header String**: `name1=value1; name2=value2; ...`
- **JSON**: `{"name1":"value1", "name2":"value2"}`

Setelah import otomatis tersimpan ke `accounts.json`, restart tidak perlu tempel ulang.

## Logika Scheduler

```
Trigger per jam
  → proses semua akun aktif
  → tiap akun buat sampai batas yang dikembalikan iCloud
  → interval antar akun 3 detik (dapat diatur)
  → setelah selesai, tunggu jam berikutnya
```

## Struktur File

```
├── icloud_hme.py        # Library inti: ekstrak Cookie / API HME / identitas akun
├── account_manager.py   # Manajer multi-akun: CRUD / buat massal / indeks alias
├── web_ui.py            # Panel Web Flask + scheduler bawaan
├── scheduler.py         # Scheduler baris perintah mandiri
└── requirements.txt     # dependensi pip
```

Dihasilkan saat runtime:

```
accounts.json          # semua akun & Cookie (persistensi otomatis)
scheduler_state.json   # status histori scheduler
logs/                  # log berjalan
results/               # daftar email yang dibuat
```

## Dependensi

```
requests>=2.25          # HTTP
pycryptodome>=3.15     # dekripsi cookie Chrome (Windows)
pywin32>=305           # Windows DPAPI (khusus Windows)
flask>=3.0             # Web UI
```

## Lisensi

MIT
