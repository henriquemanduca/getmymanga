import tkinter as tk
import customtkinter as ctk
# from CTkMessagebox import CTkMessagebox as mbox
import logging
import os
import threading
import requests

from src.services.download import DownloadService
from src.services.utils import get_default_download_folder

logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    APP_FOLDER = "getmymanga"

    def __init__(self):
        super().__init__()
        self.title("Get my manga!")
        window_width = 625
        window_height = 390
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(True, True)
        self.init_vars()
        self.create_widgets()

    def init_vars(self):
        if "nt" == os.name:
            self.wm_iconbitmap(bitmap = "./resources/icon.ico")
        else:
            img = tk.PhotoImage(file="./resources/icon2.png")
            self.tk.call('wm', 'iconphoto', self._w, img)

        self.download = DownloadService()
        self.app_logo = tk.PhotoImage(file="./resources/image.png")
        self.download_option_var = tk.StringVar()

        self.folder_var = tk.StringVar(value=f"{get_default_download_folder()}/{self.APP_FOLDER}")
        self.manga_name_var = tk.StringVar(value="Berserk")

        self.chap_start_var = tk.StringVar()
        self.chap_end_var = tk.StringVar()
        self._set_range(1,1)

        self.checkbox_compress = tk.BooleanVar(value=False)

    def create_widgets(self):
        image_label = tk.Label(self, image=self.app_logo, borderwidth=0)
        image_label.grid(row=0, column=0, columnspan=5, padx=0, pady=0)

        row = 1
        option_label = ctk.CTkLabel(self, text="Save on:")
        option_label.grid(row=row, column=0, padx=5, pady=0, sticky="w")

        manga_label = ctk.CTkLabel(self, text="Manga name:")
        manga_label.grid(row=row, column=3, padx=5, pady=0, sticky="w")

        row += 1
        folder_entry = ctk.CTkEntry(self, textvariable=self.folder_var)
        folder_entry.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        manga_name = ctk.CTkEntry(self, textvariable=self.manga_name_var)
        manga_name.grid(row=row, column=3, columnspan=1, padx=5, pady=5, sticky="ew")

        self.load_button = ctk.CTkButton(self,  text="Load Chapters", command=lambda: self.load_chapters())
        self.load_button.grid(row=row, column=4, padx=5, pady=5, sticky="we")

        row += 1
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=row, column=0, columnspan=5, padx=5, pady=5, sticky="we")
        self.progress_bar.configure(mode="indeterminnate")

        row += 1
        self.info_label = ctk.CTkLabel(self, text="Any information loaded...")
        self.info_label.grid(row=row, column=0, columnspan=5, padx=5, pady=5, sticky="w")

        row += 1
        option_label = ctk.CTkLabel(self, text="Download options:")
        option_label.grid(row=row, column=0, padx=5, pady=0, sticky="w")

        chap_start_label = ctk.CTkLabel(self, text="Start:")
        chap_start_label.grid(row=row, column=2, padx=5, pady=0, sticky="w")

        chap_end_label = ctk.CTkLabel(self, text="End:")
        chap_end_label.grid(row=row, column=3, padx=5, pady=0, sticky="w")

        row += 1
        self.info_combobox = ctk.CTkComboBox(self, state="readonly", values=["all", "range", "last one"], command=self._info_combobox, variable=self.download_option_var)
        self.info_combobox.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        self.info_combobox.set("All")

        self.chap_start = ctk.CTkEntry(self, textvariable=self.chap_start_var, placeholder_text="Start")
        self.chap_start.grid(row=row, column=2, columnspan=1, padx=5, pady=5, sticky="ew")

        self.chap_end = ctk.CTkEntry(self, textvariable=self.chap_end_var, placeholder_text="End")
        self.chap_end.grid(row=row, column=3, columnspan=1, padx=5, pady=5, sticky="ew")

        checkbox = ctk.CTkCheckBox(self, text="Compress to .cbr", variable=self.checkbox_compress)
        checkbox.grid(row=row, column=4)

        row += 1
        download_button = ctk.CTkButton(self,  text="Download", command=lambda: self.download_chapters(self.manga_name_var.get()))
        download_button.grid(row=row, column=2, columnspan=2, padx=5, pady=5, sticky="we")

        # define the grid
        # self.columnconfigure(0, weight=0)
        self.columnconfigure((0,1,2,3), weight=0)

    def _set_normal_state(self, fields):
        if isinstance(fields, list):
            for field in fields:
                field.configure(state="normal")
        else:
            fields.configure(state="normal")

    def _set_disabled_state(self, fields):
        if isinstance(fields, list):
            for field in fields:
                field.configure(state="disabled")
        else:
            fields.configure(state="disabled")

    def _info_combobox(self, event=None):
        if event == "Range":
            self._set_normal_state([self.chap_start, self.chap_end])

    def _default_state(self):
        self.progress_bar.stop()
        self._set_normal_state([self.load_button, self.info_combobox])

    def _down_state(self):
        self.progress_bar.start()
        self._set_disabled_state([self.load_button, self.info_combobox])

    def _set_range(self, first_one, last_one):
        self.chap_start_var.set(str(first_one))
        self.chap_end_var.set(str(last_one))

    def get_chapters(self):
        self._down_state()
        message = ""
        try:
            last_one = self.download.get_chapters(self.manga_name_var.get())["last_one"]
            message = f"{self.manga_name_var.get()} founded with {last_one} chapters available!"
            self._set_range(1, last_one)
        except Exception as e:
            message = f"Something went wrong. {e}"
        except requests.exceptions.ConnectionError:
            message = "Could not connect to http://mangasee123.com"
        finally:
            self.info_label.configure(text=message)
            self._default_state()

    def load_chapters(self):
        threading.Thread(target=lambda: self.get_chapters(), args=(), daemon=True).start()

    def _download_files(self):
        self._down_state()
        message = ""
        try:
            folder = self.folder_var.get()
            download_option = self.download_option_var.get()
            start = self.chap_start_var.get()
            end = self.chap_end_var.get()
            compress = self.checkbox_compress.get()
            self.download.get_files(output=folder, option=download_option, start_at=start, end_at=end, cbr=compress)
        except Exception as e:
            message = f"Something went wrong. {e}"
        finally:
            self.info_label.configure(text=message)
            self._default_state()

    def download_chapters(self, url):
        threading.Thread(target=lambda: self._download_files(), daemon=True).start()

