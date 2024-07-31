import asyncio
import subprocess
import os
import aiofiles
import json
import requests_html
import re
import typing

from src.repositories.manga import MangaRepository
from src.services.utils import (remove_leading_zeros,
                                get_default_download_folder,
                                create_folder,
                                create_cbr,
                                add_leading_zeros)


class DownloadMangaseeService:
    HOST = "https://mangasee123.com"

    def __init__(self):
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

    def _get_directories_count(self,) -> int:
        return len(self._get_manga_dict()["directories"])

    def get_manga_page_url(self, directory: int, chapter: str, page: str) -> str:
        manga_name = self.manga_name
        if directory == 1:
            return f"{self.HOST}/read-online/{manga_name}-chapter-{chapter}-page-{page}.html"

        return f"{self.HOST}/read-online/{manga_name}-chapter-{chapter}-index-{directory}-page-{page}.html"

    def _get_page_image_url(self, host: str, directory: int, chapter: int, page: int) -> str:
        schapter = add_leading_zeros(chapter, 4)
        spage = add_leading_zeros(page, 3)
        manga_name = self.manga_name

        if self._get_directories_count() > 1:
            return f"https://{host}/manga/{manga_name}/Part{directory}/{schapter}-{spage}.png"

        return f"https://{host}/manga/{manga_name}/{schapter}-{spage}.png"

    def _get_chapter_details(self,):
        url = self.get_manga_page_url(1, "1", "1")
        session = requests_html.HTMLSession()
        resp = session.get(url)
        content = resp.content.decode("utf-8")
        chapter_details_search = re.compile("vm.CHAPTERS = (.*);").search(content)

        if chapter_details_search:
            return chapter_details_search.groups()[0]
        else:
            raise Exception(f"No chapters found on \n {url} !")

    def find_directories(self, manga_name: str) -> dict:
        self.manga_name = manga_name

        if manga_dict := self._get_manga_dict():
            return manga_dict

        self._set_manga_dict(manga_name)

        chapter_details_str = self._get_chapter_details()

        last_directory = "1"
        chapters = json.loads(chapter_details_str)

        for chapter_detail in chapters:
            try:
                manga_dict = self._get_manga_dict()

                directory = chapter_detail["Directory"][4:] if chapter_detail["Directory"] != "" else last_directory
                chapter = int(remove_leading_zeros(chapter_detail["Chapter"][1:-1]))

                if manga_dict["directories"].get(directory) is None:
                    manga_dict["directories"][directory] = { "chapters": {} }

                manga_dict["directories"][directory]["chapters"][chapter] = chapter_detail
                manga_dict["directories"][directory]["last_chapter"] = chapter
                manga_dict["chapters_count"] += 1

                last_directory = directory
            except Exception as e:
                raise Exception(f"Error on get chapters!\n{e}")

        return self._get_manga_dict()

    async def _get_download_url_items(
        self,
        session,
        directory: int,
        chapter: int,
        pages: int
    ) -> list:
        items = []
        url = self.get_manga_page_url(directory, remove_leading_zeros(str(chapter)), "1")

        resp = await session.request(method="GET", url=url)
        content = resp.content.decode("utf-8")
        host_pattern = re.compile('vm.CurPathName = "(.*)";')
        host_search = host_pattern.search(content)

        if host_search:
            host = host_search.groups()[0]
        else:
            raise Exception("No match for vm.CurPathName found!")

        for page in range(1, int(pages) + 1):
            download_url = self._get_page_image_url(host, directory, chapter, page)
            sub_folder = os.path.join(add_leading_zeros(chapter, 4), f"{add_leading_zeros(page, 3)}.png")
            items.append({"download_url": download_url, "sub_folder": sub_folder})

        return items

    async def _download_and_save_chapter(
        self,
        session: requests_html.AsyncHTMLSession,
        output: str,
        directory: int,
        chapter: int,
        pages: int
    ) -> None:
        folder = ""
        try:
            items = await self._get_download_url_items(session, directory, chapter, pages)
            for item in items:
                download_url = item["download_url"]
                save_path = os.path.join(output, item["sub_folder"])
                if os.path.isfile(save_path):
                    continue

                resp = await session.request(method="GET", url=download_url)
                async with aiofiles.open(save_path, "wb") as file:
                    await file.write(resp.content)

            if self.compress_to_cbr:
                folder = os.path.join(output, add_leading_zeros(chapter, 4))
                create_cbr(folder)

        except asyncio.TimeoutError:
            raise Exception("Timeout in downloading chapter %s!", chapter)

        except Exception as e:
            raise Exception(f"Error on download and save chapter!\n{e}")

    async def _download_chapters(self, output: str, chapter_details: typing.Iterable) -> None:
        session = requests_html.AsyncHTMLSession()
        coroutines = []
        last_downloaded = 0

        for ch_detail in chapter_details:
            chapter = ch_detail["Chapter"][1:-1]
            directory = ch_detail["Directory"][4:]
            directory = int(directory) if directory != "" else 1
            pages = int(ch_detail["Page"])

            if not os.path.isdir(os.path.join(output, chapter)):
                os.mkdir(os.path.join(output, chapter))

            coroutines.append(
                self._download_and_save_chapter(session, output, directory, chapter, pages),
            )
            last_downloaded = chapter

        # Save the the latest one chosen
        manga = self.manga_repository.get_by_name(self.manga_dict["name"])
        self.manga_repository.update(manga.id, last_downloaded=last_downloaded)

        await self._chunk_routines(coroutines=coroutines)

    async def _chunk_routines(self, coroutines):
        if len(coroutines) > 10:
            for chunk in [coroutines[i:i + 10] for i in range(0, len(coroutines), 10)]:
                await asyncio.gather(*chunk)
        else:
            await asyncio.gather(*coroutines)

    def _get_folder(self, folder: str) -> str:
        temp_path = folder if folder != "" else get_default_download_folder()
        return create_folder(os.path.join(temp_path, self.manga_dict['name']))

    def _get_directory(self, directory: int) -> dict:
        return self.manga_dict["directories"][str(directory)]

    def get_files(self, params_dic):
        # if not self.chapters_check:
        #     raise Exception("Chapters not checked yet!")

        if params_dic["download_option"] == "Range":
            start_at = params_dic["start_at"]
            end_at = params_dic["end_at"]

            if start_at > end_at:
                end_at = start_at

        self.compress_to_cbr = params_dic["cbr"]

        download_folder = self._get_folder(params_dic["output"])
        target_chapters = []

        directory = self._get_directory(params_dic["directory_option"])

        for ch in range(start_at, end_at + 1):
            chapter = directory["chapters"].get(ch)
            if chapter:
                target_chapters.append(chapter)

        asyncio.run(self._download_chapters(download_folder, target_chapters))

