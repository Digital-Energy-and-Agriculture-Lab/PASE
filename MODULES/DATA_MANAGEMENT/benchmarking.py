import csv
from datetime import datetime
import os
import pandas as pd
import subprocess

def export_benchmark(df, fname_prefix='diffuse_benchmark_', mode='x', fpath=None):
    if mode == 'x':
        behavior = '(creating new file)'
    elif mode == 'a':
        behavior = '(append to existing file)'
    else :
        raise ValueError('Unexpected mode.')

    print('Saving result ' + behavior)

    exact_fpath_provided = True if fpath is not None else False

    date_str = datetime.today().strftime('%Y-%m-%d')

    written = False
    counter = 0
    while written == False:
        suffix = f'_{counter:02}'
        if exact_fpath_provided == False:
            fname = fname_prefix + date_str + suffix + '.csv'
            fpath = os.path.join('OUTPUTS', fname)

        try:

            if mode == 'a':
                # append blank line before appending the new content
                with open(fpath, 'a',
                          newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow('')


            df.to_csv(fpath, mode=mode, float_format="%.3e", sep=';')
            written = True
            print(f'Result saved in {fpath}')
            return fpath

        except FileExistsError as e:
            print(str(e) + ' Increment suffix counter.')

            counter += 1
            if counter > 10:
                raise ValueError('Too many attempts')

def get_git_revision_hash() -> str:
    """
    Get git revision hash (long form)
    source: https://stackoverflow.com/a/21901260
    :return: git rev hash (str)
    """
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()


def get_git_revision_short_hash() -> str:
    """
    Get git revision hash (short form)
    source: https://stackoverflow.com/a/21901260
    :return: git rev hash (str)
    """
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()

def sign_commit_hash(fpath):
    commit_hash = get_git_revision_hash()
    date_str = datetime.today().strftime('%Y-%m-%d')
    signature = (f'This benchmarking was generated on {date_str} with code '
                 f'version {commit_hash}')

    with open(fpath, 'a', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow('')
        writer.writerow([signature])
