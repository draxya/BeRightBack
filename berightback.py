#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeRightBack - LoL Otomatik Maç Kabul + Matchmaking Timer
Enhanced Version with Console, Language Support & Persistent Settings
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import queue

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError:
    print("Gerekli modüller yükleniyor...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter", "pillow"])
    import customtkinter as ctk
    from PIL import Image, ImageTk

import requests
import psutil
import urllib3
from requests.auth import HTTPBasicAuth

# SSL uyarılarını devre dışı bırak
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CustomTkinter ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ConfigManager:
    """Ayarları yönetir"""
    
    def __init__(self):
        self.config_dir = Path.home() / "Documents" / "BeRightBack"
        self.config_file = self.config_dir / "config.json"
        self.ensure_config_dir()
        self.config = self.load_config()
    
    def ensure_config_dir(self):
        """Config klasörünü oluştur"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> dict:
        """Config dosyasını yükle"""
        default_config = {
            "language": "tr",
            "console_visible": False,
            "stats": {
                "matches_found": 0,
                "matches_accepted": 0,
                "queue_sessions": 0
            },
            "window": {
                "width": 1000,
                "height": 700
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in loaded_config[key]:
                                    loaded_config[key][subkey] = subvalue
                    return loaded_config
        except Exception as e:
            print(f"Config load error: {e}")
        
        return default_config
    
    def save_config(self):
        """Config dosyasını kaydet"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def get(self, key, default=None):
        """Config değeri al"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, default)
            if value is None:
                return default
        return value
    
    def set(self, key, value):
        """Config değeri ayarla"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save_config()

class ConsoleHandler(logging.Handler):
    """GUI konsolu için log handler"""
    
    def __init__(self, console_callback):
        super().__init__()
        self.console_callback = console_callback
    
    def emit(self, record):
        log_entry = self.format(record)
        if self.console_callback:
            self.console_callback(log_entry)

class MatchmakingTimer:
    """LoL tarzı matchmaking timer sistemi"""
    
    def __init__(self, gui_callback=None):
        self.gui_callback = gui_callback
        self.timer_running = False
        self.timer_paused = False
        self.timer_thread = None
        self.remaining_time = 0
        self.total_time = 0
        self.on_timer_complete = None
        
        # Logger
        self.logger = logging.getLogger('Timer')
        self.logger.setLevel(logging.INFO)
    
    def start_timer(self, minutes, seconds, callback=None):
        """Timer başlat"""
        if self.timer_running:
            return False
        
        self.total_time = minutes * 60 + seconds
        self.remaining_time = self.total_time
        self.on_timer_complete = callback
        self.timer_running = True
        self.timer_paused = False
        
        self.logger.info(f"🕒 Timer başlatıldı: {minutes}:{seconds:02d}")
        
        self.timer_thread = threading.Thread(target=self._timer_worker, daemon=True)
        self.timer_thread.start()
        return True
    
    def stop_timer(self):
        """Timer durdur"""
        if self.timer_running:
            self.logger.info("⏹️ Timer durduruldu")
        self.timer_running = False
        self.timer_paused = False
        self.remaining_time = 0
    
    def pause_timer(self):
        """Timer duraklat"""
        self.timer_paused = True
        self.logger.info("⏸️ Timer duraklatıldı")
    
    def resume_timer(self):
        """Timer devam ettir"""
        self.timer_paused = False
        self.logger.info("▶️ Timer devam ettiriliyor")
    
    def _timer_worker(self):
        """Timer worker thread"""
        while self.timer_running and self.remaining_time > 0:
            time.sleep(1)
            if self.timer_running and not self.timer_paused:
                self.remaining_time -= 1
        
        if self.timer_running and self.remaining_time <= 0:
            self.logger.info("⏰ Timer tamamlandı! Matchmaking başlatılıyor...")
            if self.on_timer_complete:
                self.on_timer_complete()
        
        self.timer_running = False
    
    def get_time_display(self):
        """Zamanı MM:SS formatında döndür"""
        if self.remaining_time <= 0:
            return "00:00"
        
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_progress(self):
        """Timer ilerlemesini 0-1 arası döndür"""
        if self.total_time <= 0:
            return 0
        return 1 - (self.remaining_time / self.total_time)

