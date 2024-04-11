import asyncio
import logging
import subprocess
import os
import json
import requests_html
import re
import typing

from src.services.utils import remove_leading_zeros, get_default_download_folder, create_folder
from src.repositories.manga import MangaRepository

LOGGER = logging.getLogger()


class DownloadService:
    HOST = "https://mangasee123.com"

    def __init__(self):
        self.chapters_check = False
        self.manga_dict = {"name": str, "last_one": int, "chapters": {}}
        self.manga_repository = MangaRepository()

    def get_manga_page_url(self, manga_name: str, chapter: str, page: str) -> str:
        manga_name_url = manga_name.replace(" ", "-")
        self.manga_dict["name"] = manga_name_url

        return f"{self.HOST}/read-online/{manga_name_url}-chapter-{chapter}-page-{page}.html"

    def save_manga(self, manga_name: str):
        manga_db = self.manga_repository.get_by_name(manga_name)
        if not manga_db:
            self.manga_repository.create(manga_name)

    def get_chapters(self, manga_name) -> dict:
        url = self.get_manga_page_url(manga_name, "1", "1")

        session = requests_html.HTMLSession()
        resp = session.get(url)
        content = resp.content.decode("utf-8")

        chapter_details_search = re.compile("vm.CHAPTERS = (.*);").search(content)

        if chapter_details_search:
            chapter_details_str = chapter_details_search.groups()[0]
        else:
            raise Exception(f"No chapters found on \n {url} !")

        self.save_manga(manga_name)

        chapters = json.loads(chapter_details_str)

        for chapter_detail in chapters:
            chapter = int(remove_leading_zeros(chapter_detail["Chapter"][1:-1]))
            self.manga_dict["chapters"][chapter] = chapter_detail
            self.manga_dict["last_one"] = chapter

        self.chapters_check = True

        return self.manga_dict

    async def download_chapters(self, name: str, chapter_details: typing.Iterable) -> None:
        session = requests_html.AsyncHTMLSession()
        coroutines = []

        for ch_detail in chapter_details:
            chapter = ch_detail["Chapter"][1:-1]
            pages = int(ch_detail["Page"])

            if not os.path.isdir(os.path.join(name, chapter)):
                os.mkdir(os.path.join(name, chapter))

            coroutines.append(
                download_and_save_chapter(session, name, chapter, pages),
            )
        await asyncio.gather(*coroutines)

    def get_files(self, output="", option="all", start_at=1, end_at=1, cbr=False):
        if not self.chapters_check:
            raise Exception("Chapters not checked yet!")

        folder = output if output == "" else get_default_download_folder()

        last_one = self.manga_dict["last_one"]
        if option == "all":
            start_at = 1
            end_at = last_one
        elif option == "range":
            start_at = start_at
            end_at = end_at
        else:
            start_at = last_one
            end_at = last_one

        if cbr:
            pass

        self.chapters_check = False

        folder = create_folder(f"{folder}/{self.manga_dict['name']}")

