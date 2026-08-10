"""
Tayari's multi-hazard engine.

Given any latitude and longitude on Earth, this package answers two questions
for each of nine hazards: could this happen here at all, and is it happening
now. It does so from live public feeds only — USGS for seismicity, the
Smithsonian Global Volcanism Program for eruptions, Copernicus GloFAS for river
discharge, and Open-Meteo for weather, climatology and terrain — with no API
keys and no bundled geodata beyond a 131 KB volcano catalog.

Layout:
    registry.py         hazard metadata: names, colours, onset, provenance
    geo.py              distance maths and the DEM terrain probe
    feeds.py            every outbound HTTP call, with tiered caching
    volcano_catalog.py  the Smithsonian catalog, queried by proximity
    context.py          one concurrent gather of all feeds for a location
    scoring.py          the shared 0-1 scale and risk bands
    assessors/          one module per hazard, pure functions over the context
    engine.py           screening, orchestration and the assembled profile
"""
