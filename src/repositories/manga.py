from typing import Any

from src.database.connection import Connection
from src.models.manga import Manga


Connection.get_db().create_tables([Manga])


class MangaRepository:

    def create(self, name: str) -> Manga:
        if manga := self.get_by_name(name):
            return manga

        return Manga.create(name=name,
                            last_directory=1,
                            last_downloaded=1,
                            available_directories=1)

    def get_by_id(self, id: int) -> Any | None:
        try:
            return Manga.get(Manga.id == id)
        except Manga.DoesNotExist:
            return None

    def get_by_name(self, name: str) -> Manga | None:
        try:
            return Manga.get(Manga.name == name)
        except Manga.DoesNotExist:
            return None

    def update(self, **kwargs) -> Manga | None:
        manga = None

        if id := kwargs.get("id"):
            manga = self.get_by_id(id)
        elif name := kwargs.get("name"):
            manga = self.get_by_name(name)

        if manga:
            if name := kwargs.get("name"):
                manga.name = name

            manga.last_directory = 1
            if last_directory := kwargs.get("last_directory"):
                manga.last_directory = last_directory

            if last_downloaded := kwargs.get("last_downloaded"):
                manga.last_downloaded = last_downloaded

            if available_directories := kwargs.get("available_directories"):
                manga.available_directories = available_directories

            manga.save()
            return manga

        return None

    def delete(self, manga_id: int) -> bool:
        manga = self.get_by_id(manga_id)

        if manga:
            manga.delete_instance()
            return True

        return False

    def get_all(self) -> list[Manga]:
        return Manga.select()
