from typing import List, Tuple, Iterable, Optional
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup, element
import requests
import requests_cache
from datetime import datetime
import pytz
import re
from string import ascii_letters, digits
import zipfile
import os

requests_cache.install_cache('demo_cache', expire_after=1*60*60)


VER_MAP = {
    None: '',
    '1.10.2': '2020709689:6170'
}
PARSER = 'html.parser'


# TODO: Clean up and replace with a few regex
def mod_version(filename: str, name: str, game_ver: Iterable[str]) -> str:
    sep = '-_ ()[]. '
    for suffix in ('.jar', '.zip'):
        filename = filename.replace(suffix, '')
    for ver in game_ver:
        filename = filename.replace(ver, '')
    for word in ('universal', 'MC', 'mc', 'Mod', 'mod'):
        filename = filename.replace(word, '')
    for part in name.split():
        if part not in sep:
            filename = re.sub(part, '', filename, flags=re.IGNORECASE)
            part = re.sub('[\W_]+', '', part)
            filename = re.sub(part, '', filename, flags=re.IGNORECASE)
            part = re.sub('[^a-zA-Z]+', '', part)
            filename = re.sub(part, '', filename, flags=re.IGNORECASE)
    filename = filename.strip(sep)
    filename = filename.rsplit(' ', 1)[-1]
    filename = filename.rsplit('--', 1)[-1]
    filename = filename.strip(sep)
    if filename.startswith('v-'):
        filename = filename[2:]
    if len(filename) > 1:
        if filename[0] in ascii_letters and filename[1] in digits:
            filename = filename[1:]
    return filename


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


def get_mod(cid: str, game_ver: Optional[str]='1.10.2', download=False):
    url = 'http://minecraft.curseforge.com/projects/{}/files?' \
          'filter-game-version={}'.format(cid, VER_MAP[game_ver])
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

    size = file_size(info)

    if download and game_ver in mc_versions:
        get_mod_file(cid, fid)

    return {
        'channel': channel(info),
        'cid': cid,
        'name': name,
        'filename': filename,
        'mod_ver':  (mod_version(filename, name, mc_versions) or
                     info.abbr['data-epoch']),
        'fid': fid,
        'size': size,
        'uploaded': uploaded(info),
        'accepted': game_ver in mc_versions,
        'latest_mc': sorted(mc_versions)[0]
    }


def get_mod_file(cid: int, fid: int):
    url = 'https://minecraft.curseforge.com/projects/{}/files/{}/' \
          'download'.format(cid, fid)
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.status_code, url)
    local = 'mods/' + response.url.split('/')[-1]
    with open(local, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    # TODO: Make more generic
    if response.headers['Content-Type'] == 'application/x-zip-compressed':
        with zipfile.ZipFile(local, 'r') as z:
            local_jar = local[:-4] + '.jar'
            with open(local_jar, 'wb') as f:
                f.write(z.open(local_jar).read())
        os.remove(local)
    return local, int(response.headers['Content-Length'])
