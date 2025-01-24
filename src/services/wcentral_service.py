import asyncio
import os
import aiofiles
import json
import requests_html
import re

from typing import List

from src.repositories.manga import MangaRepository
from src.services.utils import (remove_leading_zeros,
                                get_default_download_folder,
                                create_folder,
                                create_cbr,
                                add_leading_zeros,
                                calculate_md5)


async def chunk_routines(coroutines):
    if len(coroutines) > 10:
        for chunk in [coroutines[i:i + 10] for i in range(0, len(coroutines), 10)]:
            await asyncio.gather(*chunk)
    else:
        await asyncio.gather(*coroutines)


class WeebCentralService:
    HOST = "https://weebcentral.com"

    def __init__(self):
        self.compress_to_cbr = False
        self.manga_name = None
        self.manga_dict = {}
        self.manga_repository = MangaRepository()

    def _set_manga_dict(self, name: str):
        self.manga_repository.create(name)
        self.manga_dict[self.manga_name] = {
            "name": name,
            "directories": {},
            "chapters_count": 0
        }

    def _get_manga_dict(self,) -> dict | None:
        return self.manga_dict[self.manga_name] if self.manga_name in self.manga_dict else None

    def _get_directories_count(self,) -> int:
        return len(self._get_manga_dict()["directories"])

    def _get_manga_url(self) -> str:
        return f"{self.HOST}/series/{self.manga_name}/full-chapter-list"

    def _get_manga_chapter_url(self, chapter_url: str) -> str:
        chapter_code = chapter_url.split("/")[-1]
        return f"{self.HOST}/chapters/{chapter_code}/images?is_prev=False&current_page=1&reading_style=long_strip"

    async def _get_items(
        self,
        session,
        params: dict
    ) -> list:
        items = []

        url = self._get_manga_chapter_url(params['chapter_url'])
        resp = await session.request(method='GET', url=url)
        content = resp.content.decode('utf-8')

        pattern = re.compile(r'src="https://(.*?)"')
        chapter_pages = pattern.findall(content)

        for page in chapter_pages:
            items.append({"download_url": f'https://{page}'})

        return items

    async def _download_and_save_files(self, params: dict) -> None:
        session = requests_html.AsyncHTMLSession()

        try:
            items = await self._get_items(session, params)
            save_path = os.path.join(params['output'], params['chapter'])

            for item in items:
                download_url = item['download_url']
                resp = await session.request(method='GET', url=download_url)

                file_name = download_url.split('/')[-1]
                async with aiofiles.open(f'{save_path}/{file_name}', "wb") as file:
                    await file.write(resp.content)

            if self.compress_to_cbr:
                create_cbr(save_path)

        except asyncio.TimeoutError:
            raise Exception("Timeout in downloading chapter %s!", params["chapter"])

        except Exception as e:
            raise Exception(f"Error on download and save chapter!\n\n{e}")

    async def _download_chapters(self, output: str, chapters_url_list: List[str]) -> None:
        # session = requests_html.AsyncHTMLSession()
        coroutines = []

        last_downloaded = 0
        last_directory = 0

        for ch in chapters_url_list:
            chapter = add_leading_zeros(ch['num'], 4)

            if not os.path.isdir(os.path.join(output, chapter)):
                os.mkdir(os.path.join(output, chapter))

            params = {
                "output": output,
                "directory": 1,
                "chapter": chapter,
                "chapter_url": ch['url']
            }
            coroutines.append(self._download_and_save_files(params))

            last_downloaded = chapter
            last_directory = 1

        # Save the latest one
        self.manga_repository.update(name=self.manga_name, last_downloaded=last_downloaded, last_directory=last_directory)
        await chunk_routines(coroutines=coroutines)

    def _get_folder(self, folder: str) -> str:
        temp_path = folder if folder != "" else get_default_download_folder()
        return create_folder(os.path.join(temp_path, self.manga_name))

    def _get_directory(self, directory: int) -> dict:
        return self._get_manga_dict()["directories"][str(directory)]

    def _get_search_details(self) -> List[str]:
        url = self._get_manga_url()
        session = requests_html.HTMLSession()
        resp = session.get(url)
        content = resp.content.decode("utf-8")

        pattern = re.compile(r'<a href="(.*?)"')
        chapter_details_search = pattern.findall(content)

        if chapter_details_search:
            # remove last "#top" link
            chapter_details_search.pop()
            chapter_details_search.reverse()
            return chapter_details_search
        else:
            raise Exception(f"No chapters found at {url}!")

    def search_chapters(self, manga_name: str) -> dict:
        self.manga_name = manga_name

        if manga_dict := self._get_manga_dict():
            return manga_dict

        self._set_manga_dict(manga_name)
        chapters_url_list = self._get_search_details()

        last_directory = "1"
        for idx, chapter_url in enumerate(chapters_url_list, start=1):
            try:
                manga_dict = self._get_manga_dict()

                if manga_dict["directories"].get(last_directory) is None:
                    manga_dict["directories"][last_directory] = { "chapters": [] }

                manga_dict["directories"][last_directory]["chapters"].append(
                    {
                        "num": idx,
                        "url": chapter_url
                    }
                )

                manga_dict["directories"][last_directory]["last_chapter"] = idx
                manga_dict['chapters_count'] = idx
            except Exception as e:
                raise Exception(f"Error on get chapters!\n{e}")

        self.manga_repository.update(name=self.manga_name, available_directories=last_directory)
        return self._get_manga_dict()

    def get_files(self, params_dic):
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

        for index in range(start_at-1, end_at):
            target_chapters.append(directory["chapters"][index])

        asyncio.run(self._download_chapters(download_folder, target_chapters))

