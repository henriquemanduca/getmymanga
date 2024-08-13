import asyncio
import os
import aiofiles
import requests_html
import re
import typing

from src.services.base_service import BaseService
from src.services.utils import (remove_leading_zeros,
                                create_cbr,
                                add_leading_zeros)


class MangaOnlineService(BaseService):
    HOST = "https://mangaonline.biz"

    def __init__(self):
        super().__init__()

    def _get_directories_count(self,) -> int:
        return 1

    def _get_manga_url(self,) -> str:
        return f"{self.HOST}/manga/{self.manga_name}/"

    async def _get_url_items(
        self,
        session,
        chapter: int,
        chapter_url: str
    ) -> list:
        items = []

        resp = await session.request(method="GET", url=chapter_url)
        content = resp.content.decode("utf-8")
        images_search = re.compile(r'src="(https://mangaonline.biz/wp-content/uploads/[^"]+)"').findall(content)

        if len(images_search) == 0:
            raise Exception("No match found!")

        page = 1
        for image_url in images_search:
            sub_folder = os.path.join(add_leading_zeros(chapter, 4), f"{add_leading_zeros(page, 3)}.png")
            items.append({"download_url": image_url, "sub_folder": sub_folder})
            page += 1

        return items

    async def _download_and_save_chapter(
        self,
        session: requests_html.AsyncHTMLSession,
        output: str,
        chapter: int,
        chapter_url: str,
    ) -> None:
        folder = ""
        try:
            items = await self._get_url_items(session, chapter, chapter_url)
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
            raise Exception(f"Error on download and save chapter!\n\n{e}")

    async def _download_chapters(self, output: str, chapter_details: typing.Iterable) -> None:
        session = requests_html.AsyncHTMLSession()
        coroutines = []
        last_downloaded = 0

        for ch_detail in chapter_details:
            chapter = ch_detail["Chapter"]
            chapter_url = ch_detail["URL"]

            self._override_chapter_folder(output, chapter)

            coroutines.append(
                self._download_and_save_chapter(session, output, chapter, chapter_url),
            )
            last_downloaded = chapter

        # Save the the latest one chosen
        self.manga_repository.update(name=self.manga_name, last_downloaded=last_downloaded)

        await self._chunk_routines(coroutines=coroutines)

    def get_files(self, params_dic):
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

        if len(target_chapters) == 0:
            raise Exception(f"Chapters not found on this directory!.")

        asyncio.run(self._download_chapters(download_folder, target_chapters))

    def _get_chapter_details(self,):
        url = self._get_manga_url()
        session = requests_html.HTMLSession()
        resp = session.get(url)
        content = resp.content.decode("utf-8")
        chapter_details_search = re.compile(r'<a href="([^"]+)">\s*Capítulo\s*(-?\d+)<span class="date">([^<]+)</span>').findall(content)

        if chapter_details_search:
            return sorted(chapter_details_search, key=lambda x: int(x[1]))
        else:
            raise Exception(f"No chapters found on \n {url} !")

    def find_directories(self, manga_name: str) -> dict:
        if manga_dict := self._get_manga_dict(manga_name):
            return manga_dict

        chapters = self._get_chapter_details()
        chapter_aux = 1

        for chapter_detail in chapters:
            try:
                manga_dict = self._get_manga_dict()

                directory = "1" if int(chapter_detail[1]) < 0 else "2"
                chapter = int(remove_leading_zeros(chapter_detail[1]))

                if chapter < 0:
                    chapter = chapter_aux
                    chapter_aux += 1

                if manga_dict["directories"].get(directory) is None:
                    manga_dict["directories"][directory] = { "chapters": {} }

                manga_dict["directories"][directory]["chapters"][chapter] = {
                    "Chapter": str(chapter),
                    "URL": chapter_detail[0]
                }
                manga_dict["directories"][directory]["last_chapter"] = chapter
                manga_dict["chapters_count"] += 1

                last_directory = directory
            except Exception as e:
                raise Exception(f"Error on get chapters!\n{e}")

        self.manga_repository.update(name=self.manga_name, available_directories=last_directory)

        return self._get_manga_dict()