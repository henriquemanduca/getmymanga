from src.database.connection import Connection
from src.models.manga import Manga


Connection.get_db().create_tables([Manga])

class MangaRepository():
    def create(self, name: str) -> Manga:
        return Manga.create(name=name, last_one=0)

    def get_by_id(self, id) -> Manga:
        try:
            return Manga.get(Manga.id == id)
        except Manga.DoesNotExist:
            return None

    def get_by_name(self, name) -> Manga:
        try:
            return Manga.get(Manga.name == name)
        except Manga.DoesNotExist:
            return None

    def update(self, id, name=None, last_one=None) -> Manga:
        manga = self.get_by_id(id)
        if manga:
            if name:
                manga.name = name
            if last_one:
                manga.last_one = last_one
            manga.save()
            return manga
        return None

    def delete(self, id) -> bool:
        manga = self.get_by_id(id)
        if manga:
            manga.delete_instance()
            return True
        return False

    def get_all(self):
        return Manga.select()
