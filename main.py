import customtkinter as ctk
import ctypes
import threading
import re
import pyperclip
import time
import json
import os
from PIL import Image
from deep_translator import GoogleTranslator
from ctypes import wintypes
from spellchecker import SpellChecker

# ================= КОНФИГУРАЦИЯ =================
HARD_FIX = {"спс": "спасибо", "пж": "пожалуйста", "ща": "сейчас", "пон": "понял", "бро": "про"}

# Список слов, которые Т9 не должен трогать
WHITELIST = [
    "нахуй", "пидор", "бля", "блять", "хуй", "ебать", "сука", 
    "еблан", "пиздец", "далбаеб", "долбоеб", "долбаеб", "далбаёб", "долбоёб"
]

# СЛОВАРЬ ЖИВОГО АМЕРИКАНСКОГО СЛЕНГА
# Если слово есть тут, оно переведется мгновенно и без транслита
SLANG_TRANSLATION = {
    "далбаеб": "dumbass",
    "долбоеб": "dumbass",
    "долбаеб": "dumbass",
    "далбаёб": "dumbass",
    "долбоёб": "dumbass",
    "еблан": "dickhead",
    "пидор": "faggot",
    "хуй": "dick",
    "пиздец": "holy shit",
    "блять": "fuck",
    "бля": "fuck",
    "сука": "bitch",
    "ебать": "fuck"
}

PUNCT_ALWAYS = ["а", "но", "что", "чтобы", "ибо", "хотя", "который", "если", "потому что", "где", "когда"]

spell_ru = None
spell_en = None

def load_spellcheckers():
    global spell_ru, spell_en
    try:
        spell_ru = SpellChecker(language='ru')
        spell_en = SpellChecker(language='en')
        spell_ru.word_frequency.load_words(WHITELIST)
        spell_en.word_frequency.load_words(WHITELIST)
    except: pass

threading.Thread(target=load_spellcheckers, daemon=True).start()

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

def apply_win_effects(window):
    try:
        hwnd = user32.GetParent(window.winfo_id())
        from ctypes import POINTER, c_int, c_size_t, pointer, Structure
        class ACCENTPOLICY(Structure):
            _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]
        class DATA(Structure):
            _fields_ = [("Attribute", c_int), ("Data", POINTER(ACCENTPOLICY)), ("SizeOfData", c_size_t)]
        
        accent = ACCENTPOLICY(3, 0, 0xCC101010, 0)
        data = DATA(19, pointer(accent), ctypes.sizeof(accent))
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        
        attr, val = 33, c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
    except: pass

