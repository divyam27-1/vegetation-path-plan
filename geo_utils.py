import numpy as np
import rasterio
from pyproj import CRS, Transformer, Geod
import yaml
from pymavlink import mavutil
import os

_cfgpath = "config.yaml"
with open(_cfgpath) as f:
    _cfg = yaml.safe_load(f)

CROP = _cfg['crop']
_fpath = f"Data/NDVI_{CROP}.data.tif"
ndvi, _profile, _transform, _crs = None, None, None, None
with rasterio.open(_fpath) as src:
    ndvi = src.read(1) 

    _profile = src.profile
    _transform = src.transform
    _crs = src.crs
ndvi_m = np.ma.masked_less(ndvi, -1)
NDVI_NAN_MASK = _cfg["ndvi_nan_mask"]

os.makedirs(os.path.dirname(f"Data/{CROP}/"), exist_ok=True)
os.makedirs(os.path.dirname(f"Flight Paths/{CROP}/"), exist_ok=True)
os.makedirs(os.path.dirname(f"Spray Patterns/{CROP}/"), exist_ok=True)

_xmin, _ymin = _transform * (0, 0)
_xmax, _ymax = _transform * (src.width, src.height)
HEIGHT_PX, WIDTH_PX = ndvi.shape[0], ndvi.shape[1]

UTM_CRS = CRS.from_epsg(32644)
WGS84_CRS = CRS.from_epsg(4326)
_transformer = Transformer.from_crs(UTM_CRS, WGS84_CRS, always_xy=True)
LON_MIN, LAT_MIN = _transformer.transform(_xmin, _ymin)
LON_MAX, LAT_MAX = _transformer.transform(_xmax, _ymax)

_geod = Geod(ellps="WGS84")
_, _, WIDTH_METERS = _geod.inv(LON_MIN, LAT_MIN, LON_MAX, LAT_MIN)
_, _, HEIGHT_METERS = _geod.inv(LON_MIN, LAT_MIN, LON_MIN, LAT_MAX)

CHUNK_DIM = _cfg["chunk_size_m"]
SPRAY_SIZE = _cfg["spray_diameter_m"]
CHUNK_DIM_PX = max(1, round(HEIGHT_PX * CHUNK_DIM / HEIGHT_METERS))
SPRAY_SIZE_PX = max(1, round(HEIGHT_PX * SPRAY_SIZE / HEIGHT_METERS))
NUM_CHUNKS_V = np.ceil(HEIGHT_METERS / CHUNK_DIM)
NUM_CHUNKS_H = np.ceil(WIDTH_METERS / CHUNK_DIM)

CHUNK_V_BOUNDS = range(0, HEIGHT_PX, CHUNK_DIM_PX)
CHUNK_H_BOUNDS = range(0, WIDTH_PX, CHUNK_DIM_PX)
CHUNK_BOUNDS = (CHUNK_V_BOUNDS, CHUNK_H_BOUNDS)

CHUNK_LAT_BOUNDARIES = np.linspace(LAT_MIN, LAT_MAX, int(NUM_CHUNKS_V + 1))
CHUNK_LON_BOUNDARIES = np.linspace(LON_MIN, LON_MAX, int(NUM_CHUNKS_H + 1))
CHUNK_DIM_LAT = -(LAT_MAX - LAT_MIN) / NUM_CHUNKS_V  
CHUNK_DIM_LON = (LON_MAX - LON_MIN) / NUM_CHUNKS_H

def get_chunk(chunk_y, chunk_x, img=ndvi, _chunk_bounds=CHUNK_BOUNDS, _chunk_dim=CHUNK_DIM_PX):

    chunk_bounds_y, chunk_bounds_x = _chunk_bounds[0], _chunk_bounds[1]
    start_y, start_x = chunk_bounds_y[chunk_y], chunk_bounds_x[chunk_x]
    end_y, end_x = start_y + _chunk_dim, start_x + _chunk_dim

    img_slice = img[start_y:end_y, start_x:end_x]

    return img_slice

