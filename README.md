# Terrain Reader Project

这是一个用于将 SRTM 地形数据（.zip/.hgt）转换为 Shapefile (.shp) 格式的工具。

## 功能特点
- **自动搜索**: 自动递归搜索 `earthdata` 目录下的地形数据瓦片。
- **智能拼接**: 支持跨瓦片（Mosaic）拼接，处理跨越多个地形文件的数据。
- **范围裁剪**: 根据指定的经纬度范围（Bounding Box）进行精确裁剪。
- **降采样**: 支持自定义降采样步长（Step），有效控制输出文件大小。
- **标准格式**: 输出带有 EPSG:4326 坐标系的 Point 类型 Shapefile，包含 `.prj` 投影文件。
- **格式兼容**: 自动处理 `.num` 文件重命名为 `.hgt` 以被 GDAL/Rasterio 识别。

## 环境准备

1. 确保已安装 Python 环境。
2. 安装项目依赖：
```bash
pip install -r requirements.txt
```
*(注：本项目依赖 `numpy<2` 以兼容 geopandas)*

## 数据准备

请将 SRTM 地形数据（通常为 `.zip` 压缩包）放入项目根目录下的 `earthdata` 文件夹中。
- 目录结构示例：
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

## 使用方法

运行 `terrain_converter.py` 脚本，并指定经纬度范围：

```bash
python terrain_converter.py --min_lon <最小经度> --max_lon <最大经度> --min_lat <最小纬度> --max_lat <最大纬度> [--step <降采样步长>]
```

### 参数说明
- `--min_lon`: 最小经度 (例如: 112.0)
- `--max_lon`: 最大经度 (例如: 116.0)
- `--min_lat`: 最小纬度 (例如: 20.0)
- `--max_lat`: 最大纬度 (例如: 24.0)
- `--step`: (可选) 降采样步长，默认为 1。
  - `1`: 保留所有原始数据点（数据量最大）。
  - `10`: 每 10x10 个像素取 1 个点（数据量减少 100 倍，适合大范围预览）。

### 运行示例

以深圳及周边区域（经度 112-116，纬度 20-24）为例：

```bash
python terrain_converter.py --min_lon 112.0 --max_lon 116.0 --min_lat 20.0 --max_lat 24.0
```

如果需要降低数据密度（例如测试时）：

```bash
python terrain_converter.py --min_lon 112.0 --max_lon 116.0 --min_lat 20.0 --max_lat 24.0 --step 10
```

## 输出结果

转换后的文件将保存在 `output` 目录下，文件夹名称根据输入的经纬度范围自动生成。

例如：`output/N20E112_N24E116/terrain.shp`

输出的 Shapefile 包含以下字段：
- `geometry`: 点坐标 (经度, 纬度)
- `elevation`: 海拔高度值
- `city`: 区域标识名称 (例如: "N20E112")

## 常见问题
- **Git 状态**: `earthdata` 和 `output` 目录通常被配置为忽略，不应提交到版本控制中。
- **缺少 .prj**: 脚本会自动指定 `EPSG:4326`，生成 `.prj` 文件以确保坐标系正确。

## 数据精度说明

生成的 Shapefile 地形精度主要取决于两个因素：**源数据分辨率** 和 **降采样参数 (`--step`)**。

1.  **源数据分辨率 (Source Resolution)**
    *   本项目通常使用 **SRTM GL1** 数据（文件名包含 `SRTMGL1`）。
    *   **水平精度**: 1 弧秒（1 arc-second）。
        *   在赤道附近约 **30 米**。
        *   在深圳纬度（约 N22°）附近，东西向网格间距约为 **28 米**，南北向约为 **30 米**。
    *   **垂直精度**: SRTM 数据通常为整数米（1 meter），绝对垂直误差通常在 16 米以内（90% 置信度）。

2.  **输出点密度 (Output Density)**
    *   可以通过运行脚本时的 `--step` 参数控制输出点的密度。
    *   `--step 1` (默认): 完整保留源数据精度（每 ~30 米生成一个点）。
    *   `--step 10`: 将精度降低 10 倍（每 ~300 米生成一个点），显著减小文件体积。
