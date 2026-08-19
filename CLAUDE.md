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

The site has three source files and three data files:

- **`site_data.json`** — the single source of truth for all site content. All cruise metadata, image references, and external links live here. Editing this file updates the entire site.
- **`data/drake_passage_tracks.json`** — measured ship tracks and depth-coverage statistics extracted from the CODAS databases (see below). Fetched at runtime alongside `site_data.json`; absent or unreachable, the site falls back to the illustrative `cruise.track` arrays.
- **`data/antarctic_webpy_gallery.json`** — generated manifest of standard pycurrents/CODAS figures. The Antarctic gallery fetches it at runtime; a missing manifest leaves the gallery in its unavailable state without affecting the map or coverage drawer.
- **`index.html`** — the public-facing portal. Fetches the data files at runtime and builds all UI (Leaflet maps, coverage charts, image gallery, cruise table) via JavaScript. Contains embedded fallback data (`EMBEDDED_DATA`) for `file://` preview.
- **`admin.html`** — a standalone form tool for composing new cruise records. Its output is JSON to copy-paste into `site_data.json`. It does not write files directly.
- **`images/`** — manually curated image files referenced by `site_data.json` (`cruise.images[].filename` paths are relative to this folder) are ignored. The reproducible generated figures under `images/antarctic-webpy/` are committed static assets.

## Measured tracks (`data/drake_passage_tracks.json`)

Produced by **`../../science/technical_sadcp/make_drake_passage_web_tracks.py`**, which is deliberately kept outside this repository: it needs pycurrents/CODAS and the raw loads under `/work/smullersoares_work/data/adcp/`. The file covers the series in two halves, built from two different repositories and merged into one file.

**2019 onwards** — the in-house UHDAS loads, found by crawling a directory:

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python make_drake_passage_web_tracks.py \
    /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

**1999–2018** — the science-ready sets submitted to the Joint Archive for Shipboard ADCP. These sit in `/work/smullersoares_work/data/adcp/jas_repo_complete/`, one numbered SAC directory per submitted database among ~2600 unrelated neighbours, so the cruises are selected first and the list handed to the builder. `select_drake_passage_jas_dbs.py` reads the repository's `total.inv` / `new.inv` inventories and keeps the databases attributed to the Chereskin group inside the Drake Passage box (south of 50°S, 80°W–35°W); `--merge-into` folds the result into the existing file, leaving the 2019-onwards cruises alone:

```bash
cd ../../science/technical_sadcp
python select_drake_passage_jas_dbs.py \
    --meta-out drake_passage_jas_cruises.json > jas_drake_dbs.txt
conda run -n py_ddt python make_drake_passage_web_tracks.py \
    --db-list jas_drake_dbs.txt \
    --merge-into ../../software/adcp_ucsd/data/drake_passage_tracks.json \
    --source-label /work/smullersoares_work/data/adcp/jas_repo_complete \
    /work/smullersoares_work/data/adcp/jas_repo_complete/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

This selection yields 211 cruises (206 ARSV Laurence M. Gould, 5 RVIB Nathaniel B. Palmer cDrake cruises) over 372 CODAS databases, LMG9908 through LMG1811.

**NCEI accessions** — cruises whose only copy is the archival package NCEI hands back. These are unpacked under the 2019-onwards root, one 7-digit accession directory each, and the CODAS databases sit several levels down (`<accession>/<ver>/data/0-data/<date>_<CRUISE>/<sac>/adcpdb/<db>`). pysadcp reads their TOML sidecars directly — `read_metadata_wrap` picks up cruise, sonar, vessel and JAS id from `<sac>_meta.toml`, so no `.bft` or `dbinfo.txt` is needed — but this requires the pysadcp branch `feature/ncei-ingestion` (module `pysadcp.ncei`). Accession 0314050 holds LMG2305, LMG2309, LMG2310, LMG2312, LMG2401 and LMG2404 (May 2023 – April 2024), one nb150 database each:

```bash
cd ../../science/technical_sadcp
find /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/0314050 \
    -name '*dir.blk' | sed 's/dir\.blk$//' | sort > ncei_dbs.txt
