import customtkinter as ctk
import tkinter as tk
import threading
import time
import os
import shutil
import subprocess
import requests
import random
import string
import re
from pynput.keyboard import Controller as KController, Key, Listener as KListener
from pynput.mouse import Controller as MController, Button
import mss
from tkinter import messagebox, filedialog
import webbrowser
from datetime import datetime
import pystray
from PIL import Image, ImageDraw

# === ЦВЕТОВАЯ ПАЛИТРА "SOFT MODERN" ===
BG_COLOR = "#1E1E2E"
CARD_COLOR = "#27273A"
ACCENT_COLOR = "#3B82F6"
ACCENT_HOVER = "#2563EB"
TEXT_MAIN = "#E2E8F0"
TEXT_MUTED = "#94A3B8"
BORDER_COLOR = "#33334B"
SUCCESS_COLOR = "#10B981"
DANGER_COLOR = "#EF4444"
WARNING_COLOR = "#F59E0B"
DONATE_COLOR = "#F59E0B"  # Оранжевый для доната
DONATE_HOVER = "#D97706"

ctk.set_appearance_mode("dark")


def copy_text_to_clipboard(text):
    command = f'Set-Clipboard -Value "{text}"'
    subprocess.run(["powershell", "-command", command], creationflags=subprocess.CREATE_NO_WINDOW)


def copy_image_to_clipboard(filepath):
    abs_path = os.path.abspath(filepath)
    command = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_path}'))"
    subprocess.run(["powershell", "-command", command], creationflags=subprocess.CREATE_NO_WINDOW)


class SnippingTool(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback
        self.start_x = self.start_y = self.rect = None
        self.attributes('-alpha', 0.3)
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.configure(cursor="cross")
        self.overrideredirect(True)

        self.canvas = tk.Canvas(self, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_button_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline=ACCENT_COLOR, width=2,
                                                 fill="black")

    def on_move_press(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        self.destroy()
        if abs(end_x - self.start_x) > 5 and abs(end_y - self.start_y) > 5:
            left, top = min(self.start_x, end_x), min(self.start_y, end_y)
            width, height = abs(end_x - self.start_x), abs(end_y - self.start_y)
            self.master.after(100, lambda: self.callback({"top": top, "left": left, "width": width, "height": height}))


class GlobalSettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, hk_dict, save_cb):
        super().__init__(master)
        self.title("Настройки горячих клавиш")
        self.geometry("400x450")
        self.configure(fg_color=BG_COLOR)
        self.grab_set()
        self.resizable(False, False)
        self.save_cb = save_cb

        self.hotkey_list_str = sorted(list(set(
            ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
             'space', 'enter', 'tab', 'esc', 'backspace', 'delete', 'insert',
             'home', 'end', 'page_up', 'page_down', 'up', 'down', 'left', 'right'] +
            list('abcdefghijklmnopqrstuvwxyz0123456789')
        )))

        ctk.CTkLabel(self, text="⚙️ НАСТРОЙКИ КЛАВИШ", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=TEXT_MAIN).pack(pady=(20, 15))

        frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        def create_hk_row(parent, label_text, default_val):
            ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(pady=(10, 2))
            combo = ctk.CTkComboBox(parent, values=self.hotkey_list_str, width=220, fg_color=BG_COLOR,
                                    border_color=BORDER_COLOR, button_color=ACCENT_COLOR, text_color=TEXT_MAIN)
            combo.set(default_val)
            combo.pack()
            return combo

        self.c_clicker = create_hk_row(frame, "🖱️ Кликер (Старт/Стоп):", hk_dict['clicker'])
        self.c_sf = create_hk_row(frame, "🖥️ Скриншот всего экрана:", hk_dict['snap_full'])
        self.c_sa = create_hk_row(frame, "✂️ Скриншот области:", hk_dict['snap_area'])
        self.c_ocr = create_hk_row(frame, "📝 Сканер текста (OCR):", hk_dict['ocr'])

        ctk.CTkButton(self, text="СОХРАНИТЬ", command=self.save_settings, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=SUCCESS_COLOR, hover_color="#0DA068", text_color="white", height=40).pack(pady=(0, 20),
                                                                                                         padx=20,
                                                                                                         fill="x")

    def save_settings(self):
        new_hks = {
            'clicker': self.c_clicker.get(),
            'snap_full': self.c_sf.get(),
            'snap_area': self.c_sa.get(),
            'ocr': self.c_ocr.get()
        }
        if len(set(new_hks.values())) < 4:
            messagebox.showerror("Ошибка", "Горячие клавиши не могут повторяться!")
            return
        self.save_cb(new_hks)
        self.destroy()


class UltraModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("МУЛЬТИТУЛ By Slavik")
        self.geometry("580x700")  # Чуть увеличили высоту для ссылки на донат
        self.configure(fg_color=BG_COLOR)

        self.keyboard = KController()
        self.mouse = MController()
        self.running_clicker = False

        self.hks = {
            'clicker': 'f6',
            'snap_full': 'f9',
            'snap_area': 'f10',
            'ocr': 'f11'
        }

        self.lbl_clicker_var = ctk.StringVar()
        self.lbl_snap_var = ctk.StringVar()
        self.lbl_ocr_var = ctk.StringVar()
        self.update_labels_text()

        self.copy_to_clipboard = True
        self.screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Скриншоты")
        if not os.path.exists(self.screenshot_dir): os.makedirs(self.screenshot_dir)

        self.temp_mail_address = ""
        self.temp_mail_sid_token = ""

        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.setup_ui()
        self.start_hotkey_listener()

    def update_labels_text(self):
        self.lbl_clicker_var.set(f"АВТОКЛИКЕР (Запуск: {self.hks['clicker'].upper()})")
        self.lbl_snap_var.set(
            f"Весь экран: {self.hks['snap_full'].upper()}   |   Область: {self.hks['snap_area'].upper()}")
        self.lbl_ocr_var.set(f"Горячая клавиша: {self.hks['ocr'].upper()}")

    def open_settings(self):
        GlobalSettingsWindow(self, self.hks, self.save_settings_cb)

    def save_settings_cb(self, new_hks):
        self.hks = new_hks
        self.update_labels_text()
        self.start_hotkey_listener()

    def setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(pady=(20, 15), padx=25, fill="x")

        ctk.CTkLabel(top_bar, text="МУЛЬТИТУЛ By Slavik ", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(top_bar, text="⚙️ Настройки", command=self.open_settings, width=110, height=28,
                      fg_color=CARD_COLOR, hover_color=BORDER_COLOR, text_color=TEXT_MAIN, border_width=1,
                      border_color=BORDER_COLOR).pack(side="right")

        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=25, pady=(0, 15))

        btn_w = 125
        self.btn_nav_clicker = ctk.CTkButton(nav_frame, text="🖱️ Кликер", command=lambda: self.switch_tab("Clicker"),
                                             width=btn_w, fg_color=ACCENT_COLOR, text_color="white",
                                             hover_color=ACCENT_HOVER)
        self.btn_nav_clicker.pack(side="left", padx=(0, 5))

        self.btn_nav_snap = ctk.CTkButton(nav_frame, text="📸 Скриншоты", command=lambda: self.switch_tab("Snap"),
                                          width=btn_w, fg_color=CARD_COLOR, text_color=TEXT_MUTED,
                                          hover_color=BORDER_COLOR)
        self.btn_nav_snap.pack(side="left", padx=5)

        self.btn_nav_sys = ctk.CTkButton(nav_frame, text="⚙️ Система", command=lambda: self.switch_tab("System"),
                                         width=btn_w, fg_color=CARD_COLOR, text_color=TEXT_MUTED,
                                         hover_color=BORDER_COLOR)
        self.btn_nav_sys.pack(side="left", padx=5)

        self.btn_nav_utils = ctk.CTkButton(nav_frame, text="📦 Утилиты", command=lambda: self.switch_tab("Utils"),
                                           width=btn_w, fg_color=CARD_COLOR, text_color=TEXT_MUTED,
                                           hover_color=BORDER_COLOR)
        self.btn_nav_utils.pack(side="left", padx=(5, 0))

        self.main_content_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=CARD_COLOR, border_width=1,
                                               border_color=BORDER_COLOR)
        self.main_content_frame.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        self.frame_clicker = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.frame_snap = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.frame_sys = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.frame_utils = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")

        self.build_clicker_tab()
        self.build_snap_tab()
        self.build_sys_tab()
        self.build_utils_tab()

        self.frame_clicker.pack(fill="both", expand=True, padx=10, pady=10)

        # --- FOOTER С ДВУМЯ ССЫЛКАМИ ---
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=10)

        # Telegram Link
        self.telegram_label = ctk.CTkLabel(footer_frame, text="🔗 Telegram Канал разработчика",
                                           font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED,
                                           cursor="hand2")
        self.telegram_label.pack(pady=(0, 2))
        self.telegram_label.bind("<Enter>", lambda e: self.telegram_label.configure(text_color=TEXT_MAIN,
                                                                                    font=ctk.CTkFont(size=12,
                                                                                                     weight="bold",
                                                                                                     underline=True)))
        self.telegram_label.bind("<Leave>", lambda e: self.telegram_label.configure(text_color=TEXT_MUTED,
                                                                                    font=ctk.CTkFont(size=12,
                                                                                                     weight="bold")))
        self.telegram_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://t.me/sh1tkovEvro"))

        # DonationAlerts Link
        self.donate_label = ctk.CTkLabel(footer_frame, text="☕ Поддержать автора (DonationAlerts)",
                                         font=ctk.CTkFont(size=12, weight="bold"), text_color=DONATE_COLOR,
                                         cursor="hand2")
        self.donate_label.pack(pady=(2, 0))
        self.donate_label.bind("<Enter>", lambda e: self.donate_label.configure(text_color=DONATE_HOVER,
                                                                                font=ctk.CTkFont(size=12, weight="bold",
                                                                                                 underline=True)))
        self.donate_label.bind("<Leave>", lambda e: self.donate_label.configure(text_color=DONATE_COLOR,
                                                                                font=ctk.CTkFont(size=12,
                                                                                                 weight="bold")))
        self.donate_label.bind("<Button-1>",
                               lambda e: webbrowser.open_new_tab("https://www.donationalerts.com/r/sh1tkov"))

    def switch_tab(self, tab_name):
        self.btn_nav_clicker.configure(fg_color=CARD_COLOR, text_color=TEXT_MUTED)
        self.btn_nav_snap.configure(fg_color=CARD_COLOR, text_color=TEXT_MUTED)
        self.btn_nav_sys.configure(fg_color=CARD_COLOR, text_color=TEXT_MUTED)
        self.btn_nav_utils.configure(fg_color=CARD_COLOR, text_color=TEXT_MUTED)

        self.frame_clicker.pack_forget()
        self.frame_snap.pack_forget()
        self.frame_sys.pack_forget()
        self.frame_utils.pack_forget()

        if tab_name == "Clicker":
            self.btn_nav_clicker.configure(fg_color=ACCENT_COLOR, text_color="white")
            self.frame_clicker.pack(fill="both", expand=True, padx=10, pady=10)
        elif tab_name == "Snap":
            self.btn_nav_snap.configure(fg_color=ACCENT_COLOR, text_color="white")
            self.frame_snap.pack(fill="both", expand=True, padx=10, pady=10)
        elif tab_name == "System":
            self.btn_nav_sys.configure(fg_color=ACCENT_COLOR, text_color="white")
            self.frame_sys.pack(fill="both", expand=True, padx=10, pady=10)
        elif tab_name == "Utils":
            self.btn_nav_utils.configure(fg_color=ACCENT_COLOR, text_color="white")
            self.frame_utils.pack(fill="both", expand=True, padx=10, pady=10)

    # --- ВКЛАДКА: КЛИКЕР ---
    def build_clicker_tab(self):
        ctk.CTkLabel(self.frame_clicker, textvariable=self.lbl_clicker_var, font=ctk.CTkFont(weight="bold")).pack(
            pady=(15, 15))
        self.mode_var = ctk.StringVar(value="Клавиатура")
        ctk.CTkSegmentedButton(self.frame_clicker, values=["Клавиатура", "Мышь"], command=self.update_clicker_ui,
                               variable=self.mode_var).pack(pady=10, fill="x", padx=20)
        self.action_combo = ctk.CTkComboBox(self.frame_clicker, width=250, fg_color=BG_COLOR, border_color=BORDER_COLOR,
                                            button_color=ACCENT_COLOR)
        self.action_combo.pack(pady=10)

        frame_time = ctk.CTkFrame(self.frame_clicker, fg_color="transparent")
        frame_time.pack(pady=10)
        self.sec_ent = ctk.CTkEntry(frame_time, width=70, justify="center", fg_color=BG_COLOR,
                                    border_color=BORDER_COLOR);
        self.sec_ent.grid(row=0, column=0, padx=5);
        self.sec_ent.insert(0, "1")
        ctk.CTkLabel(frame_time, text="сек").grid(row=0, column=1, padx=(0, 15))
        self.ms_ent = ctk.CTkEntry(frame_time, width=70, justify="center", fg_color=BG_COLOR,
                                   border_color=BORDER_COLOR);
        self.ms_ent.grid(row=0, column=2, padx=5);
        self.ms_ent.insert(0, "0")
        ctk.CTkLabel(frame_time, text="мс").grid(row=0, column=3)

        self.btn_clicker_status = ctk.CTkButton(self.frame_clicker, text="ОЖИДАНИЕ ЗАПУСКА", state="disabled",
                                                fg_color=BG_COLOR, text_color=TEXT_MUTED, height=45)
        self.btn_clicker_status.pack(pady=(20, 10), fill="x", padx=20)
        self.update_clicker_ui()

    # --- ВКЛАДКА: СКРИНШОТЫ ---
    def build_snap_tab(self):
        ctk.CTkLabel(self.frame_snap, text="СКРИНШОТЫ И БУФЕР", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self.frame_snap, textvariable=self.lbl_snap_var, text_color=TEXT_MUTED).pack()

        self.cb_clipboard = ctk.CTkCheckBox(self.frame_snap, text="Авто-копирование в буфер обмена", onvalue=True,
                                            offvalue=False, text_color=TEXT_MAIN)
        self.cb_clipboard.select();
        self.cb_clipboard.pack(pady=15)

        self.lbl_dir = ctk.CTkLabel(self.frame_snap, text=f"Папка: ...{self.screenshot_dir[-20:]}",
                                    text_color=TEXT_MUTED)
        self.lbl_dir.pack()
        ctk.CTkButton(self.frame_snap, text="Изменить папку", command=self.change_dir, width=150, height=28,
                      fg_color=BG_COLOR, border_color=BORDER_COLOR, border_width=1).pack(pady=(5, 20))

        ctk.CTkFrame(self.frame_snap, height=2, fg_color=BG_COLOR).pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.frame_snap, text="УМНЫЙ СКАНЕР ТЕКСТА (OCR)", font=ctk.CTkFont(weight="bold")).pack(
            pady=(10, 5))
        ctk.CTkLabel(self.frame_snap,
                     text="Выделяет область на экране, распознает текст\nи сразу копирует его в буфер обмена.",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack()
        ctk.CTkLabel(self.frame_snap, textvariable=self.lbl_ocr_var, text_color=ACCENT_COLOR).pack(pady=5)
        self.lbl_ocr_status = ctk.CTkLabel(self.frame_snap, text="Готов к сканированию", text_color=SUCCESS_COLOR)
        self.lbl_ocr_status.pack(pady=5)

    # --- ВКЛАДКА: СИСТЕМА ---
    def build_sys_tab(self):
        ctk.CTkLabel(self.frame_sys, text="ТАЙМЕР СНА ПК", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        frame_timer = ctk.CTkFrame(self.frame_sys, fg_color="transparent")
        frame_timer.pack(pady=5)
        ctk.CTkLabel(frame_timer, text="Выключить ПК через: ").grid(row=0, column=0)
        self.ent_shutdown = ctk.CTkEntry(frame_timer, width=60, justify="center", fg_color=BG_COLOR,
                                         border_color=BORDER_COLOR);
        self.ent_shutdown.grid(row=0, column=1, padx=10);
        self.ent_shutdown.insert(0, "60")
        ctk.CTkLabel(frame_timer, text="минут").grid(row=0, column=2)

        btn_frame = ctk.CTkFrame(self.frame_sys, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="ЗАВЕСТИ", command=self.set_shutdown, fg_color=ACCENT_COLOR,
                      hover_color=ACCENT_HOVER, width=120, height=35).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="ОТМЕНИТЬ", command=self.cancel_shutdown, fg_color=BG_COLOR, border_width=1,
                      border_color=DANGER_COLOR, text_color=DANGER_COLOR, width=100, height=35,
                      hover_color="#3A1C20").pack(side="left", padx=5)

        ctk.CTkFrame(self.frame_sys, height=2, fg_color=BG_COLOR).pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(self.frame_sys, text="ОЧИСТКА ПК ОТ МУСОРА", font=ctk.CTkFont(weight="bold")).pack(pady=(5, 5))
        ctk.CTkLabel(self.frame_sys,
                     text="Удаляет временные файлы из папок Temp и Prefetch.\nОсвобождает место и ускоряет систему.",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack()
        self.btn_cleaner = ctk.CTkButton(self.frame_sys, text="🧹 ОЧИСТИТЬ КЭШ И МУСОР", command=self.clean_pc_trash,
                                         fg_color=WARNING_COLOR, hover_color="#D97706", text_color="black",
                                         font=ctk.CTkFont(weight="bold"), height=40)
        self.btn_cleaner.pack(pady=(15, 10), padx=30, fill="x")

    # --- ВКЛАДКА: НОВЫЕ УТИЛИТЫ ---
    def build_utils_tab(self):
        # 1. Авто-Сортировщик Загрузок
        ctk.CTkLabel(self.frame_utils, text="СОРТИРОВЩИК ЗАГРУЗОК", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(self.frame_utils,
                     text="Автоматически раскладывает файлы в папке 'Загрузки'\nпо аккуратным папкам (Фото, Программы, Архивы).",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack()
        ctk.CTkButton(self.frame_utils, text="📁 НАВЕСТИ ПОРЯДОК В ЗАГРУЗКАХ", command=self.organize_downloads,
                      fg_color="#8B5CF6", hover_color="#7C3AED", text_color="white", font=ctk.CTkFont(weight="bold"),
                      height=35).pack(pady=(15, 10), padx=30, fill="x")

        ctk.CTkFrame(self.frame_utils, height=2, fg_color=BG_COLOR).pack(fill="x", padx=20, pady=15)

        # 2. Временная почта с кнопкой копирования
        ctk.CTkLabel(self.frame_utils, text="ВРЕМЕННАЯ ПОЧТА (Без спама)", font=ctk.CTkFont(weight="bold")).pack(
            pady=(5, 5))
        ctk.CTkLabel(self.frame_utils, text="Получите email для регистраций. Работает 60 минут.",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack()

        mail_display_frame = ctk.CTkFrame(self.frame_utils, fg_color="transparent")
        mail_display_frame.pack(pady=10, padx=30, fill="x")

        self.ent_mail = ctk.CTkEntry(mail_display_frame, justify="center", fg_color=BG_COLOR, border_color=BORDER_COLOR,
                                     text_color=SUCCESS_COLOR, font=ctk.CTkFont(weight="bold"), height=35)
        self.ent_mail.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.ent_mail.insert(0, "Нажмите кнопку ниже...")
        self.ent_mail.configure(state="disabled")

        self.btn_copy_mail = ctk.CTkButton(mail_display_frame, text="📋", width=40, height=35, fg_color=CARD_COLOR,
                                           hover_color=BORDER_COLOR, border_width=1, border_color=BORDER_COLOR,
                                           command=self.copy_mail_manual)
        self.btn_copy_mail.pack(side="right")

        mail_btn_frame = ctk.CTkFrame(self.frame_utils, fg_color="transparent")
        mail_btn_frame.pack(pady=5)

        self.btn_gen_mail = ctk.CTkButton(mail_btn_frame, text="Создать Email", command=self.generate_temp_mail,
                                          width=120, height=35, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
        self.btn_gen_mail.pack(side="left", padx=5)

        self.btn_check_mail = ctk.CTkButton(mail_btn_frame, text="Проверить входящие", command=self.check_temp_mail,
                                            width=140, height=35, fg_color=BG_COLOR, border_color=ACCENT_COLOR,
                                            border_width=1, state="disabled")
        self.btn_check_mail.pack(side="left", padx=5)

    def copy_mail_manual(self):
        if self.temp_mail_address:
            copy_text_to_clipboard(self.temp_mail_address)
            self.btn_copy_mail.configure(text="✅", text_color=SUCCESS_COLOR)
            self.after(1500, lambda: self.btn_copy_mail.configure(text="📋", text_color=TEXT_MAIN))

    # --- ЛОГИКА ОЧИСТКИ ПК ---
    def clean_pc_trash(self):
        self.btn_cleaner.configure(text="⏳ ОЧИСТКА В ПРОЦЕССЕ...", state="disabled")
        self.update()

        def perform_cleanup():
            paths_to_clean = [os.environ.get('TEMP'), r"C:\Windows\Temp", r"C:\Windows\Prefetch"]
            total_freed_bytes = 0
            files_deleted = 0
            for path in paths_to_clean:
                if not path or not os.path.exists(path): continue
                try:
                    items_in_dir = os.listdir(path)
                except PermissionError:
                    continue
                except Exception:
                    continue

                for item in items_in_dir:
                    item_path = os.path.join(path, item)
                    try:
                        size = 0
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            size = self.get_dir_size(item_path)
                            shutil.rmtree(item_path)
                        total_freed_bytes += size
                        files_deleted += 1
                    except Exception:
                        pass
            freed_mb = total_freed_bytes / (1024 * 1024)
            self.after(0, lambda: self._cleanup_done(freed_mb, files_deleted))

        threading.Thread(target=perform_cleanup, daemon=True).start()

    def get_dir_size(self, path):
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp): total += os.path.getsize(fp)
        except:
            pass
        return total

    def _cleanup_done(self, freed_mb, files_deleted):
        self.btn_cleaner.configure(text="🧹 ОЧИСТИТЬ КЭШ И МУСОР", state="normal")
        if files_deleted > 0:
            messagebox.showinfo("Очистка", f"Удалено файлов: {files_deleted}\nОсвобождено: {freed_mb:.2f} МБ")
        else:
            messagebox.showinfo("Чисто", "Система уже чистая! Мусора не найдено.")

    # --- ЛОГИКА СОРТИРОВЩИКА ЗАГРУЗОК ---
    def organize_downloads(self):
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(downloads_dir):
            messagebox.showerror("Ошибка", "Папка 'Загрузки' не найдена.")
            return

        extensions = {
            "Изображения": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"],
            "Документы": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".ppt", ".pptx", ".csv"],
            "Программы": [".exe", ".msi", ".apk"],
            "Архивы": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Медиа": [".mp4", ".mp3", ".avi", ".mkv", ".wav", ".mov"]
        }

        moved_count = 0
        try:
            for filename in os.listdir(downloads_dir):
                filepath = os.path.join(downloads_dir, filename)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    target_folder = "Прочее"
                    for folder_name, exts in extensions.items():
                        if ext in exts:
                            target_folder = folder_name
                            break
                    folder_path = os.path.join(downloads_dir, target_folder)
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                    shutil.move(filepath, os.path.join(folder_path, filename))
                    moved_count += 1
            if moved_count > 0:
                messagebox.showinfo("Готово", f"Отсортировано файлов: {moved_count}.\nЗагляните в папку 'Загрузки'!")
            else:
                messagebox.showinfo("Чисто", "В папке 'Загрузки' нет разбросанных файлов.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")

    # --- ЛОГИКА ВРЕМЕННОЙ ПОЧТЫ ---
    def generate_temp_mail(self):
        self.btn_gen_mail.configure(state="disabled", text="Генерация...")
        self.update()

        def task():
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                r = requests.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", headers=headers,
                                 timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    self.temp_mail_address = data['email_addr']
                    self.temp_mail_sid_token = data['sid_token']
                    self.after(0, self._on_mail_generated)
                else:
                    self.after(0, lambda: messagebox.showerror("Ошибка", f"Сервис отклонил запрос ({r.status_code})."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", "Нет интернета или блокировка провайдером."))
            self.after(0, lambda: self.btn_gen_mail.configure(state="normal", text="Новый Email"))

        threading.Thread(target=task, daemon=True).start()

    def _on_mail_generated(self):
        self.ent_mail.configure(state="normal")
        self.ent_mail.delete(0, tk.END)
        self.ent_mail.insert(0, self.temp_mail_address)
        self.ent_mail.configure(state="disabled")
        self.btn_check_mail.configure(state="normal")
        copy_text_to_clipboard(self.temp_mail_address)
        messagebox.showinfo("Успех",
                            "Email сгенерирован и скопирован в буфер!\nПисьма могут приходить с задержкой 10-30 сек.")

    def check_temp_mail(self):
        if not self.temp_mail_address or not hasattr(self, 'temp_mail_sid_token'): return
        self.btn_check_mail.configure(state="disabled", text="Проверка...")
        self.update()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        def task():
            try:
                url = f"https://api.guerrillamail.com/ajax.php?f=check_email&seq=1&sid_token={self.temp_mail_sid_token}"
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    messages = data.get('list', [])
                    real_messages = [m for m in messages if m['mail_from'] != 'no-reply@guerrillamail.com']
                    if len(real_messages) == 0:
                        self.after(0, lambda: messagebox.showinfo("Входящие",
                                                                  "Новых писем пока нет.\nПодождите 20-30 секунд и проверьте снова."))
                    else:
                        msg_id = real_messages[0]['mail_id']
                        fetch_url = f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={msg_id}&sid_token={self.temp_mail_sid_token}"
                        r_msg = requests.get(fetch_url, headers=headers, timeout=15)
                        msg_data = r_msg.json()
                        subject = msg_data.get('mail_subject', 'Без темы')
                        body = msg_data.get('mail_body', 'Пустое письмо')
                        self.after(0, lambda: self._show_email_content(subject, body))
                else:
                    self.after(0, lambda: messagebox.showerror("Ошибка",
                                                               f"Сбой проверки ({r.status_code}). Попробуйте еще раз."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", "Таймаут соединения. Проверьте интернет."))
            self.after(0, lambda: self.btn_check_mail.configure(state="normal", text="Проверить входящие"))

        threading.Thread(target=task, daemon=True).start()

    def _show_email_content(self, subject, body):
        win = ctk.CTkToplevel(self)
        win.title("Новое письмо")
        win.geometry("450x350")
        win.attributes('-topmost', True)
        ctk.CTkLabel(win, text=f"Тема: {subject}", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        txt = ctk.CTkTextbox(win, width=400, height=250)
        txt.pack(padx=20, pady=10)

        clean_body = body.replace("<br>", "\n").replace("<br />", "\n").replace("&nbsp;", " ")
        clean_body = re.sub(r'<[^>]+>', '', clean_body)
        txt.insert("0.0", clean_body.strip())
        txt.configure(state="disabled")

    # --- ОСТАЛЬНАЯ ЛОГИКА ---
    def update_clicker_ui(self, mode=None):
        if self.mode_var.get() == "Клавиатура":
            self.action_combo.configure(
                values=sorted(list('abcdefghijklmnopqrstuvwxyz0123456789') + ['space', 'enter', 'tab', 'esc']))
            self.action_combo.set("1")
        else:
            self.action_combo.configure(values=["Левый клик", "Правый клик", "Средний клик"])
            self.action_combo.set("Левый клик")

    def change_dir(self):
        new_dir = filedialog.askdirectory()
        if new_dir:
            self.screenshot_dir = new_dir
            self.lbl_dir.configure(text=f"Папка: ...{self.screenshot_dir[-20:]}")

    def set_shutdown(self):
        try:
            mins = int(self.ent_shutdown.get())
            if mins <= 0: raise ValueError
            os.system(f"shutdown /s /t {mins * 60}")
            messagebox.showinfo("Таймер сна", f"Компьютер будет выключен через {mins} минут.")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите правильное количество минут.")

    def cancel_shutdown(self):
        os.system("shutdown /a")
        messagebox.showinfo("Таймер сна", "Запланированное выключение отменено.")

    def on_press_hotkey(self, key):
        try:
            pressed = key.name if hasattr(key, 'name') else str(key).replace("'", "")
            if pressed == self.hks['clicker']:
                self.after(0, self.toggle_clicker)
            elif pressed == self.hks['snap_full']:
                self.after(0, lambda: self.capture_img(None))
            elif pressed == self.hks['snap_area']:
                self.after(0, lambda: SnippingTool(self, self.capture_img))
            elif pressed == self.hks['ocr']:
                self.after(0, lambda: SnippingTool(self, self.capture_text_ocr))
        except AttributeError:
            pass

    def start_hotkey_listener(self):
        if hasattr(self, 'kb_listener'): self.kb_listener.stop()
        self.kb_listener = KListener(on_press=self.on_press_hotkey)
        self.kb_listener.daemon = True;
        self.kb_listener.start()

    def capture_img(self, region):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(self.screenshot_dir, f"snap_{timestamp}.png")
        try:
            with mss.mss() as sct:
                monitor = region if region else sct.monitors[1]
                img = sct.grab(monitor)
                mss.tools.to_png(img.rgb, img.size, output=filepath)
            if self.cb_clipboard.get(): copy_image_to_clipboard(filepath)
        except Exception:
            pass

    def capture_text_ocr(self, region):
        self.lbl_ocr_status.configure(text="⏳ Распознавание...", text_color="#F59E0B")

        def process_ocr():
            try:
                temp_path = os.path.join(self.screenshot_dir, "temp_ocr.png")
                with mss.mss() as sct:
                    img = sct.grab(region)
                    mss.tools.to_png(img.rgb, img.size, output=temp_path)
                with open(temp_path, 'rb') as f:
                    payload = {'apikey': 'helloworld', 'language': 'rus', 'isOverlayRequired': False}
                    r = requests.post('https://api.ocr.space/parse/image', files={'filename': f}, data=payload)
                result = r.json()
                if result.get('IsErroredOnProcessing') == False:
                    parsed_text = result['ParsedResults'][0]['ParsedText'].strip()
                    if parsed_text:
                        copy_text_to_clipboard(parsed_text)
                        self.lbl_ocr_status.configure(text="✅ Текст скопирован!", text_color=SUCCESS_COLOR)
                    else:
                        self.lbl_ocr_status.configure(text="❌ Текст не найден.", text_color=DANGER_COLOR)
                else:
                    self.lbl_ocr_status.configure(text="❌ Ошибка сервиса.", text_color=DANGER_COLOR)
                os.remove(temp_path)
            except Exception:
                self.lbl_ocr_status.configure(text="❌ Ошибка интернета.", text_color=DANGER_COLOR)
            self.after(3000,
                       lambda: self.lbl_ocr_status.configure(text="Готов к сканированию", text_color=SUCCESS_COLOR))

        threading.Thread(target=process_ocr, daemon=True).start()

    def toggle_clicker(self):
        if self.running_clicker:
            self.running_clicker = False
            self.btn_clicker_status.configure(text="ОСТАНОВЛЕН", fg_color=BG_COLOR, text_color=DANGER_COLOR)
        else:
            try:
                interval = float(self.sec_ent.get() or 0) + (float(self.ms_ent.get() or 0) / 1000.0)
                if interval <= 0: raise ValueError
                self.running_clicker = True
                self.btn_clicker_status.configure(text=f"АКТИВЕН ({interval:.3f}с)", fg_color=SUCCESS_COLOR,
                                                  text_color="white")
                threading.Thread(target=self.loop_clicker, args=(interval,), daemon=True).start()
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректный интервал.")

    def loop_clicker(self, interval):
        mode, action = self.mode_var.get(), self.action_combo.get()
        while self.running_clicker:
            if mode == "Клавиатура":
                k = getattr(Key, action, action)
                self.keyboard.press(k);
                self.keyboard.release(k)
            else:
                btn = {"Левый клик": Button.left, "Правый клик": Button.right, "Средний клик": Button.middle}[action]
                self.mouse.click(btn)
            time.sleep(interval)

    # --- ЛОГИКА ТРЕЯ ---
    def hide_window(self):
        self.withdraw()
        image = Image.new('RGB', (64, 64), color=(59, 130, 246))
        d = ImageDraw.Draw(image)
        d.text((10, 20), "ST", fill=(255, 255, 255))
        menu = pystray.Menu(pystray.MenuItem("Открыть Мультитул", self.show_window, default=True),
                            pystray.MenuItem("Выход", self.quit_window))
        self.tray_icon = pystray.Icon("name", image, "Мультитул By Slavik", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_window(self, icon, item):
        icon.stop()
        self.running_clicker = False
        self.quit()


if __name__ == "__main__":
    app = UltraModernApp()
    app.mainloop()
