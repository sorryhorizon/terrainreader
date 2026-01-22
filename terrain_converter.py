import os
import glob
import argparse
import zipfile
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile
from shapely.geometry import box, Point
import geopandas as gpd
import numpy as np
import math
import sys
import shutil

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
    if files:
        return files[0]
    return None

def main():
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
    
    print(f"Searching for tiles in {earthdata_dir}...")
    for lat in lat_range:
        for lon in lon_range:
            tile_name = get_tile_name(lat, lon)
            zip_path = find_tile_zip(tile_name, earthdata_dir)
            if zip_path:
                print(f"Found tile: {tile_name} -> {zip_path}")
                try:
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        all_files = z.namelist()
                        # Find .hgt, .tif, or .num
                        candidates = [f for f in all_files if f.endswith(('.hgt', '.tif', '.num'))]
                        candidates = [f for f in candidates if not os.path.basename(f).startswith('._')]
                        
                        if candidates:
                            target_file = candidates[0]
                            # Extract to temp dir
                            os.makedirs(temp_dir, exist_ok=True)
                            
                            # Check if already extracted
                            # We need to handle the fact that extract might recreate dirs
                            # z.extract extracts full path.
                            extracted_path = z.extract(target_file, temp_dir)
                            
                            # If .num, rename to .hgt so rasterio recognizes it as SRTM
                            if extracted_path.endswith('.num'):
                                new_path = extracted_path[:-4] + ".hgt"
                                # Rename
                                if os.path.exists(new_path):
                                    os.remove(new_path)
                                os.rename(extracted_path, new_path)
                                extracted_path = new_path
                            
                            src_files_to_mosaic.append(extracted_path)
                            print(f"  Extracted to: {extracted_path}")
                        else:
                            print(f"  No valid data files found in zip. Contents: {all_files[:5]}...")
                except Exception as e:
                    print(f"Error reading zip {zip_path}: {e}")
            else:
                print(f"Warning: Tile {tile_name} not found.")

    if not src_files_to_mosaic:
        print("No tiles found. Exiting.")
        return

    print(f"Merging {len(src_files_to_mosaic)} tiles...")
    
    try:
        # Open all files
        src_datasets = [rasterio.open(f) for f in src_files_to_mosaic]
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
        
        # Now Clip to the exact bounding box
        bbox = box(args.min_lon, args.min_lat, args.max_lon, args.max_lat)
        
        print("Clipping to bounding box...")
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
        
        # Now convert to Points
        print("Converting to Points...")
        # out_image is (count, height, width)
        data = out_image[0] # Band 1
        
        # Downsample if needed
        if args.step > 1:
            print(f"Downsampling with step {args.step}...")
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
            print("No valid elevation points found in the area.")
            return

        print(f"Generating {len(elevs)} points...")
        if len(elevs) > 1000000:
            print("Warning: Generating > 1 million points. This may be slow.")

        # Vectorized transform
        xs, ys = rasterio.transform.xy(out_transform, rows, cols, offset='center')
        
        # Creating GeoDataFrame
        geometry = [Point(x, y) for x, y in zip(xs, ys)]
        
        # Name format
        name_str = f"N{int(args.min_lat)}E{int(args.min_lon)}"
        
        gdf = gpd.GeoDataFrame({
            'elevation': elevs,
            'city': name_str
        }, geometry=geometry, crs="EPSG:4326")
        
        # Save
        folder_name = f"N{int(args.min_lat)}E{int(args.min_lon)}_N{int(args.max_lat)}E{int(args.max_lon)}"
        out_dir = os.path.join(output_base_dir, folder_name)
        os.makedirs(out_dir, exist_ok=True)
        
        out_shp = os.path.join(out_dir, "terrain.shp")
        print(f"Saving to {out_shp}...")
        gdf.to_file(out_shp)
        print("Done.")

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