conda run -n py_ddt python make_drake_passage_web_tracks.py \
    --db-list ncei_dbs.txt \
    --merge-into ../../software/adcp_ucsd/data/drake_passage_tracks.json \
    --source-label /work/smullersoares_work/data/adcp/drake_passage_2019_onwards \
    /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

`dbs_dir` has to be the repository root rather than the accession, because `instruments[].db_dir` is recorded relative to it and `make_drake_passage_web_gallery.py` resolves a database as `<root>/<db_dir>/adcpdb/<db>`. For the UHDAS and JAS layouts that relative path is a bare directory name, so those entries are unaffected. Two of them (LMG1104, LMG1805) name both their databases after the same sonar in the `.bft`; the builder relabels the deeper one `os38nb` from its depth range and keeps the original under `instruments[].sonar_reported`.

Per cruise it holds:

- `site_id` — the key that matches `cruise.track_key` in `site_data.json`.
- `segments[]` — arrays of `[lat, lon]` for the ensembles carrying valid (non-masked) `u` and `v`, thinned to ~2 km spacing and split where the track jumps in time (>2 h) or position (>50 km). Databases of the same cruise (nb150 + os38nb) are merged into one track.
- `instruments[]` — one entry per CODAS database, each with a `coverage` block giving, per depth bin, `n_good` / `coverage_pct` (non-masked `u` and `v` over all ensembles), `err_rms_ms` and `pg_mean`, plus `max_depth_50pct` / `max_depth_80pct`.
- Cruise aggregates: `track_length_km`, `duration_days`, `n_drake_crossings`, `bbox`, `n_ens_valid`.

## Antarctic CODAS plot gallery (`data/antarctic_webpy_gallery.json`)

The gallery is built offline by
**`../../science/technical_sadcp/make_drake_passage_web_gallery.py`** with the
`py_ddt` Conda environment. It uses `site_data.json` and the measured-track
file as the portal identity contract, so every gallery record is keyed to a
map-selectable `cruise.id` / `track_key` pair. It never writes inside either
raw CODAS source tree.

For 2019-onward UHDAS loads, complete existing `webpy/` output is copied. For
1999–2018 JAS/NCEI loads, the builder runs the established
`select_drake_passage_jas_dbs.py` selector and renders the standard `quick_web.py
--auto` figures into a scratch directory. Only the supported top-level PNGs
and matching thumbnails are published; generated HTML, CODAS contents, and
the scratch output remain private. `images/` is otherwise ignored by git, but
`images/antarctic-webpy/` is committed — it is reproducible output, and the
published site has to serve it.

Run a no-write single-cruise check first:

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python make_drake_passage_web_gallery.py \
    --cruise LMG2304 --dry-run
```

Publish an already-rendered recent cruise without allowing a render:

```bash
conda run -n py_ddt python make_drake_passage_web_gallery.py \
    --cruise LMG2304 --existing-only
```

### Size budget and the two passes

The complete per-section set for all 422 databases comes to roughly 1.8 GB —
past the 1 GB ceiling GitHub Pages puts on a published site — so the portal is
built in two passes. The 2019-onwards loads (30 cruises, 50 databases) get the
full figure set; the 1999–2018 archive gets `--overviews-only`, which publishes
just the cruise overview and renders it with `quick_web.py --simple_web`
(seconds per database instead of a minute, since the section plots are never
drawn). That lands near 300 MB with every cruise still carrying figures.

```bash
cd ../../science/technical_sadcp
# 1999-2018 archive: overviews only
conda run -n py_ddt python make_drake_passage_web_gallery.py \
    $(python3 -c "import json;d=json.load(open('../../software/adcp_ucsd/site_data.json'));\
p=next(x for x in d['projects'] if x['id']=='antarctic');\
print(' '.join('--cruise '+c['id'] for c in p['cruises'] \
  if any('jas_repo_complete' in s for s in c.get('codas_dbs',[]))))") \
    --overviews-only
# 2019 onwards: the full set
conda run -n py_ddt python make_drake_passage_web_gallery.py \
    $(python3 -c "import json;d=json.load(open('../../software/adcp_ucsd/site_data.json'));\
p=next(x for x in d['projects'] if x['id']=='antarctic');\
print(' '.join('--cruise '+c['id'] for c in p['cruises'] \
  if not any('jas_repo_complete' in s for s in c.get('codas_dbs',[]))))")
