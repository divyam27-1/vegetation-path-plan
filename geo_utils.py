import numpy as np
import rasterio
from pyproj import CRS, Transformer, Geod

_fpath = "Data/NDVI.data.tif"

ndvi, _profile, _transform, _crs = None, None, None, None
with rasterio.open(_fpath) as src:
    ndvi = src.read(1) 

    _profile = src.profile
    _transform = src.transform
    _crs = src.crs
ndvi_m = np.ma.masked_less(ndvi, -1)
NDVI_NAN_MASK = -10000

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

SPRAY_RADIUS = 5    #m
CHUNK_DIM = max(1, round(HEIGHT_PX * SPRAY_RADIUS / HEIGHT_METERS))
SPRAY_RADIUS_PX = CHUNK_DIM
NUM_CHUNKS_V = np.ceil(HEIGHT_METERS / SPRAY_RADIUS)
NUM_CHUNKS_H = np.ceil(WIDTH_METERS / SPRAY_RADIUS)

CHUNK_V_BOUNDS = range(0, HEIGHT_PX, CHUNK_DIM)
CHUNK_H_BOUNDS = range(0, WIDTH_PX, CHUNK_DIM)
CHUNK_BOUNDS = (CHUNK_V_BOUNDS, CHUNK_H_BOUNDS)

CHUNK_LAT_BOUNDARIES = np.linspace(LAT_MIN, LAT_MAX, int(NUM_CHUNKS_V + 1))
CHUNK_LON_BOUNDARIES = np.linspace(LON_MIN, LON_MAX, int(NUM_CHUNKS_H + 1))
CHUNK_DIM_LAT = -(LAT_MAX - LAT_MIN) / NUM_CHUNKS_V  
CHUNK_DIM_LON = (LON_MAX - LON_MIN) / NUM_CHUNKS_H

def get_chunk(chunk_y, chunk_x, img=ndvi, _chunk_bounds=CHUNK_BOUNDS, _chunk_dim=CHUNK_DIM):

    chunk_bounds_y, chunk_bounds_x = _chunk_bounds[0], _chunk_bounds[1]
    start_y, start_x = chunk_bounds_y[chunk_y], chunk_bounds_x[chunk_x]
    end_y, end_x = start_y + _chunk_dim, start_x + _chunk_dim

    img_slice = img[start_y:end_y, start_x:end_x]

    return img_slice

def pixel_coord_to_chunk_coord(y, x, _chunk_dim=CHUNK_DIM):
    chunk_x = x // _chunk_dim
    chunk_y = y // _chunk_dim
    return chunk_y, chunk_x

def chunk_coord_to_geo_coord(y, x,
                             y_offset=0,
                             x_offset=0,
                            _chunk_latlon_boundaries=(CHUNK_LAT_BOUNDARIES, CHUNK_LON_BOUNDARIES)):
    return _chunk_latlon_boundaries[0][y]-y_offset, _chunk_latlon_boundaries[1][x]+x_offset

def pixel_coord_to_geo_coord(y, x, _chunk_dim=CHUNK_DIM, y_offset=0, x_offset=0, _chunk_latlon_boundaries=(CHUNK_LAT_BOUNDARIES, CHUNK_LON_BOUNDARIES)):
    cy, cx = pixel_coord_to_chunk_coord(y, x, _chunk_dim=_chunk_dim)
    return chunk_coord_to_geo_coord(cy, cx, y_offset=y_offset, x_offset=x_offset, _chunk_latlon_boundaries=_chunk_latlon_boundaries)

def chunk_coord_to_pixel_coord(cy, cx, _chunk_dim=CHUNK_DIM, get_center=False):
    center = np.array([cy * _chunk_dim, cx * _chunk_dim])
    if get_center:
        return center + _chunk_dim//2
    else:
        return center


#ALL
__all__ = [
    "ndvi", "_xmin", "_ymin", "_xmax", "_ymax", "HEIGHT_PX", "WIDTH_PX",
    "UTM_CRS", "WGS84_CRS", "LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX",
    "WIDTH_METERS", "HEIGHT_METERS", "SPRAY_RADIUS", "CHUNK_DIM", "NUM_CHUNKS_V",
    "NUM_CHUNKS_H", "CHUNK_V_BOUNDS", "CHUNK_H_BOUNDS", "CHUNK_BOUNDS", 
    "CHUNK_LAT_BOUNDARIES", "CHUNK_LON_BOUNDARIES", "CHUNK_DIM_LAT", "CHUNK_DIM_LON",
    "NDVI_NAN_MASK",

    "get_chunk", "pixel_coord_to_chunk_coord", "chunk_coord_to_geo_coord",
    "pixel_coord_to_geo_coord", "chunk_coord_to_pixel_coord"
]