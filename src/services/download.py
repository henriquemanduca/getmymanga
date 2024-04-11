import asyncio
import logging
import subprocess
import os
import aiofiles
import json
import requests_html
import re
import typing

from src.services.utils import remove_leading_zeros, get_default_download_folder, create_folder, add_leading_zeros
from src.repositories.manga import MangaRepository

LOGGER = logging.getLogger()


class DownloadService:
    HOST = "https://mangasee123.com"

    def __init__(self):
        self.chapters_check = False
        self.compress_to_cbr = False
        self.manga_dict = {"name": "", "last_one": 0, "chapters": {}}
        self.manga_repository = MangaRepository()

    def get_manga_page_url(self, manga_name: str, chapter: str, page: str) -> str:
        return f"{self.HOST}/read-online/{manga_name}-chapter-{chapter}-page-{page}.html"

    def save_manga(self, manga_name: str):
        manga_db = self.manga_repository.get_by_name(manga_name)
        if not manga_db:
            self.manga_repository.create(manga_name)

    def get_chapters(self, manga_name) -> dict:
        self.manga_dict["name"] = manga_name.replace(" ", "-")
        url = self.get_manga_page_url(self.manga_dict["name"], "1", "1")

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

    @staticmethod
    def _get_page_image_url(host: str, name: str, chapter: int, page: int) -> str:
        schapter = add_leading_zeros(chapter, 4)
        spage = add_leading_zeros(page, 3)
        return f"https://{host}/manga/{name}/{schapter}-{spage}.png"

    async def _get_chapter_download_and_save_data(
        self,
        session,
        name: str,
        chapter: int,
        pages: int
    ) -> list:
        data = []
        url = self.get_manga_page_url(name, str(chapter), "1")

        resp = await session.request(method="GET", url=url)
        content = resp.content.decode("utf-8")
        host_pattern = re.compile('vm.CurPathName = "(.*)";')
        host_search = host_pattern.search(content)

        if host_search:
            host = host_search.groups()[0]
        else:
            raise Exception("No match for vm.CurPathName found!")

        for page in range(1, int(pages) + 1):
            download_url = DownloadService._get_page_image_url(host, name, chapter, page)

            save_path = os.path.join(name, add_leading_zeros(chapter, 4), f"{add_leading_zeros(page, 3)}.png")

            data.append({"download_url": download_url, "save_path": save_path})

        return data

    async def _download_and_save_chapter(
        self,
        session: requests_html.AsyncHTMLSession,
        name: str,
        chapter: int,
        pages: int
    ) -> None:
        try:
            data = await self._get_chapter_download_and_save_data(session, name, chapter, pages)

            for d in data:
                download_url = d["download_url"]
                save_path = d["save_path"]

                if os.path.isfile(save_path):
                    continue

                resp = await session.request(method="GET", url=download_url)

                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(resp.content)

            if self.compress_to_cbr:
                folder = os.path.join(name, add_leading_zeros(chapter, 4))
                subprocess.run(["zip", "-r", f"{folder}.cbz", folder])
                # subprocess.run(["rm", "-r", folder])

        except asyncio.TimeoutError:
            LOGGER.warning("Timeout in downloading chapter %s!", chapter)

    async def _download_chapters(self, output: str, chapter_details: typing.Iterable) -> None:
        session = requests_html.AsyncHTMLSession()
        coroutines = []

        for ch_detail in chapter_details:
            chapter = ch_detail["Chapter"][1:-1]
            pages = int(ch_detail["Page"])

            if not os.path.isdir(os.path.join(output, chapter)):
                os.mkdir(os.path.join(output, chapter))

            coroutines.append(
                self._download_and_save_chapter(session, output, chapter, pages),
            )

        if len(coroutines) > 10:
            for chunk in [coroutines[i:i + 10] for i in range(0, len(coroutines), 10)]:
                await asyncio.gather(*chunk)
        else:
            await asyncio.gather(*coroutines)

    def get_files(self, output="", option="All", start_at=1, end_at=1, cbr=False):
        if not self.chapters_check:
            raise Exception("Chapters not checked yet!")

        folder = output if output == "" else get_default_download_folder()
        last_one = self.manga_dict["last_one"]

        if option == "All":
            start_at = 1
            end_at = last_one
        elif option == "Range":
            start_at = start_at
            end_at = end_at
        else:
            start_at = last_one
            end_at = last_one

        self.compress_to_cbr = cbr
        self.chapters_check = False

        # For testing
        start_at = 1
        end_at = 1

        folder = create_folder(f"{folder}/{self.manga_dict['name']}")

        target_chapters = []
        for ch in range(start_at, end_at + 1):
            chapter = self.manga_dict["chapters"].get(ch)
            if chapter:
                target_chapters.append(chapter)

        asyncio.run(self._download_chapters(folder, target_chapters))

