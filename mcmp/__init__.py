#!/usr/bin/env python

"""Minecraft mod pack downloader."""

from typing import Tuple, Iterable, Dict
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup
import requests
import requests_cache
from datetime import datetime as dt
import pytz
import zipfile
import os
from distutils.version import StrictVersion
from string import digits, ascii_letters
import yaml
import sys

__author__ = 'buhanec'
__version__ = '0.1.dev.0'
__all__ = ('Mod', 'IncompatibleMod')

requests_cache.install_cache('demo_cache', expire_after=1*60*60)

VALID_VERSION = set(digits + ascii_letters + '.')
PARSER = 'html.parser'
SIZE_MOD = {
    'B': 2 ** 0,
    'KB': 2 ** 10,
    'MB': 2 ** 20
}


def mc_versions() -> Dict[str, str]:
    """
    Get MC versions mapping.

    :return: MC versions mapping.
    """
    url = 'https://minecraft.curseforge.com/mc-mods'
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, PARSER)
    select = soup.find('select', id='filter-game-version')
    return {o.text.strip(): o.attrs['value']
            for o in select.find_all('option')}


VER_MAP = mc_versions()


class IncompatibleMod(Exception):
    """Incompatible mod with Minecraft version."""


class Mod:
    """Curseforge mod."""

    def __init__(self, cid: str, game_ver: str='All Versions'):
        url = 'http://minecraft.curseforge.com/projects/{}/files?filter-game-version={}'.format(cid, VER_MAP[game_ver])
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, PARSER)
        info = soup.find('tr', class_='project-file-list-item')

        if info is None:
            raise IncompatibleMod('Mod {} not available for version {}'
                                  .format(cid, game_ver))

        # Mod name
        self.name = soup.find('h1', class_='project-title').text.strip()

        # Mod versions
        extra = info.find(class_='additional-versions')
        if extra is not None:
            versions = extra['title'][5:-6].split('</div><div>')
            self.mc_versions = [v for v in versions if not v.startswith('Java ')]
        else:
            self.mc_versions = [info.find(class_='version-label').text]

        link = info.find(class_='project-file-name-container').a
        self.filename = link['data-name']
        self.cid = int(link['data-id'])
        self.fid = link['href'].rsplit('/', 1)[1]

        size, unit = info.find(class_='project-file-size').text.strip().split()
        self.size = round(float(size.replace(',', '')) * SIZE_MOD[unit])

        self.channel = info.find(class_='project-file-release-type').div['class'][0][:-6]
        self.version = mod_version(self.filename, self.mc_versions) or info.abbr['data-epoch']
        self.uploaded = dt.fromtimestamp(int(info.abbr['data-epoch']), pytz.utc)

    def download(self, path: str) -> Tuple[str, int]:
        """
        Download mod file.

        :param path: Path to put file in.
        :return: Local path and file size.
        """
        url = 'https://minecraft.curseforge.com/projects/{}/files/{}/download'.format(self.cid, self.fid)
        response = requests.get(url)
        response.raise_for_status()

        local = os.path.join(path, os.path.basename(response.url))
        local_base = os.path.splitext(os.path.basename(local))[0]
        with open(local, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        # TODO: Make more generic
        if response.headers['Content-Type'] == 'application/x-zip-compressed':
            target = None
            with zipfile.ZipFile(local, 'r') as z:
                for filename in [f.filename for f in z.filelist]:
                    filename_base = os.path.splitext(os.path.basename(filename))[0]
                    if local_base == filename_base:
                        target = os.path.join(path, os.path.basename(filename))
                        with open(target, 'wb') as f:
                            f.write(z.open(filename).read())
                        break
            if target is not None:
                os.remove(local)
                local = target
        return local, int(response.headers['Content-Length'])

    @property
    def dict(self):
        return {
            'channel': self.channel,
            'cid': self.cid,
            'name': self.name,
            'filename': self.filename,
            'version':  self.version,
            'fid': self.fid,
            'uploaded': self.uploaded
        }

    def __repr__(self):
        return '<{name} {version}>'.format(**self.__dict__)


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


def main():
    download = sys.argv[1] == '--download' or sys.argv[1] == '-d'

    if sys.argv[-1].startswith('http'):
        with requests_cache.disabled():
            response = requests.get(sys.argv[-1])
        response.raise_for_status()
        mod_list = yaml.load(response.text)
    else:
        with open(sys.argv[-1], 'r') as f:
            mod_list = yaml.load(f)
    for mod in mod_list:
        try:
            mod = Mod(mod, game_ver='1.10.2')
            if download:
                mod.download('mods')
            print('  Success:', mod)
        except IncompatibleMod:
            print('  Incompatible:', mod)
    return 0


if __name__ == '__main__':
    sys.exit(main())
