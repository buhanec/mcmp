from mcmp import get_mod
import pandas as pd
import yaml
import sys
import requests
import requests_cache


if __name__ == '__main__':
    if sys.argv[1].startswith('http'):
        with requests_cache.disabled():
            response = requests.get(sys.argv[1])
        if response.ok:
            mod_list = yaml.load(response.text)
        else:
            raise Exception(response.status_code)
    else:
        with open(sys.argv[1], 'r') as f:
            mod_list = yaml.load(f)

    mods = {mod: get_mod(mod) for mod in mod_list}
    pd.set_option('display.max_rows', len(mods))
    pd.set_option('display.width', 240)
    df = pd.DataFrame(mods).T
    df.accepted = df.accepted.astype(bool)

    print('Accepted:')
    print(df[df.accepted][['name', 'channel', 'filename', 'mod_ver']])
    print()
    print('Not Accepted:')
    print(df[~df.accepted][['name', 'channel', 'filename', 'mod_ver']])
