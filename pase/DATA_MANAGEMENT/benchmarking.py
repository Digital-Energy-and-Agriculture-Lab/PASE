import csv
from datetime import datetime
import os
import pandas as pd
import subprocess
import yaml

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider

def export_benchmark(df, fname_prefix='diffuse_benchmark_', mode='x', fpath=None):
    if mode == 'x':
        behavior = '(creating new file)'
    elif mode == 'a':
        behavior = '(append to existing file)'
    else :
        raise ValueError('Unexpected mode.')

    PASE_Logger('Saving result ' + behavior, level='INFO')

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
            PASE_Logger(f'Result saved in {fpath}', level='INFO')
            return fpath

        except FileExistsError as e:
            PASE_Logger(str(e) + ' Increment suffix counter.', level='WARNING')

            counter += 1
            if counter > 10:
                raise ValueError('Too many attempts')

def get_git_revision_hash() -> str:
    """
    Get git revision hash (long form)
    source: https://stackoverflow.com/a/21901260
    :return: git rev hash (str)
    """
    try:
        return (subprocess.check_output(['git', 'rev-parse', 'HEAD'])
                .decode('ascii').strip())
    except Exception as e:
        return f"Could not retrieve commit: {e}"


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

def save_simulation_metadata(config, Loc_1, crop_config,
                             output_path=os.path.join("OUTPUTS",
                                                      "simulation_metadata.yaml")):
    # Creating dictionary
    metadata = {}

    # Adding date and hour of simulation
    metadata['date'] = datetime.now().isoformat()

    # Finding Git commit hash
    metadata['git_commit'] = get_git_revision_hash()

    # Adding parameters from YAML and csv files contents
    try:  # TODO extend to other crop models
        metadata['soil_init'] = YAML_Inputs_provider(
            file=os.path.join("CROPS", "GRASSIM", "soil",
                              config['SoilInit'])).inputs
        metadata['crop_init'] = YAML_Inputs_provider(
            file=os.path.join("CROPS", "GRASSIM", "crop",
                              config['CropInit'])).inputs
        metadata['kc_values'] = YAML_Inputs_provider(
            file=os.path.join("CROPS", "GRASSIM", "crop",
                              config['Kc_values'])).inputs
        metadata['pft_composition'] = YAML_Inputs_provider(
            file=os.path.join("CROPS", "GRASSIM",
                              config['PFT_composition'])).inputs
        metadata['pft_values'] = pd.read_csv(
            os.path.join("INPUTS", "CROPS", "GRASSIM",
                         config['PFT_values']), sep=";",
            decimal='.').to_dict(orient='list')
        metadata['management'] = YAML_Inputs_provider(
            file=os.path.join("CROPS", "GRASSIM", "management",
                              config['Management'])).inputs
    except Exception as e:
        metadata['error_loading_yaml_inputs'] = str(e)

    # Adding others useful parameters
    metadata['general_location_config'] = Loc_1
    metadata['crop_config'] = crop_config

    # Saving metadata dictionary into YAML file
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True)

    print(f"Simulation metadata saved to {output_path}")
