import asyncio
import os

from src.repositories.manga import MangaRepository

from src.services.utils import (remove_leading_zeros,
                                get_default_download_folder,
                                create_folder,
                                create_cbr,
                                add_leading_zeros)

class BaseService():

    def __init__(self) -> None:
        self.compress_to_cbr = False
        self.manga_name = None
        self.manga_dict = {}
        self.manga_repository = MangaRepository()

    def _set_manga_dict(self, name: str) -> None:
        self.manga_repository.create(name)
        self.manga_dict[self.manga_name] = {
            "name": name,
            "chapters_count": 0,
            "directories": {},
        }

    def _get_folder(self, folder: str) -> str:
        temp_path = folder if folder != "" else get_default_download_folder()
        return create_folder(os.path.join(temp_path, self.manga_name))

    def _get_manga_dict(self, name: str = "") -> dict | None:
        manga_dict = self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None

        if manga_dict == None:
            self.manga_name = name
            self._set_manga_dict(name)
        else:
            return manga_dict

    def _get_directory(self, directory: int) -> dict:
        return self._get_manga_dict()["directories"][str(directory)]

    async def _chunk_routines(self, coroutines):
        if len(coroutines) > 10:
            for chunk in [coroutines[i:i + 10] for i in range(0, len(coroutines), 10)]:
                await asyncio.gather(*chunk)
        else:
            await asyncio.gather(*coroutines)