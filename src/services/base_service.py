from src.repositories.manga import MangaRepository

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

    def _get_manga_dict(self,) -> dict | None:
        return self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None