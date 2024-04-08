import asyncio
import logging
import subprocess
import os

LOGGER = logging.getLogger()

class DownloadService:
    def __init__(self, url=None):
        self.download_button = None
        self.progress_bar = None

    def release_buttons(self):
        if self.download_button:
            self.download_button.configure(state="normal")
        if self.progress_bar:
            self.progress_bar.stop()


    def _get_file_name(self):
        return self._yt.title.replace("|", "").replace(" ", "_").replace("*", "")


    async def _download_files(self, url, res):
        self.release_buttons()

