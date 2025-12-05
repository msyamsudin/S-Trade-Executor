# S-Trade-Executor

Aplikasi otomatisasi trading dengan eksekusi cepat dan antarmuka intuitif.

<img width="500" height="306" alt="image" src="https://github.com/user-attachments/assets/033eea3e-49f8-40ce-b71c-17a289edd68c" />

## Fitur

- **Multi-Mode Click**: Single, Double, atau Burst (klik beruntun)
- **Multi-Koordinat**: Satu hotkey untuk banyak lokasi sekaligus
- **Auto-Save**: Konfigurasi tersimpan otomatis
- **Test Mode**: Verifikasi posisi koordinat sebelum eksekusi
- **Cancel on Move**: Batalkan eksekusi jika mouse tergeser

## Instalasi

1. Install Python dari [python.org](https://www.python.org/)
2. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi:
   ```bash
   python main.py
   ```

## Penggunaan

### Membuat Aksi
1. Klik **+ New Action**
2. Beri nama aksi
3. **Bind Key**: Klik tombol, tekan hotkey yang diinginkan
4. **Set Koordinat**: Klik tombol koordinat, lalu **Middle Click** di posisi target
5. Pilih **Mode** (Single/Double/Burst) dan atur **Delay** jika perlu

### Kontrol
- **Pause/Resume**: Toggle status di pojok kiri atas
- **Test**: Verifikasi posisi dengan crosshair tanpa klik
- **Cancel on Move**: Aktifkan untuk membatalkan eksekusi jika mouse bergerak

### Tips
- Tambah koordinat dengan tombol **+** untuk multi-target
- Mode Burst ditandai dengan efek pulse merah
- Delay dalam ms (1000ms = 1s)
- Gunakan **?** untuk panduan cepat