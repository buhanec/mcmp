from __future__ import print_function
from mcmp import get_mod
import pandas as pd
# noinspection PyPackageRequirements
import yaml
import sys
import requests
import requests_cache


if __name__ == '__main__':
    download = sys.argv[1] == '--download' or sys.argv[1] == '-d'

    if sys.argv[-1].startswith('http'):
        with requests_cache.disabled():
            response = requests.get(sys.argv[-1])
        if response.ok:
            mod_list = yaml.load(response.text)
        else:
            raise Exception(response.status_code)
    else:
        with open(sys.argv[-1], 'r') as f:
            mod_list = yaml.load(f)

    mods = {mod: get_mod(mod, download=download) for mod in mod_list}
    df = pd.DataFrame(mods).T
    df.accepted = df.accepted.astype(bool)

    pd.set_option('display.max_rows', len(mods))
    pd.set_option('display.width', 240)
    print('Accepted:')
    print(df[df.accepted][['name', 'channel', 'filename', 'mod_ver']])
    print()
    print('Not Accepted:')
    print(df[~df.accepted][['name', 'channel', 'filename', 'mod_ver']])
