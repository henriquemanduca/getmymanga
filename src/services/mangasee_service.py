import asyncio
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
                                add_leading_zeros,
                                calculate_md5)


def get_directory_value(directory: str):
    if len(directory) == 2:
        return directory[1:], directory[0:1]
    if len(directory) > 2:
        return directory[4:], directory[0:3]
    return "", None


async def chunk_routines(coroutines):
    if len(coroutines) > 10:
        for chunk in [coroutines[i:i + 10] for i in range(0, len(coroutines), 10)]:
            await asyncio.gather(*chunk)
    else:
        await asyncio.gather(*coroutines)


class MangaseeService:
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
            "directory_prefix": ""
        }

    def _get_manga_dict(self,) -> dict | None:
        return self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None

    def _get_directories_count(self,) -> int:
        return len(self._get_manga_dict()["directories"])

    def _get_manga_page_url(self, params: dict) -> str:
        manga_name = self.manga_name
        directory = params["directory"]
        chapter = remove_leading_zeros(params["chapter"])

        if "sub" in params and params["sub"]:
            chapter = f"{chapter[:-1]}.{chapter[-1:]}"

        if directory == 1:
            return f"{self.HOST}/read-online/{manga_name}-chapter-{chapter}-page-1.html"

        return f"{self.HOST}/read-online/{manga_name}-chapter-{chapter}-index-{directory}-page-1.html"

    def _get_search_details(self,):
        params = {
            "directory": 1,
            "chapter": "1",
        }
        url = self._get_manga_page_url(params)
        session = requests_html.HTMLSession()
        resp = session.get(url)
        content = resp.content.decode("utf-8")
        chapter_details_search = re.compile("vm.CHAPTERS = (.*);").search(content)

        if chapter_details_search:
            return chapter_details_search.groups()[0]
        else:
            raise Exception(f"No chapters found on \n {url}.")

    def search_chapters(self, manga_name: str) -> dict:
        raise Exception("Deprecated website!")

        self.manga_name = manga_name

        if manga_dict := self._get_manga_dict():
            return manga_dict

        self._set_manga_dict(manga_name)
        chapter_details_str = self._get_search_details()

        last_directory = "1"
        last_chapter = 0
        chapters = json.loads(chapter_details_str)

        for chapter_detail in chapters:
            try:
                manga_dict = self._get_manga_dict()
                directory, prefix = get_directory_value(chapter_detail["Directory"]) if chapter_detail["Directory"] != "" else last_directory, None

                chapter = int(remove_leading_zeros(chapter_detail["Chapter"][1:-1]))
                sub_chap = int(chapter_detail["Chapter"][-1])

                manga_dict["directory_prefix"] = prefix if prefix else ""

                if manga_dict["directories"].get(directory) is None:
                    manga_dict["directories"][directory] = { "chapters": {} }

                if sub_chap > 0 and chapter == last_chapter:
                    manga_dict["directories"][directory]["chapters"][last_chapter]["sub"] = chapter_detail
                else:
                    manga_dict["directories"][directory]["chapters"][chapter] = chapter_detail
                    manga_dict["chapters_count"] += 1

                manga_dict["directories"][directory]["last_chapter"] = chapter

                last_directory = directory
                last_chapter = chapter
            except Exception as e:
                raise Exception(f"Error on get chapters!\n{e}")

        self.manga_repository.update(name=self.manga_name, available_directories=last_directory)
        return self._get_manga_dict()

    def _get_url_image(self, host: str, directory: int, chapter: int, page: int) -> str:
        str_chapter = add_leading_zeros(chapter, 4)
        spage = add_leading_zeros(page, 3)

        manga_name = self.manga_name
        directory_prefix = self.manga_dict[self.manga_name]["directory_prefix"]

        if self._get_directories_count() > 1:
            return f"https://{host}/manga/{manga_name}/{directory_prefix}{directory}/{str_chapter}-{spage}.png"

        return f"https://{host}/manga/{manga_name}/{str_chapter}-{spage}.png"

    async def _get_items(
        self,
        session,
        params: dict
    ) -> list:
        items = []
        url = self._get_manga_page_url(params)

        resp = await session.request(method="GET", url=url)
        content = resp.content.decode("utf-8")
        host_pattern = re.compile('vm.CurPathName = "(.*)";')
        host_search = host_pattern.search(content)

        if host_search:
            host = host_search.groups()[0]
        else:
            raise Exception("No match for vm.CurPathName found!")

        for page in range(1, int(params["pages"]) + 1):
            chapter = params["chapter"]

            if "sub" in params and params["sub"]:
                chapter = f"{params["chapter"][:-1]}.{params["chapter"][-1:]}"

            download_url = self._get_url_image(host, params["directory"], chapter, page)
            sub_folder = os.path.join(add_leading_zeros(params["chapter"], 4), f"{add_leading_zeros(page, 3)}.png")
            items.append({"download_url": download_url, "sub_folder": sub_folder})

        return items

    async def _download_and_save_files(
        self,
        session: requests_html.AsyncHTMLSession,
        params: dict
    ) -> None:
        try:
            items = await self._get_items(session, params)

            for item in items:
                download_url = item["download_url"]
                save_path = os.path.join(params["output"], item["sub_folder"])

                if os.path.isfile(save_path):
                    continue

                resp = await session.request(method="GET", url=download_url)
                md5_resp = await calculate_md5(resp.content)

                async with aiofiles.open(save_path, "wb") as file:
                    await file.write(resp.content)

                async with aiofiles.open(save_path, "rb") as file:
                    saved_file_content = await file.read()
                    md5_file = await calculate_md5(saved_file_content)

                # Compare the two MD5 hashes
                if not md5_resp == md5_file:
                    raise Exception(f"MD5 hashes do not match. The file might be corrupted.\n{save_path}!")

            if self.compress_to_cbr:
                folder = os.path.join(params["output"], add_leading_zeros(params["chapter"], 4))
                create_cbr(folder)

        except asyncio.TimeoutError:
            raise Exception("Timeout in downloading chapter %s!", params["chapter"])

        except Exception as e:
            raise Exception(f"Error on download and save chapter!\n\n{e}")

    def _get_chap_details(self, output: str, chp: dict, sub: bool = False):
        chapter = chp["Chapter"][1:] if sub else chp["Chapter"][1:-1]
        directory, prefix = get_directory_value(chp["Directory"])
        directory = int(directory) if directory != "" else 1
        pages = int(chp["Page"])

        if not os.path.isdir(os.path.join(output, chapter)):
            os.mkdir(os.path.join(output, chapter))

        return chapter, directory, pages

    async def _download_chapters(self, output: str, chapters_details: typing.Iterable) -> None:
        session = requests_html.AsyncHTMLSession()
        coroutines = []

        last_downloaded = 0
        last_directory = 0

        for ch_detail in chapters_details:
            chapter, directory, pages = self._get_chap_details(output, ch_detail)
            params = {
                "output": output,
                "directory": directory,
                "chapter": chapter,
                "pages": pages,
                "sub": False
            }
            coroutines.append(self._download_and_save_files(session, params))

            if "sub" in ch_detail:
                chapter, directory, pages = self._get_chap_details(output, ch_detail["sub"], True)
                params = {
                    "output": output,
                    "directory": directory,
                    "chapter": chapter,
                    "pages": pages,
                    "sub": True
                }
                coroutines.append(self._download_and_save_files(session, params))

            last_downloaded = chapter
            last_directory = directory

        # Save the latest one chosen
        self.manga_repository.update(name=self.manga_name, last_downloaded=last_downloaded, last_directory=last_directory)
        await chunk_routines(coroutines=coroutines)

    def _get_folder(self, folder: str) -> str:
        temp_path = folder if folder != "" else get_default_download_folder()
        return create_folder(os.path.join(temp_path, self.manga_name))

    def _get_directory(self, directory: int) -> dict:
        return self._get_manga_dict()["directories"][str(directory)]

    def get_files(self, params_dic):
        raise Exception("Deprecated website!")

        start_at = 1
        end_at = 1

        if params_dic["download_option"] == "Range":
            start_at = params_dic["start_at"]
            end_at = params_dic["end_at"]

            if start_at > end_at:
                end_at = start_at

        self.compress_to_cbr = params_dic["cbr"]

        download_folder = self._get_folder(params_dic["output"])
        target_chapters = []

        directory = self._get_directory(params_dic["directory_option"])
        last_chapter = directory["last_chapter"]

        if start_at > last_chapter:
            raise Exception(f"The last chapters for this directory is {last_chapter}!")

        for ch in range(start_at, end_at + 1):
            chapter = directory["chapters"].get(ch)
            if chapter:
                target_chapters.append(chapter)

        asyncio.run(self._download_chapters(download_folder, target_chapters))

