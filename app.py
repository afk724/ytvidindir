"""
YouTube Video İndirici (yt-dlp GUI) - Düz Siyah Koyu Tema
Format: yt-dlp -S "res:1080,vcodec:h264,acodec:aac" --merge-output-format mp4 "<VIDEO_URL>"
"""

import os
import sys
import re
import time
import json
import shutil
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import winsound
except ImportError:
    winsound = None

# CustomTkinter Ayarları: Saf Koyu Mod
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CONFIG_FILE = Path(__file__).parent / "config.json"


# ==============================================================================
# DÜZ SİYAH KOYU TEMA (PURE BLACK MINIMAL THEME)
# ==============================================================================
THEME = {
    # Ana Arka Planlar (Tam Siyah & Koyu Griler)
    "bg_window": "#000000",         # Saf Siyah
    "bg_card": "#0c0c0c",           # Kart Alanı
    "bg_input": "#141414",          # Giriş Kutuları
    "bg_console": "#070707",        # Terminal / Log Alanı

    # Sınırlar (İnce, Düz Gri Çizgiler)
    "border_subtle": "#222222",     # Kart Kenarlığı
    "border_input": "#2a2a2a",      # Giriş Kenarlığı
    "border_focus": "#555555",      # Odaklanma Kenarlığı

    # Metin Renkleri
    "text_primary": "#ffffff",      # Beyaz
    "text_secondary": "#a0a0a0",    # Açık Gri
    "text_muted": "#666666",        # Soluk Gri / Başlıklar

    # Buton Renkleri (Düz Minimalist)
    "btn_primary_bg": "#ffffff",    # Ana Buton (Beyaz)
    "btn_primary_hover": "#e0e0e0", # Hover
    "btn_primary_text": "#000000",  # Buton İçi Siyah Yazı

    "btn_secondary_bg": "#181818",  # İkincil Butonlar (Koyu Gri)
    "btn_secondary_hover": "#252525",
    "btn_secondary_border": "#2e2e2e",
    "btn_secondary_text": "#e0e0e0",

    "btn_danger_bg": "#1a0f0f",     # İptal Butonu
    "btn_danger_hover": "#2b1414",
    "btn_danger_border": "#451e1e",
    "btn_danger_text": "#ff6b6b",

    # Durum & İlerleme
    "status_ready": "#a0a0a0",
    "status_active": "#ffffff",
    "status_success": "#52c41a",
    "status_error": "#ff4d4f",

    "progress_fill": "#ffffff",     # İlerleme Çubuğu Rengi
    "progress_bg": "#1c1c1c"        # İlerleme Çubuğu Zemini
}


def get_default_download_dir():
    """Son kullanılan veya varsayılan İndirilenler klasörünü döner."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_dir = data.get("download_dir")
                if last_dir and os.path.exists(last_dir):
                    return last_dir
        except Exception:
            pass

    downloads = Path.home() / "Downloads"
    if downloads.exists():
        return str(downloads)
    return str(Path.home())


def save_config(folder_path):
    """Seçilen klasörü sonraki açılışlar için kaydeder."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"download_dir": folder_path}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def kill_process_tree(process):
    """Verilen sürecin ve tüm alt süreçlerinin anında durdurulmasını garanti eder."""
    if not process:
        return

    try:
        pid = process.pid
    except Exception:
        pid = None

    if pid and sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    try:
        process.kill()
    except Exception:
        pass


def cleanup_cancelled_downloads(target_folder, tracked_files, files_before, start_time):
    """
    İptal edilen indirmeye ait yarım kalmış tüm geçici (.part, .ytdl, .temp) ve
    parçalı indirme dosyalarını otomatik olarak temizler.
    """
    deleted_files = []
    if not target_folder or not os.path.exists(target_folder):
        return deleted_files

    candidates_to_delete = set()

    for f in tracked_files:
        p = Path(f)
        if not p.is_absolute():
            p = Path(target_folder) / f
        candidates_to_delete.add(p)
        candidates_to_delete.add(Path(str(p) + ".part"))
        candidates_to_delete.add(Path(str(p) + ".ytdl"))

    try:
        current_files = os.listdir(target_folder)
        for fname in current_files:
            if fname in files_before:
                continue

            fpath = Path(target_folder) / fname
            if fname.lower().endswith((".part", ".ytdl", ".temp")):
                candidates_to_delete.add(fpath)
            else:
                try:
                    mtime = fpath.stat().st_mtime
                    if mtime >= (start_time - 3):
                        for tracked in tracked_files:
                            tracked_name = Path(tracked).name
                            base_name = Path(tracked).stem.split(".")[0]
                            if base_name and (base_name in fname or fname in tracked_name):
                                candidates_to_delete.add(fpath)
                                break
                except Exception:
                    pass
    except Exception:
        pass

    for p in candidates_to_delete:
        if p.exists() and p.is_file():
            for _ in range(6):
                try:
                    p.unlink()
                    deleted_files.append(p.name)
                    break
                except Exception:
                    time.sleep(0.2)

    return deleted_files


