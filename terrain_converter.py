import os
import glob
import argparse
import zipfile
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile
from shapely.geometry import box
import geopandas as gpd
import numpy as np
import math
import sys
import shutil
import time
import concurrent.futures
from tqdm import tqdm

def extract_tile_task(args):
    """
    Task function for multiprocessing extraction.
    args: (zip_path, target_file, temp_dir)
    Returns: extracted_path
    """
    zip_path, target_file, temp_dir = args
    expected_path = os.path.join(temp_dir, target_file)
    
    if os.path.exists(expected_path):
        return expected_path
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extract(target_file, temp_dir)
        return expected_path
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return None

def get_tile_name(lat, lon):
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f"{ns}{abs(int(math.floor(lat))):02d}{ew}{abs(int(math.floor(lon))):03d}"

def find_tile_zip(tile_name, search_dir):
    # Search for *tile_name*.zip recursively
    pattern = os.path.join(search_dir, "**", f"*{tile_name}*.zip")
    files = glob.glob(pattern, recursive=True)
    # Filter out Mac OS metadata files (._*)
    files = [f for f in files if not os.path.basename(f).startswith('._')]
    
    if not files:
        return None

    # Prioritize .hgt.zip files (elevation data) over others
    hgt_files = [f for f in files if '.hgt.zip' in f.lower()]
    if hgt_files:
        return hgt_files[0]
        
    return files[0]

def format_coord_val(val, is_lat=True):
    """Format coordinate value to string, preserving decimals if present."""
    direction = ''
    if is_lat:
        direction = 'N' if val >= 0 else 'S'
    else:
        direction = 'E' if val >= 0 else 'W'
    
    abs_val = abs(val)
    if abs_val.is_integer():
        return f"{direction}{int(abs_val)}"
    else:
        return f"{direction}{abs_val:.2f}"

