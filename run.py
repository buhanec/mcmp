from mcmp import get_mod
import pandas as pd
import yaml

MODS = 'mods2.yaml'

if __name__ == '__main__':
    with open(MODS, 'r') as f:
        mod_list = yaml.load(f)

    mods = {mod: get_mod(mod) for mod in mod_list}
    pd.set_option('display.max_rows', len(mods))
    pd.set_option('display.width', 240)
    df = pd.DataFrame(mods).T
    print(df)
