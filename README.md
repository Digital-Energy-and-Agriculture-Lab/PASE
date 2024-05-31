# Framework_Agrivoltaics

The framework PASE aims to create an agrivoltaic system and to compute its photovoltaic and agricultural productions. It uses the HDKR model to compute the global tilted irradiance reaching the panels and a ray casting algorithm to compute the amount of light reaching the crop below. Crop models are then used to simulate the growth of the crop and the yield.

# Installation

There is a environment.yml file that should be used to download all the packages required to use the framework.

## Windows User
The python code requires the module PyEmbree for the ray casting. Currently (01/23), the package can NOT be easily installed via conda on windows device (it as to be compiled from the source). The solution is to install the package via pip.

# Getting started

## Input files

As a user, you should only modify the input files in the INPUTS folder. There is one file for general parameters and location parameters and one ore more file for the PV configurations (there should be one PV file per configuration). For each parmater you have information about the type of value you should enter, the limit, the unit and a definition to help you understand what is the paremeter. You should only change the value in front of the line "Value :".


# License

This software is available mainly under the MIT license, copyright University of Liège, Digital Energy and Agriculture Lab (DEAL). For a complete list of package dependencies with copyright and license information, please look at the file LICENSE-3RD-PARTY
