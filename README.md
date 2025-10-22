# Vegetation Path Plan

## Requirements:
- In the root directory, make a folder 'Data'
- Install the NDVI.data.tiff file from the following link: https://iittpacin-my.sharepoint.com/:i:/g/personal/sarvendranath_iittp_ac_in/ESl1XeO8DdtIss9tTqWQccwBBmK9HZNbNdyJNGqpgxHe0g?e=4pyrle
- Run the python notebooks in the given order

## Contents:
- `ndvi_tiff.ipynb`: Generating JSON list of infected chunks from TIFF image
- `infected_kml.ipynb`: Generate KML from JSON list of infected chunks
- `flight_path.ipynb`: Generate different NPY flight paths for use for spray pattern analysis and export to .waypoints or .plan file
- `spray_pattern.ipynb`: Analyse spray patterns of given flight paths using Point-Spraying Method
- `geo_utils.py`: Utils library for chunkwise geographic computations