class LoLClient:
    """LoL Client API wrapper"""
    
    def __init__(self):
        self.port = None
        self.token = None
        self.session = requests.Session()
        self.session.verify = False
        self.connected = False
        self.in_game = False
        
        # Logger
        self.logger = logging.getLogger('LoLClient')
        self.logger.setLevel(logging.INFO)
    
    def find_client(self) -> bool:
        """LoL Client bul ve bağlan"""
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process.info['name'] == "LeagueClientUx.exe":
                        cmdline = process.info['cmdline']
                        if not cmdline:
                            continue
                        
                        port = None
                        token = None
                        
                        for arg in cmdline:
                            if "--app-port=" in arg:
                                port = arg.split("=")[1]
                            elif "--remoting-auth-token=" in arg:
                                token = arg.split("=")[1]
                        
                        if port and token:
                            self.port = port
                            self.token = token
                            self.session.auth = HTTPBasicAuth("riot", token)
                            if self.test_connection():
                                if not self.connected:
                                    self.logger.info(f"🟢 LoL Client'a bağlanıldı (Port: {port})")
                                return True
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"❌ Client taramasında hata: {e}")
        
        if self.connected:
            self.logger.warning("🔴 LoL Client bağlantısı kesildi")
        self.connected = False
        self.in_game = False
        return False
    
    def test_connection(self) -> bool:
        """Bağlantıyı test et"""
        try:
            url = f"https://127.0.0.1:{self.port}/lol-summoner/v1/current-summoner"
            response = self.session.get(url, timeout=5)
            was_connected = self.connected
            self.connected = response.status_code == 200
            
            if self.connected:
                self.check_game_status()
            
            return self.connected
        except Exception:
            self.connected = False
            self.in_game = False
            return False
    
    def check_game_status(self):
        """Oyun durumunu kontrol et"""
        try:
            url = f"https://127.0.0.1:{self.port}/lol-gameflow/v1/gameflow-phase"
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                phase = response.json()
                was_in_game = self.in_game
                self.in_game = phase in ["InProgress", "GameStart", "WaitingForStats"]
                
                if self.in_game and not was_in_game:
                    self.logger.info("🎮 Oyuna girdi")
                elif not self.in_game and was_in_game:
                    self.logger.info("🏠 Oyundan çıktı")
                    
        except Exception:
            pass
    
    def get_ready_check_status(self) -> Optional[Dict]:
        """Ready check durumunu al"""
        try:
            url = f"https://127.0.0.1:{self.port}/lol-matchmaking/v1/ready-check"
            response = self.session.get(url, timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    def accept_match(self) -> bool:
        """Maçı kabul et"""
        try:
            url = f"https://127.0.0.1:{self.port}/lol-matchmaking/v1/ready-check/accept"
            response = self.session.post(url, timeout=5)
            success = response.status_code == 204
            if success:
                self.logger.info("✅ Maç kabul edildi!")
            return success
        except Exception as e:
            self.logger.error(f"❌ Maç kabul hatası: {e}")
            return False
    
    def start_matchmaking(self) -> bool:
        """Matchmaking başlat"""
        try:
            url = f"https://127.0.0.1:{self.port}/lol-lobby/v2/lobby/matchmaking/search"
            response = self.session.post(url, timeout=5)
            success = response.status_code == 204
            if success:
                self.logger.info("🔍 Matchmaking başlatıldı")
            return success
        except Exception as e:
            self.logger.error(f"❌ Matchmaking başlatma hatası: {e}")
            return False

class BeRightBackGUI:
    """BeRightBack Ana GUI"""
    
    def __init__(self):
        self.root = ctk.CTk()
        
        # Config Manager
        self.config = ConfigManager()
        
        # Setup
        self.setup_window()
        self.setup_colors()
        self.setup_translations()
        self.setup_logging()
        
        # Components
        self.client = LoLClient()
        self.timer = MatchmakingTimer(self)
        
        # State
        self.auto_accept_running = False
        self.console_visible = self.config.get('console_visible', False)
        self.last_ready_check_id = None  # Son kabul edilen ready check ID'si
        self.waiting_for_others = False  # Diğer oyuncuları bekleme durumu
        
        self.create_widgets()
        self.load_stats()
        self.start_monitoring()
        self.start_timer_update()  # Timer için ayrı güncelleme
    
    def setup_window(self):
        """Pencere ayarları"""
        self.root.title("BeRightBack - LoL Auto Accept & Queue")
        
        width = self.config.get('window.width', 1000)
        height = self.config.get('window.height', 700)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(800, 600)
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Grid configuration for full window coverage
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
    
    def setup_colors(self):
        """Renk paleti"""
        self.colors = {
            "bg_primary": "#0F1419",
            "bg_secondary": "#1A1D29", 
            "accent": "#00D4FF",
            "success": "#28A745",  # Daha yumuşak yeşil
            "success_hover": "#238B3D",
            "warning": "#FFB800",
            "error": "#FF4757",
            "error_hover": "#E63946",
            "text": "#FFFFFF",
            "text_dim": "#8FA2B7",
            "disabled": "#6C757D"  # Gri ton
        }
    
    def setup_translations(self):
        """Dil çevirileri"""
        self.translations = {
            "tr": {
                "title": "BeRightBack - LoL Otomatik Maç Kabul & Arama",
                "subtitle": "LoL Auto Accept & Matchmaking Timer",
                "auto_accept": "Otomatik Maç Kabul",
                "auto_accept_desc": "Maç bulunduğunda otomatik olarak kabul eder",
                "auto_queue": "Otomatik Maç Arama",
                "auto_queue_desc": "Belirlenen süre sonra otomatik maç arar",
                "start": "Başlat",
                "stop": "Durdur",
                "pause": "Duraklat",
                "resume": "Devam",
                "minutes": "Dakika",
                "seconds": "Saniye",
                "matches_found": "Bulunan Maçlar",
                "matches_accepted": "Kabul Edilen",
                "queue_sessions": "Toplam Arama",
                "connected": "Bağlı",
                "disconnected": "Bağlantısız",
                "in_game": "Oyunda",
                "waiting_client": "LoL Client bekleniyor...",
                "ready": "Hazır",
                "language": "Dil",
                "console": "Konsol",
                "show_console": "Konsolu Göster",
                "hide_console": "Konsolu Gizle",
                "clear_console": "Temizle",
                "settings": "Ayarlar",
                "version": "v3.0 - Enhanced Edition"
            },
            "en": {
                "title": "BeRightBack - LoL Auto Accept & Queue",
                "subtitle": "LoL Auto Accept & Matchmaking Timer", 
                "auto_accept": "Auto Match Accept",
                "auto_accept_desc": "Automatically accepts matches when found",
                "auto_queue": "Auto Queue Timer",
                "auto_queue_desc": "Automatically starts queue after set time",
                "start": "Start",
                "stop": "Stop",
                "pause": "Pause",
                "resume": "Resume",
                "minutes": "Minutes",
                "seconds": "Seconds",
                "matches_found": "Matches Found",
                "matches_accepted": "Accepted",
                "queue_sessions": "Total Queues",
                "connected": "Connected",
                "disconnected": "Disconnected",
                "in_game": "In Game",
                "waiting_client": "Waiting for LoL Client...",
                "ready": "Ready",
                "language": "Language",
                "console": "Console",
                "show_console": "Show Console",
                "hide_console": "Hide Console",
                "clear_console": "Clear",
                "settings": "Settings",
                "version": "v3.0 - Enhanced Edition"
            }
        }
        
        self.current_language = self.config.get('language', 'tr')
    
    def setup_logging(self):
        """Logging ayarla"""
        self.console_messages = []
        
        # Console handler
        console_handler = ConsoleHandler(self.add_console_message)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add to all loggers
        logging.getLogger('Timer').addHandler(console_handler)
        logging.getLogger('LoLClient').addHandler(console_handler)
        logging.getLogger('BeRightBack').addHandler(console_handler)
        
        # Main logger
        self.logger = logging.getLogger('BeRightBack')
        self.logger.setLevel(logging.INFO)
        self.logger.info("🚀 BeRightBack başlatıldı")
    
    def get_text(self, key):
        """Çeviri metni al"""
        return self.translations[self.current_language].get(key, key)
    
    def create_widgets(self):
        """Widget'ları oluştur"""
        # Ana container - tam pencereyi kapla
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg_primary"], corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self.create_header()
        
        # Content
        self.create_content()
        
        # Console (başlangıçta gizli)
        self.create_console()
    
    def create_header(self):
        """Header oluştur"""
        header = ctk.CTkFrame(self.main_frame, height=80, fg_color=self.colors["bg_secondary"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        
        # Logo & Title
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        logo = ctk.CTkLabel(left_frame, text="⚡", font=ctk.CTkFont(size=24), text_color=self.colors["accent"])
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 15))
        
        self.title_label = ctk.CTkLabel(
            left_frame,
            text=self.get_text("title"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text"]
        )
        self.title_label.grid(row=0, column=1, sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            left_frame,
            text=self.get_text("subtitle"),
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_dim"]
        )
        self.subtitle_label.grid(row=1, column=1, sticky="w")
        
        # Settings & Controls
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="e", padx=20, pady=15)
        
        # Language selector
        self.lang_option = ctk.CTkOptionMenu(
            right_frame,
            values=["Türkçe", "English"],
            command=self.change_language,
            width=100,
            fg_color=self.colors["accent"]
        )
        self.lang_option.grid(row=0, column=0, padx=(0, 10))
        self.lang_option.set("Türkçe" if self.current_language == "tr" else "English")
        
        # Console toggle
        console_text = self.get_text("hide_console") if self.console_visible else self.get_text("show_console")
        self.console_toggle_btn = ctk.CTkButton(
            right_frame,
            text=f"📊 {console_text}",
            command=self.toggle_console,
            width=120,
            fg_color=self.colors["warning"]
        )
        self.console_toggle_btn.grid(row=0, column=1)
        
        # Connection status
        center_frame = ctk.CTkFrame(header, fg_color="transparent")
        center_frame.grid(row=0, column=1, pady=15)
        
        self.connection_label = ctk.CTkLabel(
            center_frame,
            text="🔴 Disconnected",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["error"]
        )
        self.connection_label.pack()
    
    def create_content(self):
        """İçerik oluştur"""
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Sol panel - Auto Accept
        self.create_auto_accept_panel()
        
        # Sağ panel - Auto Queue Timer
        self.create_auto_queue_panel()
        
        # Alt status bar
        self.create_status_bar()
    
    def create_auto_accept_panel(self):
        """Auto Accept paneli"""
        panel = ctk.CTkFrame(self.content_frame, fg_color=self.colors["bg_secondary"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        
        # Title
        self.auto_accept_title = ctk.CTkLabel(
            panel,
            text=f"🎯 {self.get_text('auto_accept')}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text"]
        )
        self.auto_accept_title.grid(row=0, column=0, pady=(20, 10))
        
        # Description
        self.auto_accept_desc = ctk.CTkLabel(
            panel,
            text=self.get_text("auto_accept_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_dim"]
        )
        self.auto_accept_desc.grid(row=1, column=0, pady=(0, 20))
        
        # Start/Stop button
        self.auto_accept_btn = ctk.CTkButton(
            panel,
            text=f"▶️ {self.get_text('start')}",
            command=self.toggle_auto_accept,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.colors["success"],
            hover_color=self.colors["success_hover"],
            width=200,
            height=50
        )
        self.auto_accept_btn.grid(row=2, column=0, pady=20)
        
        # Stats
        stats_frame = ctk.CTkFrame(panel, fg_color=self.colors["bg_primary"])
        stats_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(20, 30))
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        
        # Matches found
        self.matches_found_label = ctk.CTkLabel(
            stats_frame,
            text=f"{self.get_text('matches_found')}\n0",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text"]
        )
        self.matches_found_label.grid(row=0, column=0, pady=20)
        
        # Matches accepted
        self.matches_accepted_label = ctk.CTkLabel(
            stats_frame,
            text=f"{self.get_text('matches_accepted')}\n0",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["success"]
        )
        self.matches_accepted_label.grid(row=0, column=1, pady=20)
    
    def create_auto_queue_panel(self):
        """Auto Queue Timer paneli"""
        panel = ctk.CTkFrame(self.content_frame, fg_color=self.colors["bg_secondary"])
        panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        panel.grid_columnconfigure(0, weight=1)
        
        # Title
        self.auto_queue_title = ctk.CTkLabel(
            panel,
            text=f"⏰ {self.get_text('auto_queue')}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text"]
        )
        self.auto_queue_title.grid(row=0, column=0, pady=(20, 10))
        
        # Description
        self.auto_queue_desc = ctk.CTkLabel(
            panel,
            text=self.get_text("auto_queue_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_dim"]
        )
        self.auto_queue_desc.grid(row=1, column=0, pady=(0, 20))
        
        # Timer settings
        timer_settings = ctk.CTkFrame(panel, fg_color=self.colors["bg_primary"])
        timer_settings.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        timer_settings.grid_columnconfigure(0, weight=1)
        timer_settings.grid_columnconfigure(1, weight=1)
        
        # Minutes
        self.min_label = ctk.CTkLabel(timer_settings, text=self.get_text("minutes"), text_color=self.colors["text"])
        self.min_label.grid(row=0, column=0, pady=(15, 5))
        
        self.minutes_var = ctk.StringVar(value="5")
        self.minutes_entry = ctk.CTkEntry(
            timer_settings, 
            textvariable=self.minutes_var,
            width=80,
            justify="center"
        )
        self.minutes_entry.grid(row=1, column=0, pady=(0, 15), padx=10)
        
        # Seconds
        self.sec_label = ctk.CTkLabel(timer_settings, text=self.get_text("seconds"), text_color=self.colors["text"])
        self.sec_label.grid(row=0, column=1, pady=(15, 5))
        
        self.seconds_var = ctk.StringVar(value="0")
        self.seconds_entry = ctk.CTkEntry(
            timer_settings,
            textvariable=self.seconds_var,
            width=80,
            justify="center"
        )
        self.seconds_entry.grid(row=1, column=1, pady=(0, 15), padx=10)
        
        # Timer display
        self.timer_display = ctk.CTkLabel(
            panel,
            text="00:00",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=self.colors["accent"]
        )
        self.timer_display.grid(row=3, column=0, pady=15)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            panel,
            width=250,
            progress_color=self.colors["accent"]
        )
        self.progress_bar.grid(row=4, column=0, pady=10)
        self.progress_bar.set(0)
        
        # Control buttons
        btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=15)
        
        self.start_timer_btn = ctk.CTkButton(
            btn_frame,
            text=f"▶️ {self.get_text('start')}",
            command=self.start_queue_timer,
            fg_color=self.colors["success"],
            hover_color=self.colors["success_hover"],
            width=120,
            height=40
        )
        self.start_timer_btn.grid(row=0, column=0, padx=5)
        
        self.stop_timer_btn = ctk.CTkButton(
            btn_frame,
            text=f"⏹️ {self.get_text('stop')}",
            command=self.stop_queue_timer,
            fg_color=self.colors["error"],
            hover_color=self.colors["error_hover"],
            width=120,
            height=40,
            state="disabled"
        )
        self.stop_timer_btn.grid(row=0, column=1, padx=5)
        
        # Queue sessions counter
        self.queue_sessions_label = ctk.CTkLabel(
            panel,
            text=f"{self.get_text('queue_sessions')}: 0",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_dim"]
        )
        self.queue_sessions_label.grid(row=6, column=0, pady=(10, 30))
    
    def create_status_bar(self):
        """Alt durum çubuğu"""
        self.status_frame = ctk.CTkFrame(self.content_frame, height=50, fg_color=self.colors["bg_secondary"])
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        self.status_frame.grid_propagate(False)
        self.status_frame.grid_columnconfigure(1, weight=1)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=self.get_text("waiting_client"),
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_dim"]
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Version
        self.version_label = ctk.CTkLabel(
            self.status_frame,
            text=self.get_text("version"),
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_dim"]
        )
        self.version_label.grid(row=0, column=2, padx=20, pady=15, sticky="e")
    
    def create_console(self):
        """Konsol oluştur"""
        self.console_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["bg_secondary"])
        # Başlangıçta gizli
        if not self.console_visible:
            self.console_frame.grid_remove()
        else:
            self.console_frame.grid(row=2, column=0, sticky="nsew", pady=(15, 0))
            self.main_frame.grid_rowconfigure(2, weight=1)
        
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)
        
        # Console header
        console_header = ctk.CTkFrame(self.console_frame, height=40, fg_color=self.colors["bg_primary"])
        console_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        console_header.grid_propagate(False)
        console_header.grid_columnconfigure(1, weight=1)
        
        self.console_title = ctk.CTkLabel(
            console_header,
            text=f"📊 {self.get_text('console')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text"]
        )
        self.console_title.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.clear_console_btn = ctk.CTkButton(
            console_header,
            text=f"🗑️ {self.get_text('clear_console')}",
            command=self.clear_console,
            width=80,
            height=25,
            font=ctk.CTkFont(size=10),
            fg_color=self.colors["error"],
            hover_color=self.colors["error_hover"]
        )
        self.clear_console_btn.grid(row=0, column=2, padx=15, pady=7.5, sticky="e")
        
        # Console text area (read-only)
        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
            fg_color=self.colors["bg_primary"],
            text_color=self.colors["text"],
            scrollbar_button_color=self.colors["accent"]
        )
        self.console_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        # Make read-only
        self.console_text.configure(state="disabled")
    
    def toggle_console(self):
        """Konsolu göster/gizle"""
        self.console_visible = not self.console_visible
        self.config.set('console_visible', self.console_visible)
        
        if self.console_visible:
            self.console_frame.grid(row=2, column=0, sticky="nsew")
            self.main_frame.grid_rowconfigure(2, weight=1)
            self.console_toggle_btn.configure(text=f"📊 {self.get_text('hide_console')}")
        else:
            self.console_frame.grid_remove()
            self.main_frame.grid_rowconfigure(2, weight=0)
            self.console_toggle_btn.configure(text=f"📊 {self.get_text('show_console')}")
    
    def add_console_message(self, message):
        """Konsola mesaj ekle"""
        if hasattr(self, 'console_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}\n"
            
            self.console_text.configure(state="normal")
            self.console_text.insert("end", formatted_message)
            self.console_text.configure(state="disabled")
            self.console_text.see("end")
            
            # Keep only last 1000 lines
            lines = self.console_text.get("1.0", "end").split('\n')
            if len(lines) > 1000:
                self.console_text.configure(state="normal")
                self.console_text.delete("1.0", f"{len(lines)-1000}.0")
                self.console_text.configure(state="disabled")
    
    def clear_console(self):
        """Konsolu temizle"""
        if hasattr(self, 'console_text'):
            self.console_text.configure(state="normal")
            self.console_text.delete("1.0", "end")
            self.console_text.configure(state="disabled")
            self.logger.info("🗑️ Konsol temizlendi")
    
    def toggle_auto_accept(self):
        """Auto Accept başlat/durdur"""
        if not self.client.connected:
            self.show_status("❌ LoL Client'a bağlı değil!", "error")
            return
        
        if self.client.in_game:
            self.show_status("⚠️ Oyundayken başlatılamaz!", "warning")
            return
        
        self.auto_accept_running = not self.auto_accept_running
        self.update_button_states()
        
        if self.auto_accept_running:
            self.logger.info("🟢 Otomatik maç kabul başlatıldı")
        else:
            self.logger.info("🔴 Otomatik maç kabul durduruldu")
    
    def update_button_states(self):
        """Buton durumlarını güncelle"""
        # Auto Accept button
        if self.client.in_game:
            # Oyunda - butonları devre dışı bırak
            self.auto_accept_btn.configure(
                text=f"▶️ {self.get_text('start')}",
                fg_color=self.colors["disabled"],
                hover_color=self.colors["disabled"],
                state="disabled"
            )
            self.auto_accept_running = False
        elif self.auto_accept_running:
            # Çalışıyor
            self.auto_accept_btn.configure(
                text=f"⏹️ {self.get_text('stop')}",
                fg_color=self.colors["error"],
                hover_color=self.colors["error_hover"],
                state="normal"
            )
        else:
            # Durmuş
            self.auto_accept_btn.configure(
                text=f"▶️ {self.get_text('start')}",
                fg_color=self.colors["success"],
                hover_color=self.colors["success_hover"],
                state="normal"
            )
        
        # Timer buttons
        if self.client.in_game:
            self.start_timer_btn.configure(
                fg_color=self.colors["disabled"],
                hover_color=self.colors["disabled"],
                state="disabled"
            )
            if self.timer.timer_running:
                self.stop_queue_timer()
        elif self.timer.timer_running:
            self.start_timer_btn.configure(state="disabled")
            self.stop_timer_btn.configure(state="normal")
        else:
            self.start_timer_btn.configure(
                fg_color=self.colors["success"],
                hover_color=self.colors["success_hover"],
                state="normal"
            )
            self.stop_timer_btn.configure(state="disabled")
    
    def start_queue_timer(self):
        """Queue timer başlat"""
        try:
            minutes = int(self.minutes_var.get() or "0")
            seconds = int(self.seconds_var.get() or "0")
            
            if minutes == 0 and seconds == 0:
                self.show_status("⚠️ Geçerli bir süre girin!", "warning")
                return
            
            if not self.client.connected:
                self.show_status("❌ LoL Client'a bağlı değil!", "error")
                return
            
            if self.client.in_game:
                self.show_status("⚠️ Oyundayken timer başlatılamaz!", "warning")
                return
            
            # Timer başlat
            success = self.timer.start_timer(minutes, seconds, self.on_timer_complete)
            if success:
                self.start_timer_btn.configure(state="disabled")
                self.stop_timer_btn.configure(state="normal")
                self.show_status(f"⏰ Timer başlatıldı: {minutes}:{seconds:02d}", "success")
            
        except ValueError:
            self.show_status("⚠️ Geçerli sayılar girin!", "warning")
    
    def stop_queue_timer(self):
        """Queue timer durdur"""
        self.timer.stop_timer()
        self.start_timer_btn.configure(state="normal")
        self.stop_timer_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.timer_display.configure(text="00:00")
        self.show_status("⏹️ Timer durduruldu", "warning")
    
    def on_timer_complete(self):
        """Timer tamamlandığında çalışır"""
        if self.client.connected and not self.client.in_game:
            success = self.client.start_matchmaking()
            if success:
                stats = self.config.get('stats', {})
                stats['queue_sessions'] = stats.get('queue_sessions', 0) + 1
                self.config.set('stats', stats)
                self.update_stats_display()
                self.show_status("🚀 Matchmaking başlatıldı!", "success")
            else:
                self.show_status("❌ Matchmaking başlatılamadı!", "error")
        else:
            if self.client.in_game:
                self.show_status("⚠️ Oyunda olduğu için matchmaking başlatılamadı!", "warning")
            else:
                self.show_status("❌ LoL Client bağlantısı yok!", "error")
        
        # Reset timer controls
        self.root.after(0, lambda: (
            self.start_timer_btn.configure(state="normal"),
            self.stop_timer_btn.configure(state="disabled"),
            self.progress_bar.set(0),
            self.timer_display.configure(text="00:00")
        ))
    
    def start_timer_update(self):
        """Timer güncellemesi için ayrı döngü"""
        self.update_timer_display()
        self.root.after(500, self.start_timer_update)  # Timer için 500ms güncelleme
    
    def update_timer_display(self):
        """Sadece timer gösterimini güncelle"""
        if self.timer.timer_running:
            self.timer_display.configure(text=self.timer.get_time_display())
            self.progress_bar.set(self.timer.get_progress())
    
    def start_monitoring(self):
        """İzleme başlat"""
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        self.update_gui()
    
    def _monitor_worker(self):
        """İzleme worker thread - optimized"""
        last_connection_check = 0
        
        while True:
            current_time = time.time()
            
            # Connection check - her 3 saniyede bir
            if current_time - last_connection_check >= 3:
                if not self.client.connected:
                    self.client.find_client()
                else:
                    self.client.check_game_status()
                last_connection_check = current_time
            
            # Auto accept kontrolü - sadece gerektiğinde
            if (self.auto_accept_running and self.client.connected and 
                not self.client.in_game):
                ready_check = self.client.get_ready_check_status()
                
                if ready_check:
                    ready_check_id = ready_check.get("declinerFlowStartedTime", ready_check.get("timer", 0))
                    state = ready_check.get("state", "")
                    player_response = ready_check.get("playerResponse", "None")
                    
                    if state == "InProgress":
                        # Yeni ready check ve henüz kabul etmedik
                        if (ready_check_id != self.last_ready_check_id and 
                            player_response == "None"):
                            
                            stats = self.config.get('stats', {})
                            stats['matches_found'] = stats.get('matches_found', 0) + 1
                            self.config.set('stats', stats)
                            
                            if self.client.accept_match():
                                self.last_ready_check_id = ready_check_id
                                self.waiting_for_others = True
                                stats['matches_accepted'] = stats.get('matches_accepted', 0) + 1
                                self.config.set('stats', stats)
                                self.root.after(0, self.update_stats_display)
                                self.logger.info("⏳ Diğer oyuncular bekleniyor...")
                        
                        elif player_response == "Accepted" and self.waiting_for_others:
                            # Zaten kabul ettik, sessizce bekle
                            pass
                    
                    elif state == "EveryoneReady":
                        if self.waiting_for_others:
                            self.logger.info("🎮 Herkes hazır! Oyun başlıyor...")
                            self.waiting_for_others = False
                            self.last_ready_check_id = None
                    
                    elif state not in ["InProgress", "EveryoneReady"]:
                        # Ready check bitti, reset
                        self.waiting_for_others = False
                        self.last_ready_check_id = None
                
                else:
                    # Ready check yok, reset
                    if self.waiting_for_others:
                        self.waiting_for_others = False
                        self.last_ready_check_id = None
            
            time.sleep(1.5)  # Optimized sleep interval
    
    def update_gui(self):
        """GUI güncelle - timer hariç"""
        # Connection status
        if self.client.connected:
            if self.client.in_game:
                self.connection_label.configure(
                    text=f"🎮 {self.get_text('in_game')}",
                    text_color=self.colors["warning"]
                )
                self.status_label.configure(text=f"🎮 {self.get_text('in_game')}")
            else:
                self.connection_label.configure(
                    text=f"🟢 {self.get_text('connected')}",
                    text_color=self.colors["success"]
                )
                self.status_label.configure(text=f"✅ {self.get_text('ready')}")
        else:
            self.connection_label.configure(
                text=f"🔴 {self.get_text('disconnected')}", 
                text_color=self.colors["error"]
            )
            self.status_label.configure(text=self.get_text("waiting_client"))
        
        # Button states update
        self.update_button_states()
        
        # Schedule next update - timer ayrı güncelleniyor
        self.root.after(2000, self.update_gui)
    
    def load_stats(self):
        """İstatistikleri yükle"""
        self.update_stats_display()
    
    def update_stats_display(self):
        """İstatistik ekranını güncelle"""
        stats = self.config.get('stats', {})
        
        matches_found = stats.get('matches_found', 0)
        matches_accepted = stats.get('matches_accepted', 0)
        queue_sessions = stats.get('queue_sessions', 0)
        
        self.matches_found_label.configure(text=f"{self.get_text('matches_found')}\n{matches_found}")
        self.matches_accepted_label.configure(text=f"{self.get_text('matches_accepted')}\n{matches_accepted}")
        self.queue_sessions_label.configure(text=f"{self.get_text('queue_sessions')}: {queue_sessions}")
    
    def change_language(self, language):
        """Dil değiştir"""
        new_lang = "en" if language == "English" else "tr"
        if new_lang != self.current_language:
            self.current_language = new_lang
            self.config.set('language', new_lang)
            self.update_all_texts()
    
    def update_all_texts(self):
        """Tüm metinleri güncelle"""
        # Header
        self.title_label.configure(text=self.get_text("title"))
        self.subtitle_label.configure(text=self.get_text("subtitle"))
        
        # Console toggle
        console_text = self.get_text("hide_console") if self.console_visible else self.get_text("show_console")
        self.console_toggle_btn.configure(text=f"📊 {console_text}")
        
        # Auto Accept Panel
        self.auto_accept_title.configure(text=f"🎯 {self.get_text('auto_accept')}")
        self.auto_accept_desc.configure(text=self.get_text("auto_accept_desc"))
        
        if self.auto_accept_running:
            self.auto_accept_btn.configure(text=f"⏹️ {self.get_text('stop')}")
        else:
            self.auto_accept_btn.configure(text=f"▶️ {self.get_text('start')}")
        
        # Auto Queue Panel
        self.auto_queue_title.configure(text=f"⏰ {self.get_text('auto_queue')}")
        self.auto_queue_desc.configure(text=self.get_text("auto_queue_desc"))
        self.min_label.configure(text=self.get_text("minutes"))
        self.sec_label.configure(text=self.get_text("seconds"))
        self.start_timer_btn.configure(text=f"▶️ {self.get_text('start')}")
        self.stop_timer_btn.configure(text=f"⏹️ {self.get_text('stop')}")
        
        # Console
        if hasattr(self, 'console_title'):
            self.console_title.configure(text=f"📊 {self.get_text('console')}")
            self.clear_console_btn.configure(text=f"🗑️ {self.get_text('clear_console')}")
        
        # Status bar
        self.version_label.configure(text=self.get_text("version"))
        
        # Update stats display
        self.update_stats_display()
        
        # Update button states
        self.update_button_states()
    
    def show_status(self, message, msg_type="info"):
        """Durum mesajı göster"""
        colors = {
            "info": self.colors["text"],
            "success": self.colors["success"],
            "warning": self.colors["warning"],
            "error": self.colors["error"]
        }
        
        self.status_label.configure(
            text=message,
            text_color=colors.get(msg_type, self.colors["text"])
        )
        
        # Also log to console
        self.logger.info(message)
    
    def on_closing(self):
        """Pencere kapatılırken"""
        # Save window size
        geometry = self.root.geometry()
        width, height = geometry.split('+')[0].split('x')
        self.config.set('window.width', int(width))
        self.config.set('window.height', int(height))
        
        # Stop components
        if hasattr(self, 'timer'):
            self.timer.stop_timer()
        
        self.logger.info("👋 BeRightBack kapatılıyor...")
        self.root.destroy()
    
    def run(self):
        """GUI çalıştır"""
        self.root.mainloop()

def main():
    """Ana fonksiyon"""
    try:
        app = BeRightBackGUI()
        app.run()
    except Exception as e:
        print(f"Program başlatılırken hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()