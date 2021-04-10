#!/usr/bin/env python

"""Minecraft mod pack downloader."""

from dataclasses import dataclass
import datetime
from distutils.version import StrictVersion
from enum import Enum
from functools import lru_cache
from string import ascii_letters, digits
import sys
from typing import Iterable

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import yaml

__author__ = 'buhanec'
__version__ = '0.2'

VALID_VERSION = set(digits + ascii_letters + '.')


def version_score(version: str):
    """
    Scores a version string.

    :param version: Version string.
    :return: Version score.
    """
    try:
        StrictVersion(version)
        return len(version) * 2
    except ValueError:
        return len([c for c in version if c == '.' or c in digits])


def mod_version(filename: str, game_ver: Iterable[str]) -> str:
    """
    Attempt to extract mod version from mod filename.

    :param filename: Mod filename.
    :param game_ver: Game version of mod.
    :return: Mod version.
    """
    sep = '-_ ()[]. '
    if ' ' not in filename:
        filename = filename.replace('-', ' ')
    filename = ''.join([i if i in VALID_VERSION else ' ' for i in filename])
    for ver in game_ver:
        filename = filename.replace(ver, ' ')
    parts = [p.strip(sep + ascii_letters) for p in filename.split()]
    if not parts:
        return ''
    return max(parts, key=version_score)


class Channel(Enum):
    ALPHA = 'A'
    BETA = 'B'
    RELEASE = 'R'


@dataclass
class Mod:
    channel: str
    filename: str
    size: str
    uploaded: int
    game_version: str
    downloads: int
    link: str

    @property
    def uploaded_dt(self):
        return datetime.datetime.fromtimestamp(self.uploaded, datetime.timezone.utc)

    @property
    def mod_version(self):
        # The lazy solution to only having max patch
        major_minor, patch = self.game_version.rsplit('.', maxsplit=1)
        versions = [f'{major_minor}.{p}' for p in range(0, int(patch) + 1)]
        return mod_version(self.filename, versions)


class Browser:

    def __init__(self, headless=True):
        options = Options()
        options.headless = headless
        options.add_argument("--log-level=3")
        options.add_argument('--disable-logging')
        self._driver = webdriver.Chrome(options=options)

    def close(self):
        self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @lru_cache(maxsize=None)
    def mc_versions(self):
        url = 'https://www.curseforge.com/minecraft/mc-mods'
        self._driver.get(url)
        dropdown = self._driver.find_element_by_id('filter-game-version')
        opts = dropdown.find_elements_by_tag_name('option')
        return {o.text.strip(): o.get_attribute('value') for o in opts}

    @lru_cache(maxsize=None)
    def last_file(self, cid: str, game_ver: str = 'Minecraft 1.16'):
        sem_game_ver = self.mc_versions().get(game_ver, game_ver)
        url = f'https://www.curseforge.com/minecraft/mc-mods/{cid}/files/all?filter-game-version={sem_game_ver}'
        self._driver.get(url)
        soup = BeautifulSoup(self._driver.page_source, features='html.parser')
        table = soup.table
        if table is None:
            raise RuntimeError('No files for ' + cid + ': ' + url)
        cols = [e.text.strip() for e in soup.table.thead.find_all('th')]
        cells = table.tbody.tr.find_all('td')
        thing = dict(zip(cols, cells))

        return Mod(
            channel=Channel(thing['Type'].text.strip()),
            filename=thing['Name'].a.text.strip(),
            size=thing['Size'].text.strip(),
            uploaded=int(thing['Uploaded'].abbr['data-epoch']),
            game_version=thing['Game Version'].div.div.text.strip(),
            downloads=int(thing['Downloads'].text.strip().replace(',', '')),
            link='https://www.curseforge.com' + thing['Actions'].a['href'],
        )


def main(filename: str, game_ver: str = 'Minecraft 1.16'):
    with open(filename) as f:
        data = yaml.load(f, Loader=yaml.Loader)

    with Browser(headless=False) as browser:
        for category, mods in data.items():
            for mod_id, status in mods.items():
                latest = browser.last_file(mod_id, game_ver)
                if str(status['current']) != latest.mod_version and latest.uploaded > status['updated']:
                    print('Update for', mod_id, '-', latest.filename)
                    print('  > Current:', status['current'])
                    print('  > New:', latest.mod_version, 'for', latest.game_version, '[', latest.channel, ']')
                    print('  >', latest.uploaded, '-', latest.uploaded_dt)
                    print('  >', latest.link)
                else:
                    status['updated'] = latest.uploaded

    with open('client2.yaml', 'w') as f:
        yaml.dump(data, f, sort_keys=False)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