def pixel_coord_to_chunk_coord(y, x, _chunk_dim=CHUNK_DIM_PX):
    chunk_x = x // _chunk_dim
    chunk_y = y // _chunk_dim
    return chunk_y, chunk_x

def chunk_coord_to_geo_coord(y, x,
                             y_offset=0,
                             x_offset=0,
                            _chunk_latlon_boundaries=(CHUNK_LAT_BOUNDARIES, CHUNK_LON_BOUNDARIES)):
    return _chunk_latlon_boundaries[0][y]-y_offset, _chunk_latlon_boundaries[1][x]+x_offset

def pixel_coord_to_geo_coord(y, x, img=ndvi, _lat_bounds=(LAT_MIN, LAT_MAX), _lon_bounds=(LON_MIN,LON_MAX)):
    _img_height, _img_width = img.shape[0], img.shape[1]
    _lat_min, _lat_max = _lat_bounds
    _lon_min, _lon_max = _lon_bounds
    lat = _lat_min + (y / (_img_height - 1)) * (_lat_max - _lat_min)
    lon = _lon_min + (x / (_img_width - 1)) * (_lon_max - _lon_min)

    return lat, lon

def chunk_coord_to_pixel_coord(cy, cx, _chunk_dim=CHUNK_DIM_PX, get_center=False):
    center = np.array([cy * _chunk_dim, cx * _chunk_dim])
    if get_center:
        return center + _chunk_dim//2
    else:
        return center

def generate_mission_waypoints(mission, outpath, _takeoff=(LAT_MAX, LON_MIN)):
    header = "QGC WPL 110"
    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
    alt = _cfg["mission"]["flight_altitude"]

    def write_args(file, args):
        l = len(args)
        for i, arg in enumerate(args):
            if type(arg)==float:
                file.write(f"{arg:.8f}")
            else:
                file.write(f"{arg}")
            if i == l-1:
                file.write("\n")
            else:
                file.write("\t")

    with open(outpath, "w") as f:
        f.write(f"{header}\n")
        #home position
        write_args(f, [
            0,
            1,
            frame,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0,
            0,
            0,
            0,
            _takeoff[0],
            _takeoff[1],
            alt,
            1])
        
        #takeoff command
        write_args(f, [
            1,                                      #index
            0,                                      #is current wp
            frame,                                  #coord frame
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,    #command
            0,                                      #param
            0,                                      #param
            0,                                      #param
            0,                                      #param
            _takeoff[0],                            #lat
            _takeoff[1],                            #lon
            alt,                                    #alt
            1                                       #autocontinue
        ])
        
        #rest of waypoints
        for i, wp in enumerate(mission):
            write_args(f, [
                i+2,
                0,
                frame,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                0,
                0,
                0,
                wp[0],
                wp[1],
                alt,
                1
            ])


#ALL
__all__ = [
    "ndvi", "ndvi_m", "_xmin", "_ymin", "_xmax", "_ymax", "HEIGHT_PX", "WIDTH_PX",
    "UTM_CRS", "WGS84_CRS", "LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX",
    "WIDTH_METERS", "HEIGHT_METERS", "CHUNK_DIM", "CHUNK_DIM_PX", "NUM_CHUNKS_V",
    "NUM_CHUNKS_H", "CHUNK_V_BOUNDS", "CHUNK_H_BOUNDS", "CHUNK_BOUNDS", 
    "CHUNK_LAT_BOUNDARIES", "CHUNK_LON_BOUNDARIES", "CHUNK_DIM_LAT", "CHUNK_DIM_LON",
    "NDVI_NAN_MASK",

    "get_chunk", "pixel_coord_to_chunk_coord", "chunk_coord_to_geo_coord",
    "pixel_coord_to_geo_coord", "chunk_coord_to_pixel_coord"
]