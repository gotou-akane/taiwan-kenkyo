"""由內政部國土測繪中心「鄉(鎮、市、區)界線」SHP 產生 data/counties.js。

資料：內政部國土測繪中心，鄉(鎮、市、區)界線（TWD97 經緯度，114 年 3 月 18 日版）
      https://data.gov.tw/dataset/7441  （政府資料開放授權條款－第 1 版）
用法：python build_data.py <TOWN_MOI_1140318.shp>  [輸出路徑，預設 data/counties.js]
需求：pip install shapely pyshp
"""
import json
import sys
from collections import defaultdict

import shapefile
from shapely import make_valid
from shapely.geometry import LineString, shape
from shapely.ops import linemerge, unary_union

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'data/counties.js'

EPS = 0.0012    # 判定「與鄰縣共用邊界」的容差（約 130 m）
SIMP = 0.0004   # 邊界簡化（約 44 m）
# 遊戲涵蓋範圍：台灣本島、澎湖、金門、馬祖（排除東沙、南沙、釣魚臺等遠方島嶼）
LON0, LON1, LAT0, LAT1 = 117.8, 122.5, 21.5, 26.6
MAIN = (119.95, 21.8, 122.15, 25.45)   # 台灣本島範圍，用於挑選本島部分


def in_box(g, box):
    c = g.centroid
    return box[0] <= c.x <= box[2] and box[1] <= c.y <= box[3]


def parts(g):
    return list(g.geoms) if g.geom_type in ('MultiPolygon', 'GeometryCollection') else [g]


def lines_of(g):
    if g.is_empty:
        return []
    if g.geom_type == 'LineString':
        return [g]
    if g.geom_type in ('MultiLineString', 'GeometryCollection'):
        out = []
        for x in g.geoms:
            out += lines_of(x)
        return out
    return []


def enc(g, tol=SIMP):
    res = []
    for l in lines_of(linemerge(g) if g.geom_type == 'MultiLineString' else g):
        l = l.simplify(tol)
        if l.length > 0.003:
            res.append([[round(x, 4), round(y, 4)] for x, y in l.coords])
    return res


# 1. 鄉鎮區 → 依縣市合併
r = shapefile.Reader(SRC, encoding='utf-8')
by = defaultdict(list)
for rec, shp in zip(r.records(), r.shapes()):
    by[rec['COUNTYNAME']].append(make_valid(shape(shp.__geo_interface__)))
polys = {n: unary_union(v) for n, v in by.items()}
assert len(polys) == 22, len(polys)

# 2. 每個縣市的正解邊界
out = {}
for n, p in polys.items():
    ps = [g for g in parts(p) if g.geom_type == 'Polygon']
    b = p.boundary
    others = unary_union([q for m, q in polys.items() if m != n])
    shared = b.intersection(others.buffer(EPS))
    sl = [l for l in lines_of(shared) if l.length > 0.01]
    island = (not sl) or sum(l.length for l in sl) < 0.05
    if island:  # 沒有陸地邊界的離島：只取最大島的海岸線
        pg = max(ps, key=lambda g: g.area)
        border = LineString(pg.exterior.coords)
        bounds = pg.bounds
    else:
        border = unary_union(sl)
        big = max(g.area for g in ps)
        main = [g for g in ps if in_box(g, MAIN) and g.area >= 0.05 * big] or ps  # 略過基隆嶼等小島
        bounds = unary_union(main).bounds
    out[n] = {'island': island, 'lines': enc(border), 'bbox': [round(v, 4) for v in bounds]}
    print(n, island, len(out[n]['lines']), sum(len(l) for l in out[n]['lines']))

# 3. 海岸線（僅遊戲範圍內）
land = unary_union(list(polys.values()))
coast = []
for pg in parts(land):
    if pg.geom_type != 'Polygon' or pg.area < 1e-5:
        continue
    c = pg.centroid
    if not (LON0 <= c.x <= LON1 and LAT0 <= c.y <= LAT1):
        continue
    coast.append([[round(x, 4), round(y, 4)] for x, y in pg.exterior.simplify(0.0006).coords])

js = 'window.TW_DATA=' + json.dumps({'counties': out, 'coast': coast}, ensure_ascii=False, separators=(',', ':')) + ';'
open(OUT, 'w').write(js)
print(len(js), 'bytes;', len(coast), 'coast rings')
