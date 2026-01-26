import geopandas as gpd
import matplotlib.pyplot as plt
import argparse
import os
import sys

def verify_and_plot(shp_path):
    print(f"Loading Shapefile: {shp_path}...")
    
    if not os.path.exists(shp_path):
        print(f"Error: File not found at {shp_path}")
        return False

    try:
        gdf = gpd.read_file(shp_path)
    except Exception as e:
        print(f"Error reading Shapefile: {e}")
        return False

    if gdf.empty:
        print("Error: GeoDataFrame is empty.")
        return False

    # 1. Basic Metadata Verification
    print("\n=== Verification Report ===")
    print(f"Feature Count: {len(gdf)}")
    print(f"CRS (Coordinate System): {gdf.crs}")
    
    bounds = gdf.total_bounds
    print(f"Bounds (MinX, MinY, MaxX, MaxY): {bounds}")
    
    if 'elevation' not in gdf.columns:
        print("Error: 'elevation' column missing.")
        return False
        
    elev_min = gdf['elevation'].min()
    elev_max = gdf['elevation'].max()
    elev_mean = gdf['elevation'].mean()
    
    print(f"Elevation Min: {elev_min:.2f} m")
    print(f"Elevation Max: {elev_max:.2f} m")
    print(f"Elevation Mean: {elev_mean:.2f} m")
    print("===========================\n")

    # 2. Visualization
    print("Generating visualization...")
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Plot using 'terrain' colormap
        gdf.plot(column='elevation', 
                 ax=ax, 
                 legend=True, 
                 cmap='terrain', 
                 markersize=1,  # Small markers for density
                 legend_kwds={'label': "Elevation (m)"})
        
        ax.set_title(f"Terrain Elevation Map\nSource: {os.path.basename(os.path.dirname(shp_path))}", fontsize=15)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        
        # Save plot
        output_dir = os.path.dirname(shp_path)
        output_png = os.path.join(output_dir, "terrain_preview.png")
        plt.savefig(output_png, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Visualization saved to: {output_png}")
        return True
        
    except Exception as e:
        print(f"Error during visualization: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Verify and visualize generated terrain Shapefile.")
    
    # Option 1: Direct file path
    parser.add_argument("--file", type=str, help="Path to the .shp file")
    
    # Option 2: Lat/Lon range (to find the folder automatically)
    parser.add_argument("--min_lon", type=float)
    parser.add_argument("--max_lon", type=float)
    parser.add_argument("--min_lat", type=float)
    parser.add_argument("--max_lat", type=float)
    
    args = parser.parse_args()
    
    target_shp = None
    
    if args.file:
        target_shp = args.file
    elif args.min_lon is not None and args.max_lon is not None and args.min_lat is not None and args.max_lat is not None:
        # Construct path based on convention
        folder_name = f"N{int(args.min_lat)}E{int(args.min_lon)}_N{int(args.max_lat)}E{int(args.max_lon)}"
        target_shp = os.path.join("output", folder_name, "terrain.shp")
    else:
        print("Usage Error: Please provide either --file OR (--min_lon, --max_lon, --min_lat, --max_lat)")
        sys.exit(1)
        
    verify_and_plot(target_shp)

if __name__ == "__main__":
    main()
