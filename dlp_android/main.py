import flet as ft
import urllib.request
import json
import threading
import yt_dlp
import os

# --- KONFIGURASI VERSI & SERVER ---
APP_VERSION = "1.0"
STATUS_URL = "https://raw.githubusercontent.com/RasyifIbnu/Dplexe/refs/heads/main/version.json"

def main(page: ft.Page):
    # --- TEMA & PENGATURAN HALAMAN ---
    page.title = "Downloader Pro Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.window_width = 400
    page.window_height = 750
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    lokasi_unduh = "/storage/emulated/0/Download" # Default folder HP Android

    # --- ELEMEN UI ---
    header = ft.Text("⚡ Media Downloader", size=24, weight="bold", color="#F8FAFC")
    subheader = ft.Text("Cepat, Mudah, Kualitas Terbaik", size=12, color="#94A3B8")
    
    input_link = ft.TextField(label="🔗 Tempel URL Video", width=330, bgcolor="#1E293B", border_color="#334155", color="#F8FAFC")
    opsi_format = ft.Dropdown(label="⚙️ Kualitas", width=330, bgcolor="#1E293B", border_color="#334155", color="#F8FAFC",
                              options=[ft.dropdown.Option("Menunggu tautan...")])
    
    label_status = ft.Text("", size=14, weight="bold")
    
    # --- FUNGSI KEAMANAN (KILL SWITCH GITHUB) ---
    def cek_status_keamanan():
        try:
            req = urllib.request.Request(STATUS_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            if not data.get("mesin_aktif", True):
                pesan = data.get("pesan_darurat", "Keamanan sistem sedang ditingkatkan. Akses ditutup.")
                label_status.value = f"⛔ {pesan}"
                label_status.color = ft.colors.RED_400
                input_link.disabled = True
                btn_cek.disabled = True
                btn_unduh.disabled = True
                page.update()
                return

            versi_terbaru = data.get("app_version", APP_VERSION)
            if float(versi_terbaru) > float(APP_VERSION):
                url_unduh = data.get("update_url", "https://google.com")
                page.dialog = ft.AlertDialog(
                    title=ft.Text("Pembaruan Tersedia"),
                    content=ft.Text(f"Versi {versi_terbaru} telah dirilis!\nSilakan unduh dari web utama."),
                    actions=[ft.TextButton("Tutup", on_click=lambda e: page.close_dialog())]
                )
                page.dialog.open = True
                page.update()
        except Exception as e:
            print(f"Pengecekan server dilewati: {e}")

    # --- FUNGSI CEK INFO VIDEO ---
    def proses_cek_link(e):
        link = input_link.value.strip()
        if not link:
            return
            
        btn_cek.disabled = True
        label_status.value = "🔍 Memindai data video..."
        label_status.color = ft.colors.AMBER_400
        page.update()

        def eksekusi_cek():
            try:
                ydl_opts = {'quiet': True, 'noplaylist': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                
                opsi = [
                    ft.dropdown.Option(key="best", text="🎞️ Video (MP4 - Kualitas Default)"),
                    ft.dropdown.Option(key="bestaudio", text="🎵 Audio (M4A - Suara Saja)")
                ]
                
                opsi_format.options = opsi
                opsi_format.value = "best"
                label_status.value = "✨ Kualitas ditemukan! Siap diunduh."
                label_status.color = ft.colors.GREEN_400
                btn_unduh.disabled = False
            except Exception as err:
                label_status.value = "❌ Gagal: Link tidak valid / Butuh cek manual."
                label_status.color = ft.colors.RED_400
            
            btn_cek.disabled = False
            page.update()

        threading.Thread(target=eksekusi_cek, daemon=True).start()

    # --- FUNGSI UNDUH (TANPA FFMPEG) ---
    def proses_unduh(e):
        link = input_link.value.strip()
        format_pilihan = opsi_format.value
        
        btn_unduh.disabled = True
        label_status.value = "🚀 Sedang mengunduh file, mohon tunggu..."
        label_status.color = ft.colors.AMBER_400
        page.update()

        def eksekusi_unduh():
            try:
                if format_pilihan == "bestaudio":
                    ydl_opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio', 
                        'outtmpl': f'{lokasi_unduh}/%(title)s.%(ext)s'
                    }
                else:
                    ydl_opts = {
                        'format': 'best', 
                        'outtmpl': f'{lokasi_unduh}/%(title)s.%(ext)s'
                    }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                
                label_status.value = "✅ Selesai! Tersimpan di folder Download."
                label_status.color = ft.colors.GREEN_400
            except Exception as err:
                label_status.value = f"❌ Gagal mengunduh: {err}"
                label_status.color = ft.colors.RED_400
            
            btn_unduh.disabled = False
            page.update()

        threading.Thread(target=eksekusi_unduh, daemon=True).start()

    # --- KOMPONEN TOMBOL ---
    btn_cek = ft.ElevatedButton("Cari", on_click=proses_cek_link, bgcolor="#3B82F6", color="white")
    btn_unduh = ft.ElevatedButton("Unduh Sekarang", disabled=True, on_click=proses_unduh, bgcolor="#10B981", color="white", width=330, height=45)

    # --- SUSUNAN TAMPILAN ---
    card_container = ft.Container(
        content=ft.Column([
            ft.Row([input_link, btn_cek], alignment=ft.MainAxisAlignment.CENTER),
            opsi_format
        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#1E293B", padding=20, border_radius=15, border=ft.border.all(1, "#334155")
    )

    page.add(
        ft.Container(height=30),
        header,
        subheader,
        ft.Container(height=20),
        card_container,
        ft.Container(height=20),
        btn_unduh,
        ft.Container(height=10),
        label_status
    )

    threading.Thread(target=cek_status_keamanan, daemon=True).start()


    ft.app(target=main)
