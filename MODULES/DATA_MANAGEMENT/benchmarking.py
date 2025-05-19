from datetime import datetime
import os
import pandas as pd

def export_benchmark(df, fname_prefix='diffuse_benchmark_', mode='x'):
    print('Saving result ...')

    date_str = datetime.today().strftime('%Y-%m-%d')

    written = False
    counter = 0
    while written == False:
        suffix = f'_{counter:02}'
        fname = fname_prefix + date_str + suffix + '.csv'
        if os.path.isfile(fname):
            print(f'File {fname} already exists')
            counter += 1
            if counter > 10:
                raise ValueError('Too many attempts')
                break
        else:
            df.to_csv(fname, mode=mode)
            written = True
            print(f'Result saved in {fname}')