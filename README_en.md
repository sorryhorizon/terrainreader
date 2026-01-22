# Terrain Reader Project

This tool converts SRTM terrain data (.zip/.hgt) into Shapefile (.shp) format.

## Features
- **Automatic Search**: Recursively searches for terrain data tiles in the `earthdata` directory.
- **Smart Mosaicking**: Supports cross-tile (Mosaic) stitching to handle data spanning multiple terrain files.
- **Range Clipping**: Precisely clips data based on a specified latitude/longitude bounding box.
- **Downsampling**: Supports a custom downsampling step (`Step`) to effectively control output file size.
- **Standard Format**: Outputs Point type Shapefiles with EPSG:4326 coordinate system, including the `.prj` projection file.
- **Format Compatibility**: Automatically renames `.num` files to `.hgt` for recognition by GDAL/Rasterio.

## Prerequisites

1. Ensure Python is installed.
2. Install project dependencies:
```bash
pip install -r requirements.txt
```
*(Note: This project requires `numpy<2` for compatibility with geopandas)*

## Data Preparation

Please place SRTM terrain data (usually `.zip` archives) into the `earthdata` folder in the project root directory.
- Directory structure example:
  ```
  terrainreader/
  ├── earthdata/
  │   ├── SRTM_Tile_1.zip
  │   └── subfolder/
  │       └── SRTM_Tile_2.zip
  ├── output/
  ├── terrain_converter.py
  └── requirements.txt
  ```

## Usage

Run the `terrain_converter.py` script and specify the latitude/longitude range:

```bash
python terrain_converter.py --min_lon <min_longitude> --max_lon <max_longitude> --min_lat <min_latitude> --max_lat <max_latitude> [--step <downsampling_step>]
```

### Parameters
- `--min_lon`: Minimum Longitude (e.g., 112.0)
- `--max_lon`: Maximum Longitude (e.g., 116.0)
- `--min_lat`: Minimum Latitude (e.g., 20.0)
- `--max_lat`: Maximum Latitude (e.g., 24.0)
- `--step`: (Optional) Downsampling step, default is 1.
  - `1`: Retain all original data points (maximum data volume).
  - `10`: Take 1 point every 10x10 pixels (reduces data volume by 100x, suitable for large-area previews).

### Example Run

For Shenzhen and surrounding areas (Longitude 112-116, Latitude 20-24):

```bash
python terrain_converter.py --min_lon 112.0 --max_lon 116.0 --min_lat 20.0 --max_lat 24.0
```

To reduce data density (e.g., for testing):

```bash
python terrain_converter.py --min_lon 112.0 --max_lon 116.0 --min_lat 20.0 --max_lat 24.0 --step 10
```

## Output Results

The converted files will be saved in the `output` directory, with folder names automatically generated based on the input latitude/longitude range.

Example: `output/N20E112_N24E116/terrain.shp`

The output Shapefile contains the following fields:
- `geometry`: Point coordinates (Longitude, Latitude)
- `elevation`: Elevation value
- `city`: Area identifier name (e.g., "N20E112")

## FAQ
- **Git Status**: `earthdata` and `output` directories are usually configured to be ignored and should not be committed to version control.
- **Missing .prj**: The script automatically specifies `EPSG:4326` and generates a `.prj` file to ensure the correct coordinate system.

## Data Precision

The precision of the generated terrain Shapefile depends primarily on two factors: **Source Data Resolution** and **Downsampling Parameter (`--step`)**.

1.  **Source Data Resolution**
    *   This project typically uses **SRTM GL1** data (filenames containing `SRTMGL1`).
    *   **Horizontal Accuracy**: 1 arc-second.
        *   Approximately **30 meters** at the equator.
        *   Near Shenzhen latitude (approx. N22°), the east-west grid spacing is about **28 meters**, and north-south is about **30 meters**.
    *   **Vertical Accuracy**: SRTM data is usually in integer meters. The absolute vertical error is typically within 16 meters (90% confidence).

2.  **Output Point Density**
    *   You can control the density of output points via the `--step` parameter when running the script.
    *   `--step 1` (Default): Fully retains source data precision (one point every ~30 meters).
    *   `--step 10`: Reduces precision by 10x (one point every ~300 meters), significantly reducing file size.
