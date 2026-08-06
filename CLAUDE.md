# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Preview

This is a static HTML/JS site with no build step. To preview it locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Opening `index.html` directly as a `file://` URL works but Leaflet map tiles will not load, and `site_data.json` will not be fetched — the page falls back to embedded stub data instead.

## Architecture

The site has three source files and two data files:

- **`site_data.json`** — the single source of truth for all site content. All cruise metadata, image references, and external links live here. Editing this file updates the entire site.
- **`data/drake_passage_tracks.json`** — measured ship tracks and depth-coverage statistics extracted from the CODAS databases (see below). Fetched at runtime alongside `site_data.json`; absent or unreachable, the site falls back to the illustrative `cruise.track` arrays.
- **`index.html`** — the public-facing portal. Fetches both data files at runtime and builds all UI (Leaflet maps, coverage charts, image gallery, cruise table) via JavaScript. Contains embedded fallback data (`EMBEDDED_DATA`) for `file://` preview.
- **`admin.html`** — a standalone form tool for composing new cruise records. Its output is JSON to copy-paste into `site_data.json`. It does not write files directly.
- **`images/`** — image files referenced by `site_data.json` (`cruise.images[].filename` paths are relative to this folder). This directory is not committed.

## Measured tracks (`data/drake_passage_tracks.json`)

Produced by **`../../science/technical_sadcp/make_drake_passage_web_tracks.py`**, which is deliberately kept outside this repository: it needs pycurrents/CODAS and the raw loads under `/work/smullersoares_work/data/adcp/`. Regenerate with

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python make_drake_passage_web_tracks.py \
    /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

Per cruise it holds:

- `site_id` — the key that matches `cruise.track_key` in `site_data.json`.
- `segments[]` — arrays of `[lat, lon]` for the ensembles carrying valid (non-masked) `u` and `v`, thinned to ~2 km spacing and split where the track jumps in time (>2 h) or position (>50 km). Databases of the same cruise (nb150 + os38nb) are merged into one track.
- `instruments[]` — one entry per CODAS database, each with a `coverage` block giving, per depth bin, `n_good` / `coverage_pct` (non-masked `u` and `v` over all ensembles), `err_rms_ms` and `pg_mean`, plus `max_depth_50pct` / `max_depth_80pct`.
- Cruise aggregates: `track_length_km`, `duration_days`, `n_drake_crossings`, `bbox`, `n_ens_valid`.

## Data model (`site_data.json`)

The `_README` key at the top of the file documents the schema. Key points:

- `projects[]` — top-level programs (currently `"antarctic"` and `"calcofi"`). Each project has `id`, `color`, `map_center`, `map_zoom`, and a `cruises[]` array.
- `cruise.track` — array of `[latitude, longitude]` pairs (negative = S/W) forming the map polyline.
- `cruise.stations` — array of `{lat, lng, label}` objects for individual markers.
- `cruise.images[].filename` — basename only; file must exist at `images/<filename>`.
- `cruise.status` — one of `"processed"`, `"archived"`, `"in_review"`, `"pending"`.
- `cruise.jasadcp_url` — optional; renders a purple "JASADCP" button in the data table when present.
- `cruise.track_key` — links the cruise to its measured track in `data/drake_passage_tracks.json`. When it resolves, the measured track replaces `cruise.track` on the map and the row becomes clickable.
- `cruise.codas_dbs` — the CODAS database directories the cruise was built from; the table is expected to stay in step with these loads.

## index.html JavaScript structure

Key globals and functions:

- `SITE` — populated after `loadData()` resolves; holds the full parsed `site_data.json`.
- `TRACKS` — measured tracks keyed by `site_id`; `trackFor(cruise)` / `hasTrack(cruise)` resolve a cruise against it.
- `mapsInitialized` — keyed by `project.id`; stores the Leaflet `Map` instance to prevent double-init.
- `mapCruiseLayers` — keyed by `project.id` then `cruise.id`; stores per-cruise `LayerGroup` for the toggle checkboxes.
- `mapCruiseLines` — the visible polylines of each cruise, used by `highlightTrack()` to thicken a track when its table row is hovered (and vice versa).
- `initSite()` — runs once after data loads; builds footer, hero buttons, stats, and project cards.
- `showProject(projId)` — builds the full project page HTML (`buildProjectHTML`) and defers map init by 100 ms to let the DOM paint.
- `initProjectMap(p)` — creates the Leaflet map with ESRI Ocean basemap (no API key required) and an OSM fallback layer; draws one `LayerGroup` per cruise for toggling. Measured tracks are drawn solid, one polyline per segment plus a wide transparent hit line; illustrative `cruise.track` arrays stay dashed.
- `toggleCruiseLayer / setCruisesAll` — toggle cruise track visibility via the chip bar below each map.
- `focusCruise(projId, cruiseId)` — zooms to the cruise bbox and opens the coverage drawer; wired to both the table rows and the map tracks.
- `openCoverage()` / `profileChart()` — the drawer and its two depth profiles (coverage %, error-velocity RMS), drawn as inline SVG with a hover readout (`covHover`) and a "show the numbers" table.

Navigation is section-based (no URL routing): `showSection(id)` shows/hides `<section id="section-{id}">` elements.