# ==============================================================================
# DÜZ SİYAH UYGULAMA PENCERESİ
# ==============================================================================
class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Yapılandırması
        self.title("YouTube Video İndirici")
        self.geometry("820x680")
        self.minsize(740, 580)
        self.configure(fg_color=THEME["bg_window"])

        # Durum Değişkenleri
        self.download_process = None
        self.is_downloading = False
        self.is_cancelled = False
        self.download_dir = ctk.StringVar(value=get_default_download_dir())
        self.url_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Hazır")
        self.speed_eta_var = ctk.StringVar(value="")

        # İptal ve Temizlik Takibi
        self.tracked_files = set()
        self.files_before_download = set()
        self.download_start_time = 0

        # yt-dlp tespiti
        self.ytdlp_cmd = self.detect_ytdlp()

        self.build_ui()

    def detect_ytdlp(self):
        """Sistemde yt-dlp komutunu bulur."""
        exe = shutil.which("yt-dlp")
        if exe:
            return [exe]
        winget_link = Path.home() / "AppData/Local/Microsoft/WinGet/Links/yt-dlp.exe"
        if winget_link.exists():
            return [str(winget_link)]
        return [sys.executable, "-m", "yt_dlp"]

    def build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=26, pady=22)

        # ----------------------------------------------------------------------
        # 1. BAŞLIK ALANI (Sade ve Düz)
        # ----------------------------------------------------------------------
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 16))

        title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(anchor="w")

        main_title = ctk.CTkLabel(
            title_row,
            text="YouTube Video İndirici",
            font=("Segoe UI", 18, "bold"),
            text_color=THEME["text_primary"]
        )
        main_title.pack(side="left")

        # Format Rozeti
        format_badge = ctk.CTkFrame(
            title_row,
            fg_color=THEME["bg_input"],
            border_color=THEME["border_subtle"],
            border_width=1,
            corner_radius=6
        )
        format_badge.pack(side="left", padx=(12, 0))

        badge_lbl = ctk.CTkLabel(
            format_badge,
            text="1080p • H.264 • AAC • MP4",
            font=("Segoe UI", 10),
            text_color=THEME["text_secondary"],
            padx=8,
            pady=2
        )
        badge_lbl.pack()

        # ----------------------------------------------------------------------
        # 2. GİRİŞ KARTI (Link ve Klasör)
        # ----------------------------------------------------------------------
        card = ctk.CTkFrame(
            container,
            fg_color=THEME["bg_card"],
            border_color=THEME["border_subtle"],
            border_width=1,
            corner_radius=8
        )
        card.pack(fill="x", pady=(0, 14))

        card_content = ctk.CTkFrame(card, fg_color="transparent")
        card_content.pack(fill="x", padx=16, pady=16)

        # --- Video Linki ---
        url_label = ctk.CTkLabel(
            card_content,
            text="VİDEO LİNKİ",
            font=("Segoe UI", 10, "bold"),
            text_color=THEME["text_muted"]
        )
        url_label.pack(anchor="w", pady=(0, 4))

        url_box = ctk.CTkFrame(card_content, fg_color="transparent")
        url_box.pack(fill="x", pady=(0, 14))

        self.url_entry = ctk.CTkEntry(
            url_box,
            textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=38,
            corner_radius=6,
            fg_color=THEME["bg_input"],
            border_color=THEME["border_input"],
            border_width=1,
            text_color=THEME["text_primary"],
            placeholder_text_color=THEME["text_muted"],
            font=("Segoe UI", 12)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda event: self.start_download())

        paste_btn = ctk.CTkButton(
            url_box,
            text="📋 Yapıştır",
            command=self.paste_from_clipboard,
            width=90,
            height=38,
            corner_radius=6,
            fg_color=THEME["btn_secondary_bg"],
            hover_color=THEME["btn_secondary_hover"],
            border_color=THEME["btn_secondary_border"],
            border_width=1,
            text_color=THEME["btn_secondary_text"],
            font=("Segoe UI", 11)
        )
        paste_btn.pack(side="right")

        # --- Kayıt Klasörü ---
        folder_label = ctk.CTkLabel(
            card_content,
            text="KAYDEDİLECEK KLASÖR",
            font=("Segoe UI", 10, "bold"),
            text_color=THEME["text_muted"]
        )
        folder_label.pack(anchor="w", pady=(0, 4))

        folder_box = ctk.CTkFrame(card_content, fg_color="transparent")
        folder_box.pack(fill="x")

        self.folder_entry = ctk.CTkEntry(
            folder_box,
            textvariable=self.download_dir,
            height=38,
            corner_radius=6,
            fg_color=THEME["bg_input"],
            border_color=THEME["border_input"],
            border_width=1,
            text_color=THEME["text_primary"],
            font=("Segoe UI", 11)
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            folder_box,
            text="📁 Klasör Seç",
            command=self.browse_folder,
            width=100,
            height=38,
            corner_radius=6,
            fg_color=THEME["btn_secondary_bg"],
            hover_color=THEME["btn_secondary_hover"],
            border_color=THEME["btn_secondary_border"],
            border_width=1,
            text_color=THEME["btn_secondary_text"],
            font=("Segoe UI", 11)
        )
        browse_btn.pack(side="left", padx=(0, 6))

        open_dir_btn = ctk.CTkButton(
            folder_box,
            text="📂 Aç",
            command=self.open_current_folder,
            width=65,
            height=38,
            corner_radius=6,
            fg_color=THEME["btn_secondary_bg"],
            hover_color=THEME["btn_secondary_hover"],
            border_color=THEME["btn_secondary_border"],
            border_width=1,
            text_color=THEME["btn_secondary_text"],
            font=("Segoe UI", 11)
        )
        open_dir_btn.pack(side="left")

        # ----------------------------------------------------------------------
        # 3. KONTROLLER VE İLERLEME
        # ----------------------------------------------------------------------
        controls = ctk.CTkFrame(container, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))

        btn_box = ctk.CTkFrame(controls, fg_color="transparent")
        btn_box.pack(side="left")

        self.download_btn = ctk.CTkButton(
            btn_box,
            text="⬇  Videoyu İndir",
            command=self.start_download,
            height=38,
            width=140,
            corner_radius=6,
            fg_color=THEME["btn_primary_bg"],
            hover_color=THEME["btn_primary_hover"],
            text_color=THEME["btn_primary_text"],
            font=("Segoe UI", 12, "bold")
        )
        self.download_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_box,
            text="⏹  İptal Et",
            command=self.cancel_download,
            height=38,
            width=100,
            corner_radius=6,
            fg_color=THEME["btn_danger_bg"],
            hover_color=THEME["btn_danger_hover"],
            border_color=THEME["btn_danger_border"],
            border_width=1,
            text_color=THEME["btn_danger_text"],
            font=("Segoe UI", 11, "bold"),
            state="disabled"
        )
        self.cancel_btn.pack(side="left")

        # Durum ve Hız Bilgisi
        status_box = ctk.CTkFrame(controls, fg_color="transparent")
        status_box.pack(side="right")

        self.status_label = ctk.CTkLabel(
            status_box,
            textvariable=self.status_var,
            font=("Segoe UI", 12, "bold"),
            text_color=THEME["status_ready"]
        )
        self.status_label.pack(side="right")

        self.speed_label = ctk.CTkLabel(
            status_box,
            textvariable=self.speed_eta_var,
            font=("Segoe UI", 11),
            text_color=THEME["text_secondary"]
        )
        self.speed_label.pack(side="right", padx=(0, 12))

        # İlerleme Çubuğu (Düz Minimalist Çizgi)
        self.progress_bar = ctk.CTkProgressBar(
            container,
            height=4,
            corner_radius=2,
            fg_color=THEME["progress_bg"],
            progress_color=THEME["progress_fill"]
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 12))

        # ----------------------------------------------------------------------
        # 4. İŞLEM GÜNLÜĞÜ (TERMINAL)
        # ----------------------------------------------------------------------
        log_header = ctk.CTkFrame(container, fg_color="transparent")
        log_header.pack(fill="x", pady=(0, 6))

        log_title = ctk.CTkLabel(
            log_header,
            text="İŞLEM GÜNLÜĞÜ",
            font=("Segoe UI", 10, "bold"),
            text_color=THEME["text_muted"]
        )
        log_title.pack(side="left")

        clear_btn = ctk.CTkButton(
            log_header,
            text="Temizle",
            command=self.clear_logs,
            width=50,
            height=20,
            fg_color="transparent",
            hover_color=THEME["bg_card"],
            text_color=THEME["text_muted"],
            font=("Segoe UI", 10, "underline")
        )
        clear_btn.pack(side="right")

        self.console_box = ctk.CTkTextbox(
            container,
            fg_color=THEME["bg_console"],
            text_color=THEME["text_secondary"],
            border_color=THEME["border_subtle"],
            border_width=1,
            corner_radius=6,
            font=("Consolas", 10),
            wrap="word",
            activate_scrollbars=True
        )
        self.console_box.pack(fill="both", expand=True)

        # Karşılama
        self.append_log("Uygulama hazır.\n")
        self.append_log(f"yt-dlp: {' '.join(self.ytdlp_cmd)}\n")
        self.append_log(f"Hedef Klasör: {self.download_dir.get()}\n")
        self.append_log("Format: yt-dlp -S \"res:1080,vcodec:h264,acodec:aac\" --merge-output-format mp4\n\n")

    def paste_from_clipboard(self):
        try:
            content = self.clipboard_get().strip()
            if content:
                self.url_var.set(content)
        except Exception:
            pass

    def browse_folder(self):
        folder = filedialog.askdirectory(
            title="Videoların Kaydedileceği Klasörü Seçin",
            initialdir=self.download_dir.get()
        )
        if folder:
            self.download_dir.set(folder)
            save_config(folder)
            self.append_log(f"Klasör seçildi: {folder}\n")

    def open_current_folder(self):
        path = self.download_dir.get()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Klasör Bulunamadı", f"Belirtilen klasör mevcut değil:\n{path}")

    def clear_logs(self):
        self.console_box.delete("1.0", "end")

    def append_log(self, text):
        self.console_box.insert("end", text)
        self.console_box.see("end")

    def set_status(self, text, state="default"):
        self.status_var.set(text)
        if state == "active":
            self.status_label.configure(text_color=THEME["status_active"])
        elif state == "success":
            self.status_label.configure(text_color=THEME["status_success"])
        elif state == "error":
            self.status_label.configure(text_color=THEME["status_error"])
        else:
            self.status_label.configure(text_color=THEME["status_ready"])

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        folder = self.download_dir.get().strip()

        if not url:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir YouTube video linki girin.")
            self.url_entry.focus_set()
            return

        if not folder:
            messagebox.showwarning("Eksik Bilgi", "Lütfen videonun kaydedileceği klasörü seçin.")
            return

        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Hata", f"Hedef klasör oluşturulamadı:\n{e}")
                return

        save_config(folder)

        self.is_downloading = True
        self.is_cancelled = False
        self.download_btn.configure(state="disabled", fg_color=THEME["btn_secondary_bg"], text_color=THEME["text_muted"])
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.speed_eta_var.set("")
        self.set_status("İndirme başlatılıyor...", state="active")

        # Temizlik takibi
        self.download_start_time = time.time()
        self.tracked_files = set()
        try:
            self.files_before_download = set(os.listdir(folder))
        except Exception:
            self.files_before_download = set()

        self.append_log("\n" + "—" * 60 + "\n")
        self.append_log(f"İndirme Başlatıldı\n")
        self.append_log(f"Link: {url}\n")
        self.append_log(f"Hedef: {folder}\n")

        thread = threading.Thread(target=self._run_ytdlp_process, args=(url, folder), daemon=True)
        thread.start()

    def _run_ytdlp_process(self, url, folder):
        cmd = [
            *self.ytdlp_cmd,
            "-S", "res:1080,vcodec:h264,acodec:aac",
            "--merge-output-format", "mp4",
            "-P", folder,
            "-o", "%(title)s.%(ext)s",
            "--newline",
            "--no-mtime",
            url
        ]

        self.after(0, lambda: self.append_log(f"Komut: {' '.join(cmd)}\n\n"))

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.download_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags
            )

            prog_regex = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)")
            dest_regex = re.compile(r"\[download\]\s+Destination:\s+(.+)")
            merger_regex = re.compile(r"\[Merger\]\s+Merging formats into\s+\"?([^\"\n]+)\"?")
            alrd_regex = re.compile(r"\[download\]\s+(.+?)\s+has already been downloaded")

            for raw_line in iter(self.download_process.stdout.readline, ""):
                if self.is_cancelled:
                    break
                if not raw_line:
                    break

                line = raw_line.strip()

                m_dest = dest_regex.search(line) or merger_regex.search(line) or alrd_regex.search(line)
                if m_dest:
                    fpath = m_dest.group(1).strip().strip('"')
                    self.tracked_files.add(fpath)

                match = prog_regex.search(line)
                if match:
                    percent = float(match.group(1))
                    size = match.group(2)
                    speed = match.group(3)
                    eta = match.group(4)
                    if not self.is_cancelled:
                        self.after(0, self._update_progress, percent, speed, eta)
                elif "[Merger]" in line or "Merging formats" in line:
                    if not self.is_cancelled:
                        self.after(0, lambda: self.set_status("MP4 birleştiriliyor...", state="active"))
                elif "Destination:" in line:
                    if not self.is_cancelled:
                        self.after(0, lambda: self.set_status("İndiriliyor...", state="active"))

                if not self.is_cancelled:
                    self.after(0, lambda l=raw_line: self.append_log(l))

            try:
                self.download_process.stdout.close()
            except Exception:
                pass

            if self.is_cancelled:
                return

            return_code = self.download_process.wait()

            if self.is_cancelled:
                return

            if return_code == 0:
                self.after(0, self._on_download_success, folder)
            else:
                self.after(0, self._on_download_error, f"yt-dlp çıkış kodu: {return_code}")

        except Exception as e:
            if not self.is_cancelled:
                self.after(0, self._on_download_error, str(e))
        finally:
            if not self.is_cancelled:
                self.after(0, self._reset_ui)

    def _update_progress(self, percent, speed, eta):
        self.progress_bar.set(percent / 100.0)
        self.speed_eta_var.set(f"{speed} • Kalan: {eta}")
        self.set_status(f"%{percent:.1f}", state="active")

    def _on_download_success(self, folder):
        self.progress_bar.set(1.0)
        self.speed_eta_var.set("")
        self.set_status("Tamamlandı ✓", state="success")
        self.append_log("\n✓ Video başarıyla indirildi ve MP4 olarak kaydedildi.\n")

        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        ans = messagebox.askyesno(
            "İndirme Tamamlandı",
            "Video başarıyla indirildi!\n\nDosyanın bulunduğu klasörü açmak ister misiniz?"
        )
        if ans:
            self.open_current_folder()

    def _on_download_error(self, err_msg):
        if self.is_cancelled:
            return
        self.set_status("Hata", state="error")
        self.append_log(f"\n✕ Hata: {err_msg}\n")
        messagebox.showerror("İndirme Hatası", f"İndirme sırasında bir sorun oluştu:\n{err_msg}")

    def cancel_download(self):
        """İndirmeyi durdurur ve yarım kalan parçaları temizler."""
        if not self.is_downloading:
            return

        self.is_cancelled = True
        self.cancel_btn.configure(state="disabled")
        self.set_status("İptal ediliyor...", state="error")
        self.append_log("\nİptal isteği alındı. İşlemler durduruluyor ve yarım dosyalar temizleniyor...\n")

        proc = self.download_process
        target_dir = self.download_dir.get().strip()
        tracked = set(self.tracked_files)
        files_before = set(self.files_before_download)
        start_t = self.download_start_time

        def _kill_and_cleanup():
            if proc:
                kill_process_tree(proc)

            time.sleep(0.3)
            deleted = cleanup_cancelled_downloads(target_dir, tracked, files_before, start_t)

            self.after(0, lambda: self._on_download_cancelled(deleted))

        threading.Thread(target=_kill_and_cleanup, daemon=True).start()

    def _on_download_cancelled(self, deleted_files=None):
        self.progress_bar.set(0)
        self.speed_eta_var.set("")
        self.set_status("İptal Edildi ⏹", state="error")
        self.append_log("İndirme durduruldu.\n")

        if deleted_files:
            for fname in deleted_files:
                self.append_log(f"Temizlenen yarım dosya: {fname}\n")
        else:
            self.append_log("Klasörde temizlenecek yarım dosya bulunamadı.\n")

        self._reset_ui()

    def _reset_ui(self):
        self.is_downloading = False
        self.download_process = None
        self.download_btn.configure(
            state="normal",
            fg_color=THEME["btn_primary_bg"],
            text_color=THEME["btn_primary_text"]
        )
        self.cancel_btn.configure(state="disabled")

    def on_close(self):
        """Pencere kapatıldığında süreçleri sonlandırır ve yarım dosyaları temizler."""
        if self.is_downloading and self.download_process:
            self.is_cancelled = True
            kill_process_tree(self.download_process)
            time.sleep(0.2)
            cleanup_cancelled_downloads(
                self.download_dir.get().strip(),
                self.tracked_files,
                self.files_before_download,
                self.download_start_time
            )
        self.destroy()


if __name__ == "__main__":
    app = DownloaderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
