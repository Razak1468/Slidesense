# SlideSpect soil-moisture data source

## Primary source

NASA Soil Moisture Active Passive (SMAP), L4 analyzed surface soil moisture.

NASA Worldview lists the layer as **Surface Soil Moisture 9 km (L4, 12z
Instantaneous)** and reports the units as m³/m³.

NASA GIBS publishes the `SMAP_L4_Analyzed_Surface_Soil_Moisture` layer and
provides map tiles by date.

## Why this source

- Satellite/model-assisted Earth observation.
- Global coverage, including Northeast India.
- Approximately 9 km spatial resolution for this L4 layer.
- Date-addressable map tiles through GIBS.
- Suitable for the first working SlideSpect visualization.

## Important interpretation

A 9 km product is an area/grid observation, not an independent measurement
at every road, village or building. Soil moisture should later be combined
with rainfall, terrain, geology/soil, land cover and other features before
being used as a landslide-risk model input.

## Official references

- NASA Worldview: https://worldview.earthdata.nasa.gov/
- NASA GIBS layer metadata: https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/
- NASA GIBS soil-moisture colormap: https://gibs.earthdata.nasa.gov/colormaps/v1.3/output/SMAP_Soil_Moisture.html
- NASA Earthdata CMR SMAP L4 collection: https://cmr.earthdata.nasa.gov/
