# 縣界王 台灣版

限時在地圖上描出指定縣市的邊界，依一致率計分。靈感來自 KSKだぜGAMES「県境王」。

- 縣市界：內政部國土測繪中心「鄉(鎮、市、區)界線」（TWD97 經緯度，114 年 3 月 18 日版，[政府資料開放授權條款－第 1 版](https://data.gov.tw/license)），由 `build_data.py` 依縣市合併並簡化
- 地形：AWS Open Data Terrain Tiles，高程來源為 SRTM、GMTED2010（美國地質調查局 USGS 提供）與 ETOPO1（NOAA NCEI 提供），皆為公有領域資料；山影在瀏覽器端計算。地圖函式庫：Leaflet（BSD-2-Clause）
- 重新產生資料：`python build_data.py <TOWN_MOI_*.shp>`（資料集：https://data.gov.tw/dataset/7441）