def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Convert SRTM terrain data to Shapefile.")
    parser.add_argument("--min_lon", type=float, required=True)
    parser.add_argument("--max_lon", type=float, required=True)
    parser.add_argument("--min_lat", type=float, required=True)
    parser.add_argument("--max_lat", type=float, required=True)
    parser.add_argument("--step", type=int, default=1, help="Downsampling step (default 1)")
    
    args = parser.parse_args()
    
    earthdata_dir = os.path.join(os.getcwd(), "earthdata")
    output_base_dir = os.path.join(os.getcwd(), "output")
    temp_dir = os.path.join(output_base_dir, "temp_tiles")
    
    # Identify tiles
    start_lat = math.floor(args.min_lat)
    end_lat = math.floor(args.max_lat)
    
    lat_range = range(start_lat, end_lat + 1)
    lon_range = range(math.floor(args.min_lon), math.floor(args.max_lon) + 1)
    
    src_files_to_mosaic = []
    extraction_tasks = []
    
    print(f"Searching for tiles in {earthdata_dir}...")
    
    # 1. Search tiles first (Lightweight)
    for lat in lat_range:
        for lon in lon_range:
            tile_name = get_tile_name(lat, lon)
            zip_path = find_tile_zip(tile_name, earthdata_dir)
            if zip_path:
                try:
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        all_files = z.namelist()
                        # Find .hgt or .tif
                        candidates = [f for f in all_files if f.endswith(('.hgt', '.tif'))]
                        candidates = [f for f in candidates if not os.path.basename(f).startswith('._')]
                        
                        num_files = [f for f in all_files if f.endswith('.num')]
                        if not candidates and num_files:
                            print(f"  ERROR: Found metadata file (.num) but NO elevation data in {zip_path}.")
                            continue

                        if candidates:
                            target_file = candidates[0]
                            # Prepare task for parallel extraction
                            extraction_tasks.append((zip_path, target_file, temp_dir))
                        else:
                            print(f"  No valid data files found in zip: {zip_path}")
                except Exception as e:
                    print(f"Error reading zip {zip_path}: {e}")
            else:
                print(f"Warning: Tile {tile_name} not found.")

    if not extraction_tasks:
        print("No tiles found. Exiting.")
        return

    # Define steps for progress bar
    steps = [
        "Extracting Files",
        "Reading Files",
        "Merging",
        "Clipping",
        "Converting to Points",
        "Generating Geometry",
        "Saving Shapefile"
    ]
    
    # Configure tqdm to output to sys.stdout and force flush
    pbar = tqdm(total=len(steps), desc="Processing", unit="step", 
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                file=sys.stdout)
    
    try:
        # Step 1: Parallel Extraction
        pbar.set_description("Extracting Files")
        os.makedirs(temp_dir, exist_ok=True)
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # Map tasks to executor
            results = list(executor.map(extract_tile_task, extraction_tasks))
            
        # Filter valid results
        src_files_to_mosaic = [r for r in results if r is not None]
        
        if not src_files_to_mosaic:
            print("Extraction failed. No files to process.")
            pbar.close()
            return
            
        pbar.update(1)

        print(f"\nMerging {len(src_files_to_mosaic)} tiles...")
        
        # Step 2: Reading Files
        pbar.set_description("Reading Files")
        src_datasets = [rasterio.open(f) for f in src_files_to_mosaic]
        pbar.update(1)
        
        # Step 2: Merging
        pbar.set_description("Merging")
        mosaic, out_trans = merge(src_datasets)
        
        # Close datasets
        for ds in src_datasets:
            ds.close()
            
        # Create metadata for the mosaic
        out_meta = src_datasets[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans
        })
        pbar.update(1)
        
        # Step 3: Clipping
        pbar.set_description("Clipping")
        # Now Clip to the exact bounding box
        bbox = box(args.min_lon, args.min_lat, args.max_lon, args.max_lat)
        
        with MemoryFile() as memfile:
            with memfile.open(**out_meta) as dataset:
                dataset.write(mosaic)
                
                # Now mask
                out_image, out_transform = mask(dataset, [bbox], crop=True)
                out_meta = dataset.meta.copy()

        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        pbar.update(1)
        
        # Step 4: Converting to Points
        pbar.set_description("Converting to Points")
        # out_image is (count, height, width)
        data = out_image[0] # Band 1
        
        # Downsample if needed
        if args.step > 1:
            tqdm.write(f"Downsampling with step {args.step}...")
            data = data[::args.step, ::args.step]
            rows, cols = np.indices(data.shape)
            rows = rows * args.step
            cols = cols * args.step
        else:
            rows, cols = np.indices(data.shape)
            
        rows = rows.flatten()
        cols = cols.flatten()
        elevations_flat = data.flatten()
        
        # Filter nodata
        valid_mask = elevations_flat != -32768
        
        rows = rows[valid_mask]
        cols = cols[valid_mask]
        elevs = elevations_flat[valid_mask]
        
        if len(elevs) == 0:
            tqdm.write("No valid elevation points found in the area.")
            sys.stdout.flush()
            pbar.close()
            return

        tqdm.write(f"Generating {len(elevs)} points...")
        if len(elevs) > 1000000:
            tqdm.write("Warning: Generating > 1 million points. This may be slow.")
        sys.stdout.flush()
        pbar.update(1)
        
        # Step 5: Generating Geometry
        pbar.set_description("Generating Geometry")
        # Vectorized transform
        xs, ys = rasterio.transform.xy(out_transform, rows, cols, offset='center')
        
        # Creating GeoDataFrame using vectorized operation (much faster)
        geometry = gpd.points_from_xy(xs, ys)
        
        # Name format
        name_str = f"{format_coord_val(args.min_lat, True)}{format_coord_val(args.min_lon, False)}"
        
        gdf = gpd.GeoDataFrame({
            'elevation': elevs,
            'city': name_str
        }, geometry=geometry, crs="EPSG:4326")
        pbar.update(1)
        
        # Step 6: Saving
        pbar.set_description("Saving Shapefile")
        min_str = f"{format_coord_val(args.min_lat, True)}{format_coord_val(args.min_lon, False)}"
        max_str = f"{format_coord_val(args.max_lat, True)}{format_coord_val(args.max_lon, False)}"
        folder_name = f"{min_str}_{max_str}"
        
        out_dir = os.path.join(output_base_dir, folder_name)
        os.makedirs(out_dir, exist_ok=True)
        
        out_shp = os.path.join(out_dir, "terrain.shp")
        # Use pyogrio engine for faster IO
        gdf.to_file(out_shp, engine="pyogrio")
        pbar.update(1)
        pbar.close()
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"Done. Total time: {duration:.2f} seconds.")

        # Cleanup temp
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
