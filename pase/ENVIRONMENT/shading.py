# -*- coding: utf-8 -*-


import pvlib
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

class Horizon:
    """
    Class managing the far shadings / horizon profile.
    
    It allows to:
    1. Fetch horizon data (e.g. from PVGIS via pvlib)
    2. Store the horizon profile (Azimuth vs Elevation)
    3. Check visibility of points (Sun positions or Sky patches) against this horizon.
    """
    
    def __init__(self, lat, lon):
        """
        Initialize the Horizon object with location coordinates.
        
        Parameters:
            lat (float): Latitude of the location
            lon (float): Longitude of the location
        """
        self.lat = lat
        self.lon = lon
        self.horizon_profile = None
        self.interp_func = None
        
    def get_horizon_pvgis(self, timeout=30):
        """
        Fetch horizon profile from PVGIS using pvlib.
        
        Parameters:
            timeout (int): Timeout for the API request in seconds.
            
        Returns:
            pd.DataFrame: The horizon profile data.
        """
        try:

            data, metadata = pvlib.iotools.get_pvgis_horizon(self.lat, 
                                                             self.lon, 
                                                             timeout=timeout)
            

            self.horizon_profile = pd.DataFrame({
                'azimuth': data.index,
                'elevation': data.values.flatten()
            }).sort_values('azimuth')

            azimuths = self.horizon_profile['azimuth'].values
            elevations = self.horizon_profile['elevation'].values
            
            # Ensure strictly increasing azimuths for interpolation
            if azimuths[-1] < 360:
                 azimuths = np.append(azimuths, 
                                      360)
                 elevations = np.append(elevations, 
                                        elevations[0])
                 
            self.interp_func = interp1d(azimuths, 
                                        elevations, 
                                        kind='linear', 
                                        fill_value="extrapolate")
            
            return self.horizon_profile
            
        except Exception as e:
            print(f"Error fetching PVGIS horizon data: {e}")
            raise

    def get_horizon_mask(self, azimuths, elevations):
        """
        Compute a boolean mask for a set of points (azimuth, elevation).
        Returns True if the point is VISIBLE (above horizon), False otherwise.
        
        Parameters:
            azimuths (np.array): Array of azimuths [degrees] (0=North, 90=East)
            elevations (np.array): Array of elevations [degrees]
            
        Returns:
            np.array: Boolean mask (True=Visible, False=Shaded)
        """
        if self.interp_func is None:
            print("Warning: No horizon profile loaded. Assuming clear horizon.")
            return np.ones_like(azimuths, 
                                dtype=bool)
        
        az_norm = np.mod(azimuths, 360)
        
        horizon_el = self.interp_func(az_norm)
        
        is_visible = elevations > horizon_el
        
        return is_visible

    def is_sun_visible(self, solar_az, solar_el):
        """
        Check if the sun is visible for single or multiple positions.
        Wrapper around get_horizon_mask.
        """
        return self.get_horizon_mask(np.array(solar_az), 
                                     np.array(solar_el))
