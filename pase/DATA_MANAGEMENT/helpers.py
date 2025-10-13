import numpy as np
import pandas as pd


def aggregate_lat_lon(latitude, longitude):
    if isinstance(latitude, float) and isinstance(longitude, float):
        return f'{latitude}; {longitude}'

    if isinstance(latitude, pd.Series) and isinstance(longitude, pd.Series):
        return latitude.astype(str) + "; " + longitude.astype(str)


def unpack_latlon(latlon):
    if isinstance(latlon, pd.Series):
        lat_lon = latlon.str.split("; ", expand=True).astype(float)

        return lat_lon[0].values, lat_lon[1].values

    if isinstance(latlon, np.ndarray):
        latlon_series = pd.Series(latlon)
        lat_lon = latlon_series.str.split("; ", expand=True).astype(float)

        return lat_lon[0].values, lat_lon[1].values

def parse_date_range(df):
    dates = pd.to_datetime(df['DAY'], format="%Y%m%d")
    return pd.date_range(start=dates.min(), end=dates.max(), freq="D")