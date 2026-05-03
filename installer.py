import os
import sys
import ctypes
import threading
import subprocess
import requests
import customtkinter as ctk
from tkinter import filedialog
from win32com.client import Dispatch

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# =====================================================================
# НАСТРОЙКИ: Прямая ссылка на ваш main.exe из GitHub Releases
# =====================================================================
DOWNLOAD_URL = "https://github.com/ваш-логин/Mute-Translator/releases/download/v1.0.0/main.exe"
# =====================================================================

def get_resource_path(relative_path):
    """Возвращает правильный путь к ресурсам (картинкам) при работе в .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def apply_win_effects(window):
    """Эффект Acrylic Blur и закругление углов Windows 11"""
    try:
        hwnd = user32.GetParent(window.winfo_id())
        from ctypes import POINTER, c_int, c_size_t, pointer, Structure
        
        class ACCENTPOLICY(Structure):
            _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]
            
        class DATA(Structure):
            _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENTPOLICY)), ("SizeOfData", c_size_t)]
        
        accent = ACCENTPOLICY(3, 0, 0xFF050505, 0) # Сверхтемный блюр
        data = DATA(19, pointer(accent), ctypes.sizeof(accent))
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        
        attr, val = 33, c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
    except:
        pass

class MultiStepInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mute Translator - Setup")
        self.geometry("550x450")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#050505")

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"550x450+{(sw-550)//2}+{(sh-450)//2}")

        # Глобальные переменные установки
        default_path = os.path.join(os.environ["LOCALAPPDATA"], "MuteTranslator").replace("\\", "/")
        self.install_path = ctk.StringVar(value=default_path)
        self.create_shortcut_var = ctk.BooleanVar(value=True)
        self.agree_var = ctk.BooleanVar(value=False)
        self.installed_exe_path = ""

        # Шапка окна
        self.draw_header()

        # Контейнер для динамического содержимого
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=25, pady=20)

        # Показываем 1 стадию
        self.show_stage_1()
        self.after(10, lambda: apply_win_effects(self))

    def draw_header(self):
        header = ctk.CTkFrame(self, fg_color="#0a0a0a", height=60, corner_radius=0)
        header.pack(fill="x")
        
        ctk.CTkLabel(header, text="MUTE", font=("Segoe UI Variable Display", 24, "bold"), text_color="#2eb85c").pack(side="left", padx=(25, 5))
        ctk.CTkLabel(header, text="INSTALLER", font=("Segoe UI Variable Display", 24, "bold"), text_color="white").pack(side="left")
        
        ctk.CTkButton(header, text="✕", width=35, height=35, fg_color="transparent", 
                       hover_color="#ff4b4b", command=self.destroy).pack(side="right", padx=15)

    def clear_body(self):
        """Очищает центральную часть окна для нового шага"""
        for widget in self.body.winfo_children():
            widget.destroy()

    def fix_entry_shortcuts(self, event):
        """Исправляет работу Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X на любой раскладке"""
        # 4 — это маска клавиши Ctrl в Windows
        if event.state & 4 or event.state & 12:
            # 65 = Код клавиши A (Ф)
            if event.keycode == 65:
                event.widget.select_range(0, 'end')
                event.widget.icursor('end')
                return "break"
            
            # 67 = Код клавиши C (С)
            elif event.keycode == 67:
                try:
                    self.clipboard_clear()
                    self.clipboard_append(event.widget.selection_get())
                except:
                    pass
                return "break"
            
            # 86 = Код клавиши V (М)
            elif event.keycode == 86:
                try:
                    text = self.clipboard_get()
                    if event.widget.select_present():
                        start = event.widget.index("sel.first")
                        end = event.widget.index("sel.last")
                        event.widget.delete(start, end)
                    
                    event.widget.insert("insert", text)
                except:
                    pass
                return "break"
            
            # 88 = Код клавиши X (Ч)
            elif event.keycode == 88:
                try:
                    if event.widget.select_present():
                        self.clipboard_clear()
                        self.clipboard_append(event.widget.selection_get())
                        start = event.widget.index("sel.first")
                        end = event.widget.index("sel.last")
                        event.widget.delete(start, end)
                except:
                    pass
                return "break"

    # ==========================================
    # СТАДИЯ 1: ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ
    # ==========================================
    def show_stage_1(self):
        self.clear_body()

        label_title = ctk.CTkLabel(self.body, text="ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ", font=("Segoe UI Variable Display", 14, "bold"), text_color="#555")
        label_title.pack(anchor="w", pady=(0, 5))

        license_box = ctk.CTkTextbox(self.body, fg_color="#0d0d0d", border_color="#151515", border_width=1, corner_radius=8, font=("Segoe UI", 11), text_color="#aaa", activate_scrollbars=True)
        license_box.pack(fill="both", expand=True, pady=(0, 15))
        
        license_box.insert("0.0", "Добро пожаловать в установщик Mute Translator!\n\n"
                                  "Пожалуйста, внимательно прочитайте условия использования перед установкой программного обеспечения:\n\n"
                                  "1. ИСПОЛЬЗОВАНИЕ ПРОГРАММЫ\n"
                                  "Программа 'Mute Translator' предоставляется бесплатно для личного использования. Вы не имеете права продавать или распространять данное ПО от своего имени.\n\n"
                                  "2. ИНТЕРНЕТ И СЕТЕВЫЕ ФУНКЦИИ\n"
                                  "Приложение требует стабильного подключения к интернету для выполнения перевода. Программа автоматически обращается к серверам для получения данных. Передавая текст, вы соглашаетесь с обработкой этих данных сторонними сервисами перевода.\n\n"
                                  "3. ПРАВА И ОБЯЗАННОСТИ\n"
                                  "Программа не собирает личные данные пользователей. Автор не несёт ответственности за возможные перебои в работе, ошибки перевода или любой ущерб, возникший в процессе использования.\n\n"
                                  "4. ОБНОВЛЕНИЯ И ИЗМЕНЕНИЯ\n"
                                  "Разработчик оставляет за собой право изменять функционал программы без предварительного уведомления.\n\n"
                                  "Если вы согласны со всеми пунктами, установите галочку ниже и нажмите кнопку 'ДАЛЕЕ'.")
        license_box.configure(state="disabled")

        self.agree_checkbox = ctk.CTkCheckBox(self.body, text="Я принимаю условия лицензионного соглашения", 
                                               variable=self.agree_var, onvalue=True, offvalue=False,
                                               font=("Segoe UI", 12), text_color="#ccc", checkbox_height=20, checkbox_width=20,
                                               border_width=1, fg_color="#2eb85c", hover_color="#239a4b",
                                               command=self.toggle_agree_button)
        self.agree_checkbox.pack(anchor="w", pady=(0, 15))

        self.btn_agree = ctk.CTkButton(self.body, text="ДАЛЕЕ", font=("Segoe UI Variable Display", 15, "bold"), 
                                       fg_color="#1b6a37", text_color="#888", state="disabled", height=45, command=self.show_stage_2)
        self.btn_agree.pack(fill="x")

    def toggle_agree_button(self):
        """Активирует/деактивирует кнопку Далее"""
        if self.agree_var.get():
            self.btn_agree.configure(state="normal", fg_color="#2eb85c", hover_color="#239a4b", text_color="white")
        else:
            self.btn_agree.configure(state="disabled", fg_color="#1b6a37", hover_color="#1b6a37", text_color="#888")

    # ==========================================
    # СТАДИЯ 2: ВЫБОР ДИРЕКТОРИИ
    # ==========================================
    def show_stage_2(self):
        self.clear_body()

        label_title = ctk.CTkLabel(self.body, text="ВЫБЕРИТЕ ПАПКУ ДЛЯ УСТАНОВКИ", font=("Segoe UI Variable Display", 14, "bold"), text_color="#555")
        label_title.pack(anchor="w", pady=(20, 5))

        path_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        path_frame.pack(fill="x", pady=(0, 25))

        self.entry = ctk.CTkEntry(path_frame, textvariable=self.install_path, font=("Segoe UI", 12), fg_color="#030303", border_color="#121212", height=42)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Жёсткая привязка всех нажатий к исправлению горячих клавиш
        self.entry.bind("<KeyPress>", self.fix_entry_shortcuts)

        btn_browse = ctk.CTkButton(path_frame, text="Обзор", width=80, height=42, fg_color="#0f0f0f", hover_color="#1a1a1a", command=self.browse_folder)
        btn_browse.pack(side="right")

        label_desc = ctk.CTkLabel(self.body, text="Программа будет установлена в указанную папку.\nДля работы приложения права администратора не требуются.",
                                  font=("Segoe UI", 12), text_color="#444", justify="left")
        label_desc.pack(anchor="w", pady=(0, 20))

        btn_next = ctk.CTkButton(self.body, text="НАЧАТЬ УСТАНОВКУ", font=("Segoe UI Variable Display", 15, "bold"), 
                                fg_color="#2eb85c", hover_color="#239a4b", height=45, command=self.show_stage_3)
        btn_next.pack(fill="x", side="bottom")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.install_path.set(folder)

    # ==========================================
    # СТАДИЯ 3: СКАЧИВАНИЕ И ПРОГРЕСС
    # ==========================================
    def show_stage_3(self):
        self.clear_body()

        self.status_label = ctk.CTkLabel(self.body, text="Скачивание файлов...", font=("Segoe UI Variable Display", 16, "bold"), text_color="#2eb85c")
        self.status_label.pack(anchor="w", pady=(50, 2))

        self.sub_label = ctk.CTkLabel(self.body, text="Загрузка MuteTranslator.exe с сервера...", font=("Segoe UI", 12), text_color="#666")
        self.sub_label.pack(anchor="w", pady=(0, 20))

        self.progress = ctk.CTkProgressBar(self.body, progress_color="#2eb85c", fg_color="#111111", height=12)
        self.progress.pack(fill="x", pady=10)
        self.progress.set(0)

        threading.Thread(target=self.download_thread, daemon=True).start()

    def download_thread(self):
        target_dir = self.install_path.get()
        self.installed_exe_path = os.path.join(target_dir, "MuteTranslator.exe")

        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            response = requests.get(DOWNLOAD_URL, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.installed_exe_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = downloaded / total_size
                            self.after(0, lambda p=percent: self.progress.set(p))
                            self.after(0, lambda d=downloaded, t=total_size: self.sub_label.configure(
                                text=f"Загружено {d // 1024} КБ из {t // 1024} КБ"))

            self.after(600, self.show_stage_4)

        except Exception as e:
            self.after(0, lambda err=e: self.show_error_screen(str(err)))

    # ==========================================
    # СТАДИЯ 4: ФИНАЛ И СОЗДАНИЕ ЯРЛЫКА
    # ==========================================
    def show_stage_4(self):
        self.clear_body()

        icon_label = ctk.CTkLabel(self.body, text="✓", font=("Segoe UI Variable Display", 54, "bold"), text_color="#2eb85c")
        icon_label.pack(pady=(15, 2))

        title_label = ctk.CTkLabel(self.body, text="УСПЕШНО СКАЧАНО!", font=("Segoe UI Variable Display", 18, "bold"), text_color="white")
        title_label.pack(pady=2)

        desc_label = ctk.CTkLabel(self.body, text="Программа установлена и готова к первому запуску.", font=("Segoe UI", 12), text_color="#666")
        desc_label.pack(pady=(0, 15))

        sw_frame = ctk.CTkFrame(self.body, fg_color="#0d0d0d", corner_radius=10, height=45, border_width=1, border_color="#151515")
        sw_frame.pack(fill="x", pady=(0, 20))
        sw_frame.pack_propagate(False)

        ctk.CTkLabel(sw_frame, text="Создать ярлык на Рабочем столе", font=("Segoe UI", 12), text_color="#ccc").pack(side="left", padx=15)
        sw = ctk.CTkSwitch(sw_frame, text="", variable=self.create_shortcut_var, progress_color="#2eb85c")
        sw.pack(side="right", padx=15)

        btn_finish = ctk.CTkButton(self.body, text="ЗАПУСТИТЬ ПРИЛОЖЕНИЕ", font=("Segoe UI Variable Display", 15, "bold"), 
                                   fg_color="#2eb85c", hover_color="#239a4b", height=45, command=self.finish_and_launch)
        btn_finish.pack(fill="x")

    def finish_and_launch(self):
        if self.create_shortcut_var.get():
            self.create_shortcut(self.installed_exe_path)

        try:
            if os.path.exists(self.installed_exe_path):
                subprocess.Popen([self.installed_exe_path], cwd=os.path.dirname(self.installed_exe_path))
        except:
            pass

        self.destroy()

    def create_shortcut(self, target_exe):
        try:
            desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            shortcut_path = os.path.join(desktop, "Mute Translator.lnk")
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target_exe
            shortcut.WorkingDirectory = os.path.dirname(target_exe)
            shortcut.IconLocation = target_exe
            shortcut.save()
        except:
            pass

    def show_error_screen(self, err_msg):
        self.clear_body()

        icon_label = ctk.CTkLabel(self.body, text="✕", font=("Segoe UI Variable Display", 54, "bold"), text_color="#ff4b4b")
        icon_label.pack(pady=(15, 2))

        title_label = ctk.CTkLabel(self.body, text="ОШИБКА УСТАНОВКИ", font=("Segoe UI Variable Display", 18, "bold"), text_color="white")
        title_label.pack(pady=2)

        desc_label = ctk.CTkLabel(self.body, text=f"Проверьте интернет-соединение.\n{err_msg[:50]}...", font=("Segoe UI", 12), text_color="#666")
        desc_label.pack(pady=(0, 25))

        btn_close = ctk.CTkButton(self.body, text="ЗАКРЫТЬ", font=("Segoe UI Variable Display", 15, "bold"), 
                                  fg_color="#ff4b4b", hover_color="#c93b3b", height=45, command=self.destroy)
        btn_close.pack(fill="x")

if __name__ == "__main__":
    app = MultiStepInstaller()
    app.mainloop()