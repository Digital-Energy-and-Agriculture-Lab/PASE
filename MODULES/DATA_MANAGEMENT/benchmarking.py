import csv
from datetime import datetime
import os
import pandas as pd

def export_benchmark(df, fname_prefix='diffuse_benchmark_', mode='x', fname=None):
    if mode == 'x':
        behavior = '(creating new file)'
    elif mode == 'a':
        behavior = '(append to existing file)'
    else :
        raise ValueError('Unexpected mode.')

    print('Saving result ' + behavior)

    exact_fname_provided = True if fname is not None else False

    date_str = datetime.today().strftime('%Y-%m-%d')

    written = False
    counter = 0
    while written == False:
        suffix = f'_{counter:02}'
        if exact_fname_provided == False:
            fname = fname_prefix + date_str + suffix + '.csv'

        try:
            if mode == 'a':
                # append blank line before appending the new content
                with open(fname, 'a',
                          newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow('')

            df.to_csv(fname, mode=mode)
            written = True
            print(f'Result saved in {fname}')
            return fname

        except FileExistsError as e:
            print(str(e) + ' Increment suffix counter.')

            counter += 1
            if counter > 10:
                raise ValueError('Too many attempts')
