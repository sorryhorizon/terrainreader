# Terrain Reader Project

这是一个用于将 SRTM 地形数据（.hgt/.tif）转换为 Shapefile (.shp) 格式的工具。本项目包含完整的流程：数据下载指南、地形转换、以及数据验证与可视化。

## 功能特点

- **自动搜索**: 自动递归搜索 `earthdata` 目录下的地形数据瓦片。
- **智能筛选**: 优先匹配包含海拔数据的 `.hgt.zip` 文件，自动忽略无用的元数据文件（如 `.num`）。
- **智能拼接**: 支持跨瓦片（Mosaic）拼接，处理跨越多个地形文件的数据。
- **性能优化**:
  - **向量化计算**: 使用 `geopandas.points_from_xy` 替代循环，生成速度提升 10 倍以上。
  - **I/O 加速**: 集成 `pyogrio` 引擎，实现 Shapefile 的极速写入。
  - **并行解压**: 采用多进程（Multiprocessing）并行解压瓦片数据，大幅缩短准备时间。
  - **解压缓存**: 自动检测临时文件，跳过重复解压步骤。
- **进度可视化**: 集成 `tqdm` 实时进度条，支持步骤显示和预计剩余时间。
- **跨平台支持**: 完美支持 Windows 和 Linux 环境（路径自动适配，依赖包跨平台）。
- **范围裁剪**: 根据指定的经纬度范围（Bounding Box）进行精确裁剪。
- **降采样**: 支持自定义降采样步长（Step），有效控制输出文件大小。
- **标准格式**: 输出带有 EPSG:4326 坐标系的 Point 类型 Shapefile，包含 `.prj` 投影文件。
- **数据验证**: 提供 `verify_terrain.py` 脚本，可生成地形热力图并统计海拔极值，快速验证数据质量。

## 环境准备

1. 确保已安装 Python 环境。
2. 安装项目依赖：
```bash
pip install -r requirements.txt
```
*(注：本项目依赖 `numpy<2` 以兼容 geopandas)*

## 项目目录结构

```
terrainreader/
├── earthdata/          # 存放下载的 SRTM 地形数据 (.zip)
│   ├── N30E120.SRTMGL1.hgt.zip
│   └── ...
├── output/             # 存放生成的 Shapefile 和预览图
│   └── N30E120_N32E123/
│       ├── terrain.shp
│       ├── terrain_preview.png
│       └── ...
├── terrain_converter.py # 核心转换脚本
├── verify_terrain.py    # 验证与可视化脚本
├── requirements.txt     # 项目依赖
└── README.md            # 项目说明文档
```

## 数据获取 (Earthdata 指南)

本项目推荐使用 NASA Earthdata 提供的 SRTM GL1 (30米精度) 数据。

1.  访问 [NASA Earthdata Search](https://search.earthdata.nasa.gov/search)。
2.  搜索关键词 **"SRTMGL1"** (SRTM GL1 Global 1 arc second)。
3.  **筛选范围 (Filter)**:
    *   点击左上角的矩形工具，在地图上框选你需要的区域（例如上海或青藏高原）。
    *   或者直接输入坐标范围。
4.  **下载数据**:
    *   点击 "Download All"。
    *   选择 "Direct Download" (直接下载文件)。
    *   **重要**: 确保下载的文件列表中包含 `.hgt.zip` 文件。千万不要只下载 `.num` (Source Number) 文件，那是数据源编号，不包含海拔信息。
5.  将下载的 `.zip` 文件放入项目的 `earthdata` 文件夹中（支持子文件夹）。

## 使用方法

### 1. 地形转换 (Convert)

运行 `terrain_converter.py` 脚本，并指定经纬度范围：

```bash
python terrain_converter.py --min_lon <最小经度> --max_lon <最大经度> --min_lat <最小纬度> --max_lat <最大纬度> [--step <降采样步长>]
```

**参数说明**:
- `--min_lon` / `--max_lon`: 经度范围 (例如: 120.0 到 123.0)
- `--min_lat` / `--max_lat`: 纬度范围 (例如: 30.0 到 32.0)
- `--file`: (可选) 指定单个地形文件路径 (例如: `dem.tif`)。如果指定此参数，将直接读取该文件并跳过自动搜索。
- `--step`: (可选) 降采样步长，默认为 1。
  - `1`: 保留所有原始数据点 (约30米精度)，文件最大。
  - `5`: 每5个点取1个 (约150米精度)，推荐用于城市级范围。
  - `20`: 每20个点取1个 (约600米精度)，推荐用于省/大洲级范围。

**运行示例 (自动搜索)**:
```bash
python -u terrain_converter.py --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32 --step 5
```

**运行示例 (指定本地文件)**:
```bash
python -u terrain_converter.py --file dem.tif --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32 --step 5
```
*(提示：使用 `-u` 参数可以禁用输出缓冲，确保进度条实时显示)*

### 2. 数据验证与可视化 (Verify)

运行 `verify_terrain.py` 脚本来检查生成的 Shapefile 是否正确，并生成预览图。

**自动验证**: (使用与转换相同的坐标参数)
```bash
python verify_terrain.py --min_lon 120 --max_lon 123 --min_lat 30 --max_lat 32
```

**手动指定文件**:
```bash
python verify_terrain.py --file output/N30E120_N32E123/terrain.shp
```

**输出**:
- 终端会显示海拔统计信息（最低、最高、平均海拔）。
- 在 Shapefile 同级目录下生成 `terrain_preview.png` 地形热力图。

## 输出结果

转换后的文件将保存在 `output` 目录下，文件夹名称根据输入的经纬度范围自动生成。

例如：`output/N30E120_N32E123/terrain.shp`

输出的 Shapefile 包含以下字段：
- `geometry`: 点坐标 (经度, 纬度)
- `elevation`: 海拔高度值 (米)
- `city`: 区域标识名称

## 常见问题

1.  **海拔数据显示 0-200 但地形不对？**
    *   原因：可能下载到了 `.num` (Source) 数据而非 `.hgt` (Elevation) 数据。
    *   解决：请重新下载 SRTMGL1 数据，确保 zip 包内含 `.hgt` 文件。本项目最新脚本会自动检测并警告此问题。

2.  **生成文件过大 (超过 2GB)？**
    *   原因：Shapefile 格式有 2GB 大小限制。
    *   解决：增大 `--step` 参数（例如设为 5 或 10）来降低数据密度。

3.  **缺少 .prj 文件？**
    *   解决：最新脚本已修复此问题，会自动生成包含 EPSG:4326 (WGS84) 信息的 `.prj` 文件。
