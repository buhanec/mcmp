from typing import List, Tuple, Iterable, Optional
from bs4 import BeautifulSoup, element
import requests
import requests_cache
from operator import itemgetter
from datetime import datetime
import pytz
import re

requests_cache.install_cache('demo_cache', expire_after=1*60*60)


class Version(tuple):
    """Version(major, minor, patch)"""

    __slots__ = ()

    _fields = ('major', 'minor', 'patch')

    def __new__(cls, major, minor, patch=0):
        """Create new instance of Version(major, minor, patch)"""
        return tuple.__new__(cls, (int(major), int(minor), int(patch)))

    def __str__(self):
        """Return string representation"""
        return '.'.join(map(str, self))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return (f'{self.__class__.__name__}(major={self.major}, '
                f'minor={self.minor}, patch={self.patch})')

    major = property(itemgetter(0), doc='Alias for field number 0')

    minor = property(itemgetter(1), doc='Alias for field number 1')

    patch = property(itemgetter(2), doc='Alias for field number 2')


class NoMatchingMod(Exception):
    """No mod matching version required"""


VER_MAP = {
    None: '',
    '1.10.2': '2020709689:6170'
}
PARSER = 'html.parser'


def mod_version(filename: str, name: str, game_ver: Iterable[str]) -> str:
    sep = '-_ ()[].'
    word_pattern = re.compile('[\W_]+')
    for suffix in ('.jar', '.zip'):
        filename = filename.replace(suffix, '')
    for ver in game_ver:
        filename = filename.replace(ver, '')
    for word in ('universal', 'MC', 'mc'):
        word = word_pattern.sub('', word)
        filename = filename.replace(word, '')
    for part in name.split():
        if part not in sep:
            filename = filename.replace(part.strip(sep), '')
            filename = filename.replace(part.strip(sep).lower(), '')
    return filename.strip(sep)


def versions(info: element.Tag, skip_java=False) -> List[str]:
    extra = info.find(class_='additional-versions')
    if extra is not None:
        ret = extra['title'][5:-6].split('</div><div>')
        if skip_java:
            return [v for v in ret if not v.startswith('Java ')]
        return ret
    return [info.find(class_='version-label').text]


def link(info: element.Tag) -> Tuple[str, int, int]:
    a = info.find(class_='project-file-name-container').a
    return a['data-name'], int(a['data-id']), int(a['href'].rsplit('/', 1)[1])


def file_size(info: element.Tag) -> int:
    mod = {
        'B': 2 ** 0,
        'KB': 2 ** 10,
        'MB': 2 ** 20
    }
    size, unit = info.find(class_='project-file-size').text.strip().split()
    return round(float(size.replace(',', '')) * mod[unit])


def uploaded(info: element.Tag) -> datetime:
    return datetime.fromtimestamp(int(info.abbr['data-epoch']), pytz.utc)


def mod_name(root: element.Tag) -> str:
    return root.find('h1', class_='project-title').text.strip()


def channel(info: element.Tag) -> str:
    return info.find(class_='project-file-release-type').div['class'][0][:-6]


def get_mod(cid: str, game_ver: Optional[str]='1.10.2'):
    url = f'http://minecraft.curseforge.com/projects/{cid}/files?filter-game-version={VER_MAP[game_ver]}'
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.status_code, url)

    bs = BeautifulSoup(response.text, PARSER)
    name = mod_name(bs)
    info = bs.find('tr', class_='project-file-list-item')

    if info is None:
        return get_mod(cid, game_ver=None)

    mc_versions = versions(info)
    filename, cid, fid = link(info)

    return {
        'channel': channel(info),
        'cid': cid,
        'name': name,
        'mod_ver':  mod_version(filename, name, mc_versions),
        'fid': fid,
        'approx_size': file_size(info),
        'uploaded': uploaded(info),
        'accepted': game_ver in mc_versions,
        'latest_mc': sorted(mc_versions)[0]
    }
