# Terrain Reader Project

This tool converts SRTM terrain data (.hgt/.tif) into Shapefile (.shp) format. This project includes a complete workflow: data download guide, terrain conversion, and data verification & visualization.

## Features

- **Automatic Search**: Recursively searches for terrain data tiles in the `earthdata` directory.
- **Smart Filtering**: Prioritizes `.hgt.zip` files (elevation data) and automatically ignores useless metadata files (like `.num`).
- **Smart Mosaicking**: Supports cross-tile (Mosaic) stitching to handle data spanning multiple terrain files.
- **Performance Optimization**:
  - **Vectorized Calculation**: Uses `geopandas.points_from_xy` for >10x speedup in point generation.
  - **Fast I/O**: Integrated `pyogrio` engine for high-speed Shapefile writing.
  - **Parallel Decompression**: Uses Multiprocessing for parallel tile extraction.
  - **Decompression Cache**: Automatically detects temp files to skip redundant unzipping.
- **Progress Visualization**: Integrated `tqdm` for real-time progress bars with ETA.
- **Cross-Platform**: Fully compatible with Windows and Linux (path handling, dependencies).
- **Range Clipping**: Precisely clips data based on a specified latitude/longitude bounding box.
- **Downsampling**: Supports a custom downsampling step (`Step`) to effectively control output file size.
- **Standard Format**: Outputs Point type Shapefiles with EPSG:4326 coordinate system, including the `.prj` projection file.
- **Data Verification**: Provides `verify_terrain.py` script to generate terrain heatmaps and statistical extremes for quick data quality verification.

## Prerequisites

1. Ensure Python is installed.
2. Install project dependencies:
```bash
pip install -r requirements.txt
```
*(Note: This project requires `numpy<2` for compatibility with geopandas)*

## Project Directory Structure

```
terrainreader/
├── earthdata/          # Stores downloaded SRTM terrain data (.zip)
│   ├── N30E120.SRTMGL1.hgt.zip
│   └── ...
├── output/             # Stores generated Shapefiles and preview images
│   └── N30E120_N32E123/
│       ├── terrain.shp
│       ├── terrain_preview.png
│       └── ...
├── terrain_converter.py # Core conversion script
├── verify_terrain.py    # Verification and visualization script
├── requirements.txt     # Project dependencies
└── README.md            # Project documentation
```

## Data Acquisition (Earthdata Guide)

This project recommends using SRTM GL1 (30-meter resolution) data provided by NASA Earthdata.

1.  Visit [NASA Earthdata Search](https://search.earthdata.nasa.gov/search).
2.  Search for **"SRTMGL1"** (SRTM GL1 Global 1 arc second).
3.  **Filter Range**:
    *   Click the rectangle tool on the top left to select your area of interest on the map (e.g., Shanghai or Tibetan Plateau).
    *   Or directly input coordinate ranges.
4.  **Download Data**:
    *   Click "Download All".
    *   Select "Direct Download".
    *   **Important**: Ensure the downloaded file list contains `.hgt.zip` files. Do NOT download only `.num` (Source Number) files, as they are data source IDs and contain no elevation info.
5.  Place the downloaded `.zip` files into the `earthdata` folder in the project root (subfolders are supported).

## Usage

### 1. Terrain Conversion (Convert)

Run the `terrain_converter.py` script and specify the latitude/longitude range:

```bash
python terrain_converter.py --min_lon <min_lon> --max_lon <max_lon> --min_lat <min_lat> --max_lat <max_lat> [--step <step>]
```

**Parameters**:
- `--min_lon` / `--max_lon`: Longitude range (e.g., 120.0 to 123.0)
- `--min_lat` / `--max_lat`: Latitude range (e.g., 30.0 to 32.0)
- `--file`: (Optional) Path to a single terrain file (e.g., `dem.tif`). If specified, automatic search in `earthdata` is skipped.
- `--step`: (Optional) Downsampling step, default is 1.
  - `1`: Retain all original data points (approx. 30m precision), largest file size.
  - `5`: Take 1 point every 5 points (approx. 150m precision), recommended for city-level scale.
  - `20`: Take 1 point every 20 points (approx. 600m precision), recommended for province/continent scale.

**Example Run (Auto Search)**:
```bash
python -u terrain_converter.py --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32 --step 5
```

**Example Run (Local File)**:
```bash
python -u terrain_converter.py --file dem.tif --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32 --step 5
```
*(Tip: Use `-u` flag to disable output buffering for real-time progress bars)*

### 2. Data Verification & Visualization (Verify)

Run the `verify_terrain.py` script to check if the generated Shapefile is correct and generate a preview image.

**Auto Verification**: (Use the same coordinate parameters as conversion)
```bash
python verify_terrain.py --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32
```

**Manual File Selection**:
```bash
python verify_terrain.py --file output/N30E120_N32E123/terrain.shp
```

**Output**:
- Terminal displays elevation statistics (min, max, mean elevation).
- Generates `terrain_preview.png` terrain heatmap in the same directory as the Shapefile.

## Output Results

Converted files are saved in the `output` directory, with folder names automatically generated based on the input latitude/longitude range.

Example: `output/N30E120_N32E123/terrain.shp`

The output Shapefile contains the following fields:
- `geometry`: Point coordinates (Longitude, Latitude)
- `elevation`: Elevation value (meters)
- `city`: Area identifier name

## FAQ

1.  **Elevation shows 0-200 but terrain is wrong?**
    *   Reason: You may have downloaded `.num` (Source) data instead of `.hgt` (Elevation) data.
    *   Solution: Please re-download SRTMGL1 data, ensuring the zip package contains `.hgt` files. The latest script automatically detects and warns about this issue.

2.  **Generated file is too large (> 2GB)?**
    *   Reason: Shapefile format has a 2GB size limit.
    *   Solution: Increase the `--step` parameter (e.g., set to 5 or 10) to reduce data density.

3.  **Missing .prj file?**
    *   Solution: The latest script fixes this issue and automatically generates a `.prj` file containing EPSG:4326 (WGS84) information.
