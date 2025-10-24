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
        """
        Sets the manga dictionary for the given name.

        Args:
            name (str): The name of the manga.
        """
        self.manga_repository.create(name)
        self.manga_dict[self.manga_name] = {
            "name": name,
            "chapters_count": 0,
            "directories": {},
        }

    def _get_folder(self, folder: str) -> str:
        """
        Gets the folder for the manga.

        Args:
            folder (str): The folder path.

        Returns:
            str: The path to the manga folder.
        """
        temp_path = folder if folder != "" else get_default_download_folder()
        return create_folder(os.path.join(temp_path, f"{self.manga_name}_br"))

    def _get_manga_dict(self, name: str | None = None) -> dict | None:
        """
        Gets the manga dictionary for the given name.

        Args:
            name (str | None, optional): The name of the manga. Defaults to None.

        Returns:
            dict | None: The manga dictionary or None if not found.
        """
        if name != None:
            self.manga_name = name

        manga_dict = self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None
        if manga_dict == None:
            self._set_manga_dict(name)
        else:
            return manga_dict

    def _get_directory(self, directory: int) -> dict:
        """
        Gets the directory for the given chapter.

        Args:
            directory (int): The chapter number.

        Returns:
            dict: The directory dictionary.
        """
        return self._get_manga_dict()["directories"][directory]

    def _override_chapter_folder(self, output, chapter):
        """
        Overrides the chapter folder.

        Args:
            output (str): The output path.
            chapter (int): The chapter number.
        """
        folder = add_leading_zeros(chapter, 4)
        path = os.path.join(output, folder)

        if os.path.isdir(path):
            remove_files(path)

        os.mkdir(os.path.join(output, folder))

    async def _chunk_routines(self, coroutines):
        """
        Chunks the coroutines to be executed.

        Args:
            coroutines (list): The list of coroutines to be executed.
        """
        if len(coroutines) > 5:
            for chunk in [coroutines[i:i + 5] for i in range(0, len(coroutines), 5)]:
                await asyncio.gather(*chunk)
        else:
            await asyncio.gather(*coroutines)