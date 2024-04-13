from src.database.connection import Connection
from src.models.manga import Manga


Connection.get_db().create_tables([Manga])

class MangaRepository():
    def create(self, name: str) -> Manga:
        if manga := self.get_by_name(name):
            return manga

        return Manga.create(name=name, last_downloaded=0)

    def get_by_id(self, id: int) -> Manga:
        try:
            return Manga.get(Manga.id == id)
        except Manga.DoesNotExist:
            return None

    def get_by_name(self, name: str) -> Manga:
        try:
            return Manga.get(Manga.name == name)
        except Manga.DoesNotExist:
            return None

    def update(self, id: int, **kwargs) -> Manga:
        manga = self.get_by_id(id)

        if manga:
            if name := kwargs.get("name"):
                manga.name = name
            if last_downloaded := kwargs.get("last_downloaded"):
                manga.last_downloaded = last_downloaded
            manga.save()
            return manga

        return None

    def delete(self, id: int) -> bool:
        manga = self.get_by_id(id)
        if manga:
            manga.delete_instance()
            return True
        return False

    def get_all(self):
        return Manga.select()
