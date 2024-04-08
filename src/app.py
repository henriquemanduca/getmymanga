import tkinter as tk
import customtkinter as ctk
import logging
import os
import threading

from src.services.download import DownloadService
from src.services.file_utils import get_default_download_folder

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
        window_width = 500
        window_height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(False, False)
        self.init_vars()
        self.create_widgets()

    def init_vars(self):
        self.down_service = DownloadService()

        if "nt" == os.name:
            self.wm_iconbitmap(bitmap = "./resources/icon.ico")
        else:
            img = tk.PhotoImage(file="./resources/icon2.png")
            self.tk.call('wm', 'iconphoto', self._w, img)

        self.app_logo = tk.PhotoImage(file="./resources/image.png")
        self.info_combobox_var = tk.StringVar()

        self.folder_var = tk.StringVar()
        self.folder_var.set(f"{get_default_download_folder()}/{self.APP_FOLDER}")

        self.url_var = tk.StringVar()
        self.url_var.set("Manga name here")

    def create_widgets(self):
        try:
            image_label = tk.Label(self, image=self.app_logo, borderwidth=0)
            image_label.grid(row=0, column=0, columnspan=3, padx=0, pady=0)
        except:
            print("Image not found")

        row = 1
        folder_label = ctk.CTkLabel(self, text="Save on:")
        folder_label.grid(row=row, column=0, padx=5, pady=5, sticky="e")
        folder_entry = ctk.CTkEntry(self, textvariable=self.folder_var)
        folder_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        row += 1
        manga_label = ctk.CTkLabel(self, text="Manga name:")
        manga_label.grid(row=row, column=0, padx=5, pady=5, sticky="e")
        url_entry = ctk.CTkEntry(self, textvariable=self.url_var)
        url_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        row += 1
        self.info_combobox = ctk.CTkComboBox(self, state="readonly", values=["720p", "1080p"], command=self.info_combobox_callback, variable=self.info_combobox_var)
        self.info_combobox.grid(row=row, column=1, padx=5, pady=5, sticky="we")
        self.info_combobox.set("1080p")

        self.download_button = ctk.CTkButton(self,  text="Download", command=lambda: self.download_chapters(self.url_var.get()))
        self.download_button.grid(row=row, column=2, padx=5, pady=5, sticky="we")

        row += 1
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=row, column=1, columnspan=3, padx=5, pady=5, sticky="we")
        self.progress_bar.configure(mode="indeterminnate")

        # define the grid
        self.columnconfigure(0, weight=0)
        self.columnconfigure((1,2), weight=1)

        # Pass controle to the service
        self.down_service.download_button = self.download_button
        self.down_service.progress_bar = self.progress_bar

    def info_combobox_callback(self, event=None):
        print(self.info_combobox_var.get())

    def get_info(self, url):
        try:
            self.down_service.get_infos(url)
            self.info_combobox.configure(values=self.down_service.resolutions)
            self.info_combobox.set(self.down_service.resolutions[0])
        finally:
            pass

    def download_chapters(self, url):
        self.progress_bar.start()
        self.download_button.configure(state="disabled")

        folder_option = self.folder_var.get()
        resolution_option = self.info_combobox_var.get()

        # Create a new thread for downloading the video
        threading.Thread(target=self.down_service.download_video, args=(folder_option, url, resolution_option), daemon=True).start()