```

Both passes must pass `--cruise` filters: the manifest only preserves records
for cruises outside the filter, so an unfiltered run would drop the other pass.

For a full refresh in one scope, omit `--cruise`; use `--strict` when every
selected source must succeed, and `--keep-scratch` only while diagnosing a
pycurrents failure.
Validate the resulting manifest with `python3 -m json.tool
data/antarctic_webpy_gallery.json >/dev/null`, then preview over HTTP. In the
portal, an Antarctic cruise's `Plots` button selects the corresponding gallery;
the next `Plots` selection replaces it. Map clicks remain dedicated to the
coverage drawer.

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
- `cruise.sac_id` / `cruise.sac_ids` — the JASADCP (NODC/UH SAC) cruise id of the primary database, and one `{sac_id, sonar}` entry per submitted database. `jasadcp_url` is `https://uhslc.soest.hawaii.edu/sadcp/DATABASE/<sac_id>.html`. Cruises processed in house and not yet submitted (2019 onwards) have none of these.
- `cruise.ncei_accession` — the bare NCEI accession number behind `ncei_url` (`https://www.ncei.noaa.gov/archive/accession/<n>`). JASADCP submissions up to ~2018 were archived in batches, so many cruises share one accession; from 2019 each Drake Passage season has its own. `../../science/technical_sadcp/resolve_jasadcp_ncei_accessions.py` rebuilds the SAC-id-to-accession mapping by walking the NCEI archive directories (NCEI's own mapping page went with the GOCD when it was decommissioned in April 2025).
- `data/antarctic_webpy_gallery.json` is intentionally separate from `cruise.images[]`; it carries generated CODAS plot paths, thumbnails, checksums, plot-family metadata, and per-cruise availability.

## index.html JavaScript structure

Key globals and functions:

- `SITE` — populated after `loadData()` resolves; holds the full parsed `site_data.json`.
- `TRACKS` — measured tracks keyed by `site_id`; `trackFor(cruise)` / `hasTrack(cruise)` resolve a cruise against it.
- `WEBPY_GALLERY` — Antarctic pycurrents figure manifest keyed by cruise id. `selectWebpyGallery()` is called only by an Antarctic measured track hit-line and replaces the one visible gallery selection.
- `mapsInitialized` — keyed by `project.id`; stores the Leaflet `Map` instance to prevent double-init.
- `mapCruiseLayers` — keyed by `project.id` then `cruise.id`; stores per-cruise `LayerGroup` for the toggle checkboxes.
- `mapCruiseLines` — the visible polylines of each cruise, used by `highlightTrack()` to thicken a track when its table row is hovered (and vice versa).
- `initSite()` — runs once after data loads; builds footer, hero buttons, stats, and project cards.
- `showProject(projId)` — builds the full project page HTML (`buildProjectHTML`) and defers map init by 100 ms to let the DOM paint.
- `initProjectMap(p)` — creates the Leaflet map with ESRI Ocean basemap (no API key required) and an OSM fallback layer; draws one `LayerGroup` per cruise for toggling. Measured tracks are drawn solid, one polyline per segment plus a wide transparent hit line; illustrative `cruise.track` arrays stay dashed.
- `toggleCruiseLayer / setCruisesAll / setCruisesYear` — toggle cruise track visibility via the chip bar below each map. With the full series on the map the chips run to a few hundred, so they sit in their own scroll area and `setCruisesYear` (one button per season, from `cruiseYear`) narrows the map to a single year.
- `sacLink(sac)` — renders a SAC id as a link to its JASADCP page; used in the coverage drawer's per-sonar cards. Ids that are not five digits (`unsubmitted`) get no link.
- `focusCruise(projId, cruiseId)` — zooms to the cruise bbox and opens the coverage drawer; wired to both the table rows and the map tracks.
- `openCoverage()` / `profileChart()` — the drawer and its two depth profiles (coverage %, error-velocity RMS), drawn as inline SVG with a hover readout (`covHover`) and a "show the numbers" table.

Navigation is section-based (no URL routing): `showSection(id)` shows/hides `<section id="section-{id}">` elements.
