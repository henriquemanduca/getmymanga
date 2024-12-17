import tkinter as tk
import customtkinter as ctk
import logging
import os
import threading
import requests

from CTkMessagebox import CTkMessagebox as mbox

from src.repositories.manga import MangaRepository
from src.services.mangasee_service import MangaseeService
from src.services.mangaonline_service import MangaOnlineService
from src.services.utils import get_default_download_folder, get_sources


logging.basicConfig()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Get my manga!")
        window_width = 605
        window_height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(True, True)
        self.init_vars()
        self.create_widgets()
        self._get_history()
        self._source_combobox(self.get_default_source())

    def init_vars(self):
        if "nt" == os.name:
            self.wm_iconbitmap(bitmap="./resources/icon.ico")
        else:
            img = tk.PhotoImage(file="./resources/icon2.png")
            self.tk.call('wm', 'iconphoto', self._w, img)

        self.manga_repository = MangaRepository()
        self.download_service = None
        self.dir_option_var = tk.StringVar()
        self.download_option_var = tk.StringVar()
        # self.history_option_var = tk.StringVar()
        self.history_option_var = tk.StringVar(value=self.get_last_manga())
        self.source_option_var = tk.StringVar(value=self.get_default_source())

        self.folder_var = tk.StringVar(value=f"{get_default_download_folder()}")
        self.manga_name_var = tk.StringVar(value="")

        self.chap_start_var = tk.StringVar()
        self.chap_end_var = tk.StringVar()

        self._set_range(1, 5)

        self.checkbox_compress = tk.BooleanVar(value=False)

    def create_widgets(self):
        row = 1
        option_label = ctk.CTkLabel(self, text="Save on:")
        option_label.grid(row=row, column=0, padx=5, pady=0, sticky="w")

        manga_label = ctk.CTkLabel(self, text="Name (from URL):")
        manga_label.grid(row=row, column=3, padx=5, pady=0, sticky="w")

        row += 1
        folder_entry = ctk.CTkEntry(self, textvariable=self.folder_var)
        folder_entry.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        manga_name = ctk.CTkEntry(self, textvariable=self.manga_name_var)
        manga_name.grid(row=row, column=3, columnspan=2, padx=5, pady=5, sticky="ew")

        row += 1
        history_label = ctk.CTkLabel(self, text="History:")
        history_label.grid(row=row, column=0, padx=5, pady=0, sticky="w")

        history_label = ctk.CTkLabel(self, text="Source:")
        history_label.grid(row=row, column=3, padx=5, pady=0, sticky="w")

        row += 1
        self.history_combobox = ctk.CTkComboBox(
            self, state="readonly", values=[], command=self._history_combobox, variable=self.history_option_var
        )
        self.history_combobox.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="we")

        self.source_combobox = ctk.CTkComboBox(
            self, state="readonly", values=get_sources(), command=self._source_combobox, variable=self.source_option_var
        )
        self.source_combobox.grid(row=row, column=3, columnspan=1, padx=5, pady=5, sticky="we")

        self.load_button = ctk.CTkButton(self,  text="Search Chapters", command=lambda: self.search_chapters())
        self.load_button.grid(row=row, column=4, columnspan=1, padx=5, pady=5, sticky="we")

        row += 1
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=row, column=0, columnspan=5, padx=5, pady=5, sticky="we")
        self.progress_bar.configure(mode="indeterminnate")

        row += 1
        self.info_label = ctk.CTkLabel(self, text="Any information loaded...")
        self.info_label.grid(row=row, column=0, columnspan=5, padx=5, pady=5, sticky="w")

        row += 1
        option_label = ctk.CTkLabel(self, text="Directory:")
        option_label.grid(row=row, column=0, padx=5, pady=0, sticky="w")

        option_label = ctk.CTkLabel(self, text="Download options:")
        option_label.grid(row=row, column=2, padx=5, pady=0, sticky="w")

        chap_start_label = ctk.CTkLabel(self, text="Start:")
        chap_start_label.grid(row=row, column=3, padx=5, pady=0, sticky="w")

        chap_end_label = ctk.CTkLabel(self, text="End:")
        chap_end_label.grid(row=row, column=4, padx=5, pady=0, sticky="w")

        row += 1
        self.dir_combobox = ctk.CTkComboBox(
            self,
            state="readonly",
            values=["1"],
            variable=self.dir_option_var
        )
        self.dir_combobox.grid(row=row, column=0, columnspan=1, padx=5, pady=5, sticky="we")
        self.dir_combobox.set("1")

        self.info_combobox = ctk.CTkComboBox(
            self,
            state="readonly",
            values=["Range", "Last one"],
            command=self._info_combobox,
            variable=self.download_option_var
        )
        self.info_combobox.grid(row=row, column=2, columnspan=1, padx=5, pady=5, sticky="we")
        self.info_combobox.set("Range")

        self.chap_start = ctk.CTkEntry(self, textvariable=self.chap_start_var, placeholder_text="Start")
        self.chap_start.grid(row=row, column=3, columnspan=1, padx=5, pady=5, sticky="ew")

        self.chap_end = ctk.CTkEntry(self, textvariable=self.chap_end_var, placeholder_text="End")
        self.chap_end.grid(row=row, column=4, columnspan=1, padx=5, pady=5, sticky="ew")

        row += 1
        self.checkbox = ctk.CTkCheckBox(self, text="Compress to .cbr", variable=self.checkbox_compress)
        self.checkbox.grid(row=row, column=0, columnspan=2)

        self.download_button = ctk.CTkButton(self, text="Download", state="disabled", command=lambda: self.download_chapters())
        self.download_button.grid(row=row, column=3, columnspan=2, padx=5, pady=5, sticky="we")

        # define the grid
        # self.columnconfigure(0, weight=0)
        self.columnconfigure((0, 1, 2, 3), weight=0)

    def get_last_manga(self) -> str:
        return "Berserk"

    def get_default_source(self) -> str:
        return get_sources()[0]

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
        else:
            self._set_disabled_state([self.chap_start, self.chap_end])

    def _default_state(self):
        self.progress_bar.stop()
        self._set_normal_state([
            self.history_combobox,
            self.source_combobox,
            self.load_button,
            self.info_combobox,
            self.download_button,
            self.checkbox,
            self.chap_start,
            self.chap_end
        ])

    def _down_state(self):
        self.progress_bar.start()
        self._set_disabled_state([self.chap_start, self.chap_end])
        self._set_disabled_state([
            self.load_button,
            self.history_combobox,
            self.source_combobox,
            self.info_combobox,
            self.download_button,
            self.checkbox]
        )

    def _set_range(self, first_one, last_one):
        self.chap_start_var.set(str(first_one))
        self.chap_end_var.set(str(last_one))

    def _get_history(self):
        mangas = self.manga_repository.get_all()
        self.history_combobox.configure(values=[manga.name for manga in mangas])

    def _history_combobox(self, event=None):
        if name := event:
            manga = self.manga_repository.get_by_name(name)
            self._set_directory(manga.last_directory)

            next_chapter = manga.last_downloaded + 1
            next_range = next_chapter + 5

            self._set_range(next_chapter, next_range)
            self._set_directory(manga.available_directories)
            self.dir_option_var.set(manga.last_directory)

    def _source_combobox(self, event=None):
        if event == get_sources()[0]:
            self.download_service = MangaseeService()
        else:
            self.download_service = MangaOnlineService()

    def _set_directory(self, directories: int):
         self.dir_combobox.configure(values=[str(i) for i in range(1, directories + 1)])

    def _get_directories(self):
        manga_name = self.manga_name_var.get().replace(" ", "")
        manga_history = self.history_option_var.get()

        if manga_name == "" and manga_history == "":
            mbox(title="Info", message="Inform a manga name or select from history!")
            return
        else:
            manga_name = manga_name if manga_name != "" else manga_history

        self._down_state()
        message = ""

        try:
            manga_dict = self.download_service.search_chapters(manga_name)
            self.available_directories = manga_dict["directories"]

            direcotory_count = len(self.available_directories)
            chapters_count = manga_dict["chapters_count"]

            self._set_directory(len(self.available_directories))

            message = f"{direcotory_count} directories founded with {chapters_count} chapters available!"
        except requests.exceptions.ConnectionError:
            mbox(title="Warning", message="Could not connect to server", icon="warning", option_1="Cancel")
        except Exception as e:
            mbox(title="Error", message=f"Something went wrong.\n\n{e}", icon="cancel", option_1="Close")
        finally:
            self.info_label.configure(text=message)
            self._get_history()
            self._default_state()

    def search_chapters(self):
        threading.Thread(target=lambda: self._get_directories(), args=(), daemon=True).start()

    def _download_files(self):
        self._down_state()
        try:
            params_dic = {
                "output": self.folder_var.get(),
                "directory_option": int(self.dir_option_var.get()),
                "download_option": self.download_option_var.get(),
                "start_at": int(self.chap_start_var.get()),
                "end_at": int(self.chap_end_var.get()),
                "cbr": self.checkbox_compress.get()
            }

            self.download_service.get_files(params_dic)
            mbox(title="Info", message=f"Save it on {params_dic['output']}.")
        except Exception as e:
            mbox(title="Error", message=f"Something went wrong!\n\n{e}")
        finally:
            self._default_state()

    def download_chapters(self):
        threading.Thread(target=lambda: self._download_files(), daemon=True).start()

