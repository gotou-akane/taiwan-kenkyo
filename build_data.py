import json
from shapely.geometry import Polygon, shape, mapping, MultiLineString, LineString
from shapely.ops import unary_union, linemerge

d = json.load(open('/private/tmp/claude-501/-Users-chunyen-Projects-taiwan-legal-mcp/1e8b7552-a3e8-4772-be30-ed6ddb3432d5/scratchpad/c.json'))
polys = {}
for f in d['features']:
    n = f['properties']['county'].replace('臺', '臺')
    n = '桃園市' if n == '桃園縣' else n
    g = f['geometry']
    parts = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    ps = []
    for part in parts:
        rings = [r for r in part if len(r) >= 4]
        if rings: ps.append(Polygon(rings[0], rings[1:]).buffer(0))
    polys[n] = unary_union(ps)

EPS = 0.0012  # ~130m
SIMP = 0.0004

def lines_of(g):
    if g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    if g.geom_type in ('MultiLineString', 'GeometryCollection'):
        out = []
        for x in g.geoms: out += lines_of(x)
        return out
    return []

def enc(g, tol=SIMP):
    res = []
    for l in lines_of(linemerge(g) if g.geom_type == 'MultiLineString' else g):
        l = l.simplify(tol)
        if l.length > 0.003:
            res.append([[round(x, 4), round(y, 4)] for x, y in l.coords])
    return res

out = {}
land = unary_union(list(polys.values()))
for n, p in polys.items():
    b = p.boundary
    others = unary_union([q for m, q in polys.items() if m != n])
    shared = b.intersection(others.buffer(EPS))
    sl = [l for l in lines_of(shared) if l.length > 0.01]
    island = (not sl) or sum(l.length for l in sl) < 0.05
    border = b if island else unary_union(sl)
    if island:  # 離島只取最大島的海岸線（與原版相同）
        pg = max(p.geoms if p.geom_type == 'MultiPolygon' else [p], key=lambda g: g.area)
        border = LineString(pg.exterior.coords)
        p = pg  # bbox 也只取最大島
    out[n] = {'island': island, 'lines': enc(border), 'bbox': [round(v, 4) for v in p.bounds]}
    print(n, island, len(out[n]['lines']), sum(len(l) for l in out[n]['lines']))

coast = []
for pg in (land.geoms if land.geom_type == 'MultiPolygon' else [land]):
    if pg.area < 1e-5: continue
    coast.append([[round(x, 4), round(y, 4)] for x, y in pg.exterior.simplify(0.0006).coords])
js = 'window.TW_DATA=' + json.dumps({'counties': out, 'coast': coast}, ensure_ascii=False, separators=(',', ':')) + ';'
open('/Users/chunyen/Projects/taiwan-kenkyo/data/counties.js', 'w').write(js)
print(len(js))
