import asyncio
import os

from src.repositories.manga import MangaRepository
from src.services.utils import (remove_files,
                                get_default_download_folder,
                                create_folder,
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
        return create_folder(os.path.join(temp_path, f"{self.manga_name}_br"))

    def _get_manga_dict(self, name: str | None = None) -> dict | None:
        if name != None:
            self.manga_name = name

        manga_dict = self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None
        if manga_dict == None:
            self._set_manga_dict(name)
        else:
            return manga_dict

    def _get_directory(self, directory: int) -> dict:
        return self._get_manga_dict()["directories"][directory]

    def _override_chapter_folder(self, output, chapter):
        folder = add_leading_zeros(chapter, 4)
        path = os.path.join(output, folder)

        if os.path.isdir(path):
            remove_files(path)

        os.mkdir(os.path.join(output, folder))

    async def _chunk_routines(self, coroutines):
        if len(coroutines) > 5:
            for chunk in [coroutines[i:i + 5] for i in range(0, len(coroutines), 5)]:
                await asyncio.gather(*chunk)
        else:
            await asyncio.gather(*coroutines)