# ================= ОКНО ИНТРО =================
class IntroWindow(ctk.CTkToplevel):
    def __init__(self, on_finish):
        super().__init__()
        self.on_finish = on_finish
        self.width, self.height = 500, 320
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(fg_color="#0a0a0a")
        
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.width}x{self.height}+{(sw-self.width)//2}+{(sh-self.height)//2}")
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(expand=True)
        
        ctk.CTkLabel(self.container, text="WELCOME TO", font=("Segoe UI Variable Display", 16, "bold"), text_color="#555").pack()
        
        title_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        title_frame.pack(pady=10)
        ctk.CTkLabel(title_frame, text="MUTE", font=("Segoe UI Variable Display", 42, "bold"), text_color="#2eb85c").pack(side="left")
        ctk.CTkLabel(title_frame, text=" TRANSLATOR", font=("Segoe UI Variable Display", 42, "bold"), text_color="white").pack(side="left")
        
        hint_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        hint_frame.pack(pady=20, padx=20)
        ctk.CTkLabel(hint_frame, text="HOTKEY TO OPEN: CTRL + ALT + X", font=("Segoe UI Variable Display", 14, "bold"), text_color="#777").pack()
        
        self.after(10, lambda: apply_win_effects(self))
        self.fade_in()

    def fade_in(self):
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            self.attributes("-alpha", alpha + 0.05)
            self.after(20, self.fade_in)
        else:
            self.after(2000, self.fade_out)

    def fade_out(self):
        alpha = self.attributes("-alpha")
        if alpha > 0.0:
            self.attributes("-alpha", alpha - 0.05)
            self.after(20, self.fade_out)
        else:
            self.destroy()
            self.on_finish()

# ================= ОКНО НАСТРОЕК =================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.width, self.height = 360, 520 
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.grab_set() 
        
        self.configure(fg_color="#0a0a0a")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.width}x{self.height}+{(sw-self.width)//2}+{(sh-self.height)//2}")
        
        self.draw_ui()
        self.after(10, lambda: apply_win_effects(self))

    def draw_ui(self):
        header = ctk.CTkFrame(self, fg_color="#111", height=60, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="PREFERENCES", font=("Segoe UI Variable Display", 16, "bold"), text_color="#444").pack(side="left", padx=25)
        ctk.CTkButton(header, text="✕", width=35, height=35, fg_color="transparent", hover_color="#ff4b4b", command=self.close_and_save).pack(side="right", padx=15)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        self.create_switch(container, "Autocorrect (T9)", self.parent.t9_active, "t9")
        self.create_switch(container, "Smart Punctuation", self.parent.auto_punct, "punct")
        self.create_switch(container, "Show Intro Always", self.parent.always_intro, "intro")

        ctk.CTkLabel(container, text="INTERFACE OPACITY", font=("Segoe UI Variable Display", 11, "bold"), text_color="#555").pack(anchor="w", pady=(15, 5), padx=5)
        s = ctk.CTkSlider(container, from_=0.3, to=1.0, button_color="#2eb85c", command=self.update_opacity)
        s.set(self.parent.attributes("-alpha"))
        s.pack(fill="x", padx=5)

        line = ctk.CTkFrame(container, height=1, fg_color="#1a1a1a")
        line.pack(fill="x", pady=25)

        info_box = ctk.CTkFrame(container, fg_color="#0d0d0d", corner_radius=12, border_width=1, border_color="#151515")
        info_box.pack(fill="x")
        
        ctk.CTkLabel(info_box, text="QUICK GUIDE", font=("Segoe UI Variable Display", 12, "bold"), text_color="#2eb85c").pack(pady=(10, 2))
        ctk.CTkLabel(info_box, text="To toggle this window use:", font=("Segoe UI", 12), text_color="#777").pack()
        ctk.CTkLabel(info_box, text="CTRL + ALT + X", font=("Segoe UI Variable Display", 16, "bold"), text_color="white").pack(pady=(2, 10))

    def create_switch(self, parent, text, val, type_key):
        box = ctk.CTkFrame(parent, fg_color="#151515", corner_radius=15, height=55)
        box.pack(fill="x", pady=5); box.pack_propagate(False)
        ctk.CTkLabel(box, text=text, font=("Segoe UI Variable Display", 14, "bold")).pack(side="left", padx=15)
        sw = ctk.CTkSwitch(box, text="", progress_color="#2eb85c", command=lambda: self.toggle(type_key))
        if val: sw.select()
        sw.pack(side="right", padx=10)

    def toggle(self, type_key):
        if type_key == "t9": self.parent.t9_active = not self.parent.t9_active
        elif type_key == "punct": self.parent.auto_punct = not self.parent.auto_punct
        elif type_key == "intro": self.parent.always_intro = not self.parent.always_intro

    def update_opacity(self, val): 
        self.parent.attributes("-alpha", val)

    def close_and_save(self):
        self.parent.save_settings()
        self.grab_release()
        self.destroy()

# ================= ОСНОВНОЕ ПРИЛОЖЕНИЕ =================
class MuteTranslator(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.width, self.height = 720, 440
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        self.settings_file = "settings.json"
        config = self.load_settings()
        
        self.attributes("-alpha", config.get("opacity", 0.95))
        self.auto_copy = config.get("auto_copy", True)
        self.t9_active = config.get("t9_active", True)
        self.auto_punct = config.get("auto_punct", True)
        self.always_intro = config.get("always_intro", False)
        self.first_run_done = config.get("first_run_done", False)
        
        self.last_replacement = None
        self.ignore_word = None
        self.translate_job = None
        self.trans_request_id = 0
        self.settings_window = None
        self.was_settings_open = False

        self.setup_ui(config)
        self.start_hotkey_listener()
        self.after(100, lambda: apply_win_effects(self))
        self.withdraw()

        if self.always_intro or not self.first_run_done:
            self.after(200, self.show_intro)
        else:
            self.after(200, self.toggle_window)

    def show_intro(self):
        IntroWindow(on_finish=self.finish_intro)

    def finish_intro(self):
        self.first_run_done = True
        self.save_settings()
        self.toggle_window()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_settings(self):
        config = {
            "t9_active": self.t9_active,
            "auto_punct": self.auto_punct,
            "auto_copy": self.auto_copy,
            "opacity": self.attributes("-alpha"),
            "lang_from": self.lang_from.get(),
            "lang_to": self.lang_to.get(),
            "always_intro": self.always_intro,
            "first_run_done": self.first_run_done
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except: pass

    def setup_ui(self, config):
        self.titlebar = ctk.CTkFrame(self, height=70, fg_color="#0d0d0d", corner_radius=0)
        self.titlebar.pack(fill="x")
        
        title_container = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        title_container.pack(side="left", padx=30)
        ctk.CTkLabel(title_container, text="MUTE", font=("Segoe UI Variable Display", 28, "bold"), text_color="#2eb85c").pack(side="left")
        ctk.CTkLabel(title_container, text=" TRANSLATOR", font=("Segoe UI Variable Display", 28, "bold")).pack(side="left")

        self.button_container = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        self.button_container.pack(side="right", padx=20)
        ctk.CTkButton(self.button_container, text="⚙", width=40, height=40, fg_color="transparent", 
                      hover_color="#1a1a1a", font=("Arial", 20), command=self.open_settings).pack(side="right", padx=8)
        
        self.copy_btn = ctk.CTkButton(self.button_container, text=f"AUTO-COPY: {'ON' if self.auto_copy else 'OFF'}", 
                                      width=130, height=36, fg_color="#2eb85c" if self.auto_copy else "#e55353", 
                                      corner_radius=10, font=("Segoe UI", 12, "bold"), command=self.toggle_copy)
        self.copy_btn.pack(side="right", padx=8)

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=25, pady=20)
        self.main.grid_columnconfigure((0, 1), weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self.lang_from = ctk.CTkOptionMenu(self.main, values=["auto", "en", "ru"], width=120, fg_color="#1a1a1a", button_color="#1a1a1a")
        self.lang_from.set(config.get("lang_from", "auto"))
        self.lang_from.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 15))

        try:
            img = ctk.CTkImage(Image.open("swap.png"), size=(20, 20))
            self.swap_btn = ctk.CTkButton(self.main, image=img, text="", width=35, height=35, fg_color="transparent", hover_color="#1a1a1a", command=self.swap_languages)
        except:
            self.swap_btn = ctk.CTkButton(self.main, text="⇄", width=35, height=35, fg_color="transparent", hover_color="#1a1a1a", command=self.swap_languages)
        
        self.swap_btn.place(relx=0.5, y=18, anchor="center")

        self.lang_to = ctk.CTkOptionMenu(self.main, values=["en", "ru"], width=120, fg_color="#1a1a1a", button_color="#1a1a1a")
        self.lang_to.set(config.get("lang_to", "en"))
        self.lang_to.grid(row=0, column=1, sticky="e", padx=5, pady=(0, 15))

        f = ("Segoe UI Variable Display", 15)
        self.input = ctk.CTkTextbox(self.main, font=f, fg_color="#080808", corner_radius=18, border_width=1, border_color="#151515")
        self.input.grid(row=1, column=0, sticky="nsew", padx=(5, 5), pady=5)
        
        self.output = ctk.CTkTextbox(self.main, font=f, fg_color="#080808", corner_radius=18, border_width=1, border_color="#151515")
        self.output.grid(row=1, column=1, sticky="nsew", padx=(5, 5), pady=5)

        self.fix_shortcuts(self.input)
        self.fix_shortcuts(self.output)
        self.input.bind("<KeyPress-BackSpace>", self.handle_backspace)
        self.input._textbox.bind("<KeyRelease-space>", self.on_space)
        self.input.bind("<KeyRelease>", self.schedule_translate)

    def swap_languages(self):
        frm, to = self.lang_from.get(), self.lang_to.get()
        if frm != "auto":
            self.lang_from.set(to)
            self.lang_to.set(frm)
            self.translate()

    def toggle_window(self):
        if self.state() == "withdrawn":
            self.attributes("-alpha", 0.0)
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"720x440+{(sw-720)//2}+{(sh-440)//2}")
            self.deiconify()
            self.lift()
            self.focus_force()
            self.input.focus_set()
            self.fade_in_main()
            if self.was_settings_open:
                self.open_settings()
        else:
            if self.settings_window and self.settings_window.winfo_exists():
                self.was_settings_open = True
                self.settings_window.grab_release()
                self.settings_window.destroy()
            else:
                self.was_settings_open = False
            self.withdraw()

    def fade_in_main(self):
        alpha = self.attributes("-alpha")
        if alpha < 0.95:
            self.attributes("-alpha", alpha + 0.1)
            self.after(20, self.fade_in_main)

    def translate(self):
        text = self.input.get("1.0", "end-1c").strip()
        if not text: 
            self.output.delete("1.0", "end")
            return
        
        src, tgt = self.lang_from.get(), self.lang_to.get()
        f_src = ('ru' if bool(re.search('[а-яА-Я]', text)) else 'en') if src == "auto" else src
        f_tgt = ('en' if f_src == 'ru' else 'ru') if src == "auto" else tgt
        
        self.trans_request_id += 1
        curr_id = self.trans_request_id
        
        def do_trans():
            try:
                # 1. Сначала разбиваем на слова и проверяем наш сленг-словарь
                words = text.split()
                processed_words = []
                
                for w in words:
                    # Очищаем от знаков препинания для проверки в словаре
                    clean_w = w.lower().strip(",.!?")
                    if clean_w in SLANG_TRANSLATION:
                        # Если нашли, подставляем живой американский аналог
                        translated_slang = SLANG_TRANSLATION[clean_w]
                        # Восстанавливаем знак препинания, если он был у слова
                        if w.endswith(('.', ',', '!', '?')):
                            translated_slang += w[-1]
                        processed_words.append(translated_slang)
                    else:
                        processed_words.append(w)
                
                # Собираем строку обратно
                processed_text = " ".join(processed_words)

                # 2. Переводим остальную часть текста через Google
                res = GoogleTranslator(source=f_src, target=f_tgt).translate(processed_text)
                
                if curr_id == self.trans_request_id:
                    self.after(0, lambda: self._finalize_output(res))
            except: pass
            
        threading.Thread(target=do_trans, daemon=True).start()

    def _finalize_output(self, res):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", res)
        if self.auto_copy: 
            pyperclip.copy(res.strip())

    def schedule_translate(self, event=None):
        if self.translate_job: 
            self.after_cancel(self.translate_job)
        self.translate_job = self.after(400, self.translate)

    def fix_shortcuts(self, widget):
        def handle_key(event):
            ctrl = (event.state & 0x4) != 0
            if ctrl:
                if event.keycode == 65: # Ctrl + A
                    full_text = widget.get("1.0", "end-1c")
                    match = re.search(r'\S.*\S|\S', full_text, re.DOTALL)
                    if match:
                        start_pos = widget.index(f"1.0 + {match.start()} chars")
                        end_pos = widget.index(f"1.0 + {match.end()} chars")
                        widget.tag_add("sel", start_pos, end_pos)
                    return "break"
                elif event.keycode == 67: # Ctrl + C
                    try: 
                        txt = widget.get("sel.first", "sel.last").strip()
                        if txt: pyperclip.copy(txt)
                    except: pass
                    return "break"
                elif event.keycode == 86: # Ctrl + V
                    try:
                        if widget.tag_ranges("sel"): widget.delete("sel.first", "sel.last")
                        widget.insert("insert", pyperclip.paste())
                    except: pass
                    return "break"
                elif event.keycode == 88: # Ctrl + X
                    try:
                        txt = widget.get("sel.first", "sel.last").strip()
                        if txt: pyperclip.copy(txt)
                        widget.delete("sel.first", "sel.last")
                    except: pass
                    return "break"
        widget._textbox.bind("<Control-KeyPress>", handle_key)

    def on_space(self, event):
        if self.auto_punct: self.apply_smart_punctuation()
        if self.t9_active: self.smart_fix_word()

    def smart_fix_word(self):
        if not spell_ru or not spell_en: return
        try:
            txt = self.input.get("1.0", "insert")
            match = re.search(r"([а-яА-ЯёЁa-zA-Z]+)\s$", txt)
            if not match: return
            raw = match.group(1); lw = raw.lower()
            if len(lw) < 2 or lw in WHITELIST or self.ignore_word == lw: return
            is_russian = bool(re.search('[а-яА-Я]', lw))
            corr = HARD_FIX.get(lw)
            if not corr:
                s_obj = spell_ru if is_russian else spell_en
                if lw not in s_obj:
                    p_corr = s_obj.correction(lw)
                    if p_corr and p_corr.lower() != lw: corr = p_corr
            if corr:
                end = self.input.index("insert - 1 chars")
                start = self.input.index(f"{end} - {len(raw)} chars")
                self.last_replacement = (start, raw, corr)
                self.input.delete(start, end); self.input.insert(start, corr)
                self.ignore_word = None
        except: pass

    def apply_smart_punctuation(self):
        try:
            full = self.input.get("1.0", "insert")
            words = full.split()
            if not words: return
            last = words[-1].lower().strip(",.!?")
            if last in PUNCT_ALWAYS:
                pos = self.input.index("insert - 1 chars")
                start = self.input.index(f"{pos} - {len(last)} chars")
                if self.input.get(f"{start} - 1 chars", start) == " ":
                    self.input.insert(f"{start} - 1 chars", ",")
        except: pass

    def handle_backspace(self, event):
        if self.last_replacement:
            idx, orig, replaced = self.last_replacement
            curr = self.input.index("insert")
            if curr == self.input.index(f"{idx} + {len(replaced)} chars + 1 chars"):
                self.input.delete(idx, self.input.index("insert - 1 chars"))
                self.input.insert(idx, orig)
                self.ignore_word = orig.lower(); self.last_replacement = None
                return "break"
        self.last_replacement = None

    def toggle_copy(self):
        self.auto_copy = not self.auto_copy
        self.copy_btn.configure(text=f"AUTO-COPY: {'ON' if self.auto_copy else 'OFF'}", 
                               fg_color="#2eb85c" if self.auto_copy else "#e55353")
        self.save_settings()

    def open_settings(self):
        if not self.settings_window or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        else: self.settings_window.lift()

    def start_hotkey_listener(self):
        def listener():
            user32.RegisterHotKey(None, 1, 0x0002 | 0x0001, 0x58) 
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312: self.after(0, self.toggle_window)
                user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))
        threading.Thread(target=listener, daemon=True).start()

if __name__ == "__main__":
    app = MuteTranslator()
    app.mainloop()