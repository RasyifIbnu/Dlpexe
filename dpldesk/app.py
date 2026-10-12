import customtkinter as ctk
from tkinter import messagebox, filedialog
import subprocess
import threading
import json
import os
import urllib.request
import webbrowser
from PIL import Image
import io

# --- KONFIGURASI TEMA MODERN ---
ctk.set_appearance_mode("dark")

# --- KONFIGURASI VERSI & SERVER ---
APP_VERSION = "1.0"
# Ganti URL ini nanti dengan link file version.json mentah (raw) Anda di GitHub/Server
STATUS_URL = "https://raw.githubusercontent.com/username/repo/main/version.json" 

CONFIG_FILE = "config.json"

def muat_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"download_path": os.getcwd()}

def simpan_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

config_app = muat_config()

# --- FUNGSI KEAMANAN & PEMBARUAN ---
def cek_status_keamanan():
    """Mengecek Kill Switch dan Update Aplikasi dari server di background"""
    try:
        req = urllib.request.Request(STATUS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        # 1. Cek Kill Switch (Remote Disable)
        if not data.get("mesin_aktif", True):
            pesan = data.get("pesan_darurat", "Keamanan sistem sedang ditingkatkan. Akses ditutup sementara.")
            # Matikan tombol dari Main Thread agar tidak error
            app.after(0, lambda: btn_unduh.configure(state="disabled"))
            app.after(0, lambda: btn_cek.configure(state="disabled"))
            app.after(0, lambda: btn_update_mesin.configure(state="disabled"))
            app.after(0, lambda: messagebox.showerror("Peringatan Keamanan Darurat", pesan))
            return

        # 2. Cek Pembaruan Aplikasi (Version Checker)
        versi_terbaru = data.get("app_version", APP_VERSION)
        if float(versi_terbaru) > float(APP_VERSION):
            url_unduh = data.get("update_url", "https://google.com")
            def tampilkan_pesan():
                tanya = messagebox.askyesno(
                    "Pembaruan Tersedia", 
                    f"Versi {versi_terbaru} telah dirilis!\nApakah Anda ingin mengunduhnya sekarang?"
                )
                if tanya:
                    webbrowser.open(url_unduh)
            app.after(0, tampilkan_pesan)

    except Exception as e:
        print(f"Pengecekan server dilewati: {e}")

def perbarui_mesin():
    """Fungsi mengeksekusi yt-dlp -U secara senyap"""
    btn_update_mesin.configure(state="disabled", text="⏳ Memperbarui...")
    label_status.configure(text="⚙️ Mengunduh pembaruan...", text_color="#FBBF24")
    
    def eksekusi_update():
        try:
            perintah = ["yt-dlp", "-U"]
            hasil = subprocess.run(perintah, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            app.after(0, lambda: label_status.configure(text="✅ Mesin berhasil diperbarui!", text_color="#34D399"))
            app.after(0, lambda: messagebox.showinfo("Sukses", "Mesin unduhan berhasil diperbarui ke versi terbaru!"))
        except subprocess.CalledProcessError as e:
            app.after(0, lambda: label_status.configure(text="❌ Gagal memperbarui mesin.", text_color="#F87171"))
            app.after(0, lambda: messagebox.showerror("Error Update", f"Terjadi kesalahan:\n{e.stderr}"))
        finally:
            app.after(0, lambda: btn_update_mesin.configure(state="normal", text="🔄 Update Mesin"))

    threading.Thread(target=eksekusi_update, daemon=True).start()

# --- MENGAMBIL IKON DARI INTERNET ---
def muat_ikon_internet(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data_gambar = response.read()
        gambar_pil = Image.open(io.BytesIO(data_gambar))
        return ctk.CTkImage(light_image=gambar_pil, dark_image=gambar_pil, size=(22, 22))
    except Exception as e:
        print(f"Gagal memuat ikon: {e}")
        return None

def format_ukuran(bytes_size):
    if not bytes_size or bytes_size == 0:
        return "? MB"
    mb = bytes_size / (1024 * 1024)
    return f"{mb:.1f} MB"

def pilih_folder():
    folder_baru = filedialog.askdirectory(initialdir=path_simpan.get(), title="Pilih Lokasi Penyimpanan")
    if folder_baru:
        path_simpan.set(folder_baru)
        config_app["download_path"] = folder_baru
        simpan_config(config_app)

def cek_info():
    link = var_link.get().strip()
    if not link:
        opsi_format.configure(values=["Menunggu tautan..."])
        opsi_format.set("Menunggu tautan...")
        label_status.configure(text="", text_color="transparent")
        return
        
    btn_cek.configure(state="disabled", text="⏳")
    label_status.configure(text="🔍 Memindai data video...", text_color="#FBBF24") 
    
    def ambil_data():
        try:
            perintah = ["yt-dlp", "-J", link]
            hasil = subprocess.run(perintah, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            data = json.loads(hasil.stdout)
            
            resolusi_dict = {}
            audio_size = 0
            
            for f in data.get('formats', []):
                ukuran = f.get('filesize') or f.get('filesize_approx') or 0
                
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    if ukuran > audio_size:
                        audio_size = ukuran
                        
                vcodec = f.get('vcodec')
                note = f.get('format_note')
                if vcodec != 'none' and note and 'p' in note:
                    res_str = ''.join(filter(str.isdigit, note.split('p')[0]))
                    if res_str:
                        res = int(res_str)
                        if res not in resolusi_dict or ukuran > resolusi_dict[res]:
                            resolusi_dict[res] = ukuran
            
            pilihan = []
            for res in sorted(resolusi_dict.keys(), reverse=True):
                total_ukuran = resolusi_dict[res] + audio_size
                pilihan.append(f"🎞️ Video (MP4) - {res}p ({format_ukuran(total_ukuran)})")
                
            pilihan.append(f"🎵 Audio (MP3) - Suara Saja ({format_ukuran(audio_size)})")
            
            if not resolusi_dict:
                pilihan = ["🎞️ Video (MP4) - Kualitas Default", "🎵 Audio (MP3) - Suara Saja"]

            app.after(0, lambda: opsi_format.configure(values=pilihan))
            app.after(0, lambda: opsi_format.set(pilihan[0])) 
            app.after(0, lambda: label_status.configure(text="✨ Kualitas ditemukan! Siap diunduh.", text_color="#34D399"))
        except subprocess.CalledProcessError:
            app.after(0, lambda: label_status.configure(text="❌ Link tidak valid / Butuh cek manual", text_color="#F87171")) 
            app.after(0, lambda: opsi_format.configure(values=["- Pilih Format -"]))
            app.after(0, lambda: opsi_format.set("- Pilih Format -"))
        except Exception as e:
            app.after(0, lambda: label_status.configure(text=f"❌ Error: {e}", text_color="#F87171"))
        finally:
            app.after(0, lambda: btn_cek.configure(state="normal", text="Cari"))

    threading.Thread(target=ambil_data, daemon=True).start()

def proses_unduh():
    link = var_link.get().strip()
    pilihan = opsi_format.get()
    lokasi = path_simpan.get()
    
    if not link:
        messagebox.showwarning("Peringatan", "Link tidak boleh kosong!")
        return
    if "Pilih Format" in pilihan or "Menunggu" in pilihan:
        messagebox.showwarning("Peringatan", "Tunggu hingga data selesai dicek.")
        return
        
    btn_unduh.configure(state="disabled", text="⏳ Mengunduh...", image="")
    label_status.configure(text=f"🚀 Sedang mengunduh file, mohon tunggu...", text_color="#FBBF24")
    
    def eksekusi():
        try:
            if "Audio" in pilihan:
                perintah = ["yt-dlp", "-x", "--audio-format", "mp3", "-P", lokasi, link]
            else:
                if "Default" in pilihan:
                    perintah = ["yt-dlp", "-S", "ext:mp4:m4a", "-P", lokasi, link]
                else:
                    teks_resolusi = pilihan.split('-')[1].split('p')[0]
                    angka_res = ''.join(filter(str.isdigit, teks_resolusi))
                    perintah = ["yt-dlp", "-S", f"res:{angka_res},ext:mp4:m4a", "-P", lokasi, link]
                
            subprocess.run(perintah, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            app.after(0, lambda: label_status.configure(text="✅ Selesai! File berhasil disimpan.", text_color="#34D399"))
            
        except subprocess.CalledProcessError as e:
            app.after(0, lambda: label_status.configure(text="❌ Gagal mengunduh.", text_color="#F87171"))
            app.after(0, lambda: messagebox.showerror("Error", f"Terjadi kesalahan:\n{e.stderr}"))
        finally:
            app.after(0, lambda: btn_unduh.configure(state="normal", text=" Unduh Sekarang", image=ikon_download))

    threading.Thread(target=eksekusi, daemon=True).start()

def hapus_link():
    var_link.set("")

def paste_link():
    try:
        teks_salinan = app.clipboard_get()
        var_link.set(teks_salinan)
    except Exception:
        pass

# --- LOGIKA AUTO-CHECK ---
var_link = None
timer_delay = None

def on_link_change(*args):
    global timer_delay
    if timer_delay is not None:
        app.after_cancel(timer_delay)
    timer_delay = app.after(1000, jalankan_cek_otomatis)

def jalankan_cek_otomatis():
    link = var_link.get().strip()
    if link.startswith("http://") or link.startswith("https://"):
        cek_info()
    elif not link:
        opsi_format.configure(values=["Menunggu tautan..."])
        opsi_format.set("Menunggu tautan...")
        label_status.configure(text="", text_color="transparent")


# ==========================================
#         DESAIN UI/UX MODERN & STABIL
# ==========================================
app = ctk.CTk()
app.geometry("560x490")
app.title("Downloader Pro")
app.resizable(False, False)

app.configure(fg_color="#0F172A") 

URL_IKON = "https://img.icons8.com/ios-glyphs/60/ffffff/download--v1.png"
ikon_download = muat_ikon_internet(URL_IKON)

var_link = ctk.StringVar()
var_link.trace_add("write", on_link_change)

# --- HEADER ---
header_frame = ctk.CTkFrame(app, fg_color="transparent")
header_frame.pack(fill="x", pady=(25, 10))

ctk.CTkLabel(header_frame, text="⚡ Media Downloader", font=ctk.CTkFont(size=24, weight="bold", family="Segoe UI"), text_color="#F8FAFC").pack()
ctk.CTkLabel(header_frame, text="Cepat, Mudah, Kualitas Terbaik", font=ctk.CTkFont(size=12, family="Segoe UI"), text_color="#94A3B8").pack()

# --- CARD KONTROL UTAMA ---
card_frame = ctk.CTkFrame(app, fg_color="#1E293B", corner_radius=15, border_width=1, border_color="#334155") 
card_frame.pack(padx=25, pady=10, fill="x")

# 1. Baris Link
row1 = ctk.CTkFrame(card_frame, fg_color="transparent")
row1.pack(fill="x", padx=20, pady=(20, 10))

ctk.CTkLabel(row1, text="🔗 Tautan", width=85, anchor="w", font=ctk.CTkFont(weight="bold"), text_color="#F1F5F9").pack(side="left")

input_link = ctk.CTkEntry(row1, textvariable=var_link, placeholder_text="Tempel URL...", width=177, height=38, border_width=1, border_color="#334155", fg_color="#0F172A", corner_radius=8, text_color="#F8FAFC")
input_link.pack(side="left", padx=(15, 5)) 

btn_paste = ctk.CTkButton(row1, text="📋", width=38, height=38, corner_radius=8, fg_color="#475569", hover_color="#64748B", font=ctk.CTkFont(weight="bold", size=16), command=paste_link)
btn_paste.pack(side="left", padx=(0, 5))

btn_hapus = ctk.CTkButton(row1, text="✕", width=38, height=38, corner_radius=8, fg_color="#EF4444", hover_color="#DC2626", font=ctk.CTkFont(weight="bold", size=16), command=hapus_link)
btn_hapus.pack(side="left", padx=(0, 5))

btn_cek = ctk.CTkButton(row1, text="Cari", width=70, height=38, corner_radius=8, fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(weight="bold"), command=cek_info)
btn_cek.pack(side="left")

# 2. Baris Lokasi Simpan
row2 = ctk.CTkFrame(card_frame, fg_color="transparent")
row2.pack(fill="x", padx=20, pady=10)

ctk.CTkLabel(row2, text="📂 Simpan", width=85, anchor="w", font=ctk.CTkFont(weight="bold"), text_color="#F1F5F9").pack(side="left")
path_simpan = ctk.StringVar(value=config_app.get("download_path"))
label_lokasi = ctk.CTkEntry(row2, textvariable=path_simpan, width=263, height=38, state="readonly", border_width=1, border_color="#334155", fg_color="#0F172A", corner_radius=8, text_color="#CBD5E1")
label_lokasi.pack(side="left", padx=(15, 5)) 

btn_lokasi = ctk.CTkButton(row2, text="Ubah", width=70, height=38, corner_radius=8, fg_color="#475569", hover_color="#64748B", font=ctk.CTkFont(weight="bold"), command=pilih_folder)
btn_lokasi.pack(side="left")

# 3. Baris Pilihan Format
row3 = ctk.CTkFrame(card_frame, fg_color="transparent")
row3.pack(fill="x", padx=20, pady=(10, 20))

ctk.CTkLabel(row3, text="⚙️ Kualitas", width=85, anchor="w", font=ctk.CTkFont(weight="bold"), text_color="#F1F5F9").pack(side="left")
opsi_format = ctk.CTkOptionMenu(row3, values=["Menunggu tautan..."], width=338, height=38, corner_radius=8, fg_color="#334155", button_color="#475569", button_hover_color="#64748B")
opsi_format.pack(side="left", padx=(15, 0))


# --- AREA EKSEKUSI (Bawah) ---
btn_unduh = ctk.CTkButton(app, text=" Unduh Sekarang", image=ikon_download, width=250, height=45, corner_radius=10, 
                          fg_color="#10B981", hover_color="#059669", 
                          font=ctk.CTkFont(size=15, weight="bold"), command=proses_unduh)
btn_unduh.pack(pady=(15, 5))

label_status = ctk.CTkLabel(app, text="", font=ctk.CTkFont(size=13, weight="bold"), fg_color="transparent")
label_status.pack()

# --- TOMBOL UPDATE MESIN (Pojok Kanan Bawah) ---
btn_update_mesin = ctk.CTkButton(app, text="🔄 Update Mesin", width=120, height=28, corner_radius=8, 
                                 fg_color="#334155", hover_color="#475569", 
                                 font=ctk.CTkFont(size=12, weight="bold"), command=perbarui_mesin)
# Menempatkan tombol mengambang di pojok kanan bawah agar tidak merusak layout utama
btn_update_mesin.place(relx=0.95, rely=0.95, anchor="se")

# ==========================================
#         INISIASI & JALANKAN APLIKASI
# ==========================================
# Jalankan pengecekan keamanan di background saat aplikasi dibuka
threading.Thread(target=cek_status_keamanan, daemon=True).start()

app.mainloop()