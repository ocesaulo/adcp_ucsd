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

The site has three source files and six data files:

- **`site_data.json`** — the single source of truth for all site content. All cruise metadata, image references, and external links live here. Editing this file updates the entire site.
- **`data/drake_passage_tracks.json`**, **`data/calcofi_tracks.json`** — measured ship tracks and depth-coverage statistics extracted from the CODAS databases (see below), one file per programme. Both are fetched at runtime alongside `site_data.json` and share one `TRACKS` index, since cruise ids are unique across the projects; absent or unreachable, the site falls back to the illustrative `cruise.track` arrays.
- **`data/antarctic_webpy_gallery.json`**, **`data/calcofi_webpy_gallery.json`** — generated manifests of the per-cruise CODAS section figures. The gallery fetches both at runtime; a missing manifest leaves that project's gallery in its unavailable state without affecting the map or coverage drawer.
- **`data/calibrations.json`** — the calibration histories carried over from the original adcp.ucsd.edu portal, produced by `tools/harvest_calibrations.py` (see below). Fetched at runtime by the Documentation page; absent, that page says so and nothing else is affected.
- **`index.html`** — the public-facing portal. Fetches the data files at runtime and builds all UI (Leaflet maps, coverage charts, image gallery, cruise table) via JavaScript. Contains embedded fallback data (`EMBEDDED_DATA`) for `file://` preview.
- **`admin.html`** — a standalone form tool for composing new cruise records. Its output is JSON to copy-paste into `site_data.json`. It does not write files directly.
`tools/` holds local, uncommitted tooling — `harvest_calibrations.py` and `build_calcofi_cruises.py` (both below), which need nothing but the web, `site_data.json` and the generated data files. Their output is committed; the scripts are not, like the CODAS builders under `../../science/technical_sadcp/scripts/`.
- **`images/`** — manually curated image files referenced by `site_data.json` (`cruise.images[].filename` paths are relative to this folder) are ignored. The reproducible generated figures under `images/antarctic-webpy/` and `images/calcofi-webpy/` are committed static assets.
- **`input_info/harvest/`** — the only part of `input_info/` that is committed: the original-portal pages the generated data is derived from (the three calibration pages, the CalCOFI atlas cruise index, and JASADCP's CalCOFI inventory), kept so the harvests stay reproducible after adcp.ucsd.edu and uhslc are gone.

## Measured tracks — Antarctic (`data/drake_passage_tracks.json`)

Produced by **`../../science/technical_sadcp/scripts/make_drake_passage_web_tracks.py`**, which is deliberately kept outside this repository: it needs pycurrents/CODAS and the raw loads under `/work/smullersoares_work/data/adcp/`. The file covers the series in two halves, built from two different repositories and merged into one file.

**2019 onwards** — the in-house UHDAS loads, found by crawling a directory:

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python scripts/make_drake_passage_web_tracks.py \
    /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

**1999–2018** — the science-ready sets submitted to the Joint Archive for Shipboard ADCP. These sit in `/work/smullersoares_work/data/adcp/jas_repo_complete/`, one numbered SAC directory per submitted database among ~2600 unrelated neighbours, so the cruises are selected first and the list handed to the builder. `select_drake_passage_jas_dbs.py` reads the repository's `total.inv` / `new.inv` inventories and keeps the databases attributed to the Chereskin group inside the Drake Passage box (south of 50°S, 80°W–35°W); `--merge-into` folds the result into the existing file, leaving the 2019-onwards cruises alone:

```bash
cd ../../science/technical_sadcp
python scripts/select_drake_passage_jas_dbs.py \
    --meta-out drake_passage_jas_cruises.json > jas_drake_dbs.txt
conda run -n py_ddt python scripts/make_drake_passage_web_tracks.py \
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
conda run -n py_ddt python scripts/make_drake_passage_web_tracks.py \
    --db-list ncei_dbs.txt \
    --merge-into ../../software/adcp_ucsd/data/drake_passage_tracks.json \
    --source-label /work/smullersoares_work/data/adcp/drake_passage_2019_onwards \
    /work/smullersoares_work/data/adcp/drake_passage_2019_onwards/ \
    ../../software/adcp_ucsd/data/drake_passage_tracks.json
```

`dbs_dir` has to be the repository root rather than the accession, because `instruments[].db_dir` is recorded relative to it and `scripts/make_drake_passage_web_gallery.py` resolves a database as `<root>/<db_dir>/adcpdb/<db>`. For the UHDAS and JAS layouts that relative path is a bare directory name, so those entries are unaffected. Two of them (LMG1104, LMG1805) name both their databases after the same sonar in the `.bft`; the builder relabels the deeper one `os38nb` from its depth range and keeps the original under `instruments[].sonar_reported`.

Per cruise it holds:

- `site_id` — the key that matches `cruise.track_key` in `site_data.json`.
- `segments[]` — arrays of `[lat, lon]` for the ensembles carrying valid (non-masked) `u` and `v`, thinned to ~2 km spacing and split where the track jumps in time (>2 h) or position (>50 km). Databases of the same cruise (nb150 + os38nb) are merged into one track.
- `instruments[]` — one entry per CODAS database, each with a `coverage` block giving, per depth bin, `n_good` / `coverage_pct` (non-masked `u` and `v` over all ensembles), `err_rms_ms` and `pg_mean`, plus `max_depth_50pct` / `max_depth_80pct`.
- Cruise aggregates: `track_length_km`, `duration_days`, `n_drake_crossings`, `bbox`, `n_ens_valid`.

## Measured tracks — CalCOFI (`data/calcofi_tracks.json`)

Produced by **`../../science/technical_sadcp/scripts/make_calcofi_web_tracks.py`**,
the California Current counterpart of the Drake Passage builder. It imports
that builder's geometry, coverage and merging helpers rather than copying them,
so the two files hold the same kind of record; what differs is the selection
and the identity.

**Selection.** A CalCOFI cruise cannot be recognised from its CODAS metadata,
and no bounding box separates it from its neighbours — the California Current
repositories also hold the CCE-LTER process cruises (RR1710, RR2105), the
Atlantis/Oceanus/Thompson transits, and Atlantic and Arctic loads. So the
cruise a database belongs to is supplied rather than inferred:
**`scripts/select_calcofi_dbs.py`** writes a `<db path>\t<site id>` list plus a
metadata sidecar, from two sources.

- **1993–2009, the JAS-ADCP archive.** JASADCP publishes its own CalCOFI
  inventory, which is the authoritative list of what the program submitted: 40
  cruises, one SAC id and one NB150 database each, `<repo>/<sac>/<sac>`. A copy
  of that page is committed at
  `input_info/harvest/jasadcp_calcofi_inventory.html`. Thirty-nine are the
  Chereskin-group cruises the 2008 Digital Atlas published; the fortieth is
  NH0901 (SAC 01304, January 2009), processed at UH by Firing and Hummon.
- **2017–2023, the in-house UHDAS loads** under
  `/work/smullersoares_work/data/adcp/uh_repo_ccs_dbs/` (`cryosat/` and
  `cryosat_2023/`). These carry no archive id, and their cruise name is
  `SR2105` as often as `RL2001_WinterCalCOFI`, so the 15 CalCOFI cruises were
  identified against the CalCOFI program's own cruise list (calcofi.org) by
  ship and date and are listed explicitly in the script's `RECENT` table —
  every one matching a listed CalCOFI cruise date for date.

```bash
cd ../../science/technical_sadcp
python scripts/select_calcofi_dbs.py \
    --meta-out calcofi_cruises.json > calcofi_dbs.txt
conda run -n py_ddt python scripts/make_calcofi_web_tracks.py \
    --db-list calcofi_dbs.txt \
    --root /work/smullersoares_work/data/adcp/jas_repo_complete \
    --root /work/smullersoares_work/data/adcp/uh_repo_ccs_dbs \
    ../../software/adcp_ucsd/data/calcofi_tracks.json
```

Pass `--root` once per repository: each database is named relative to the root
it sits under, so `instruments[].db_dir` is a bare SAC id (`00410`) for the
archive and a path (`cryosat/SR2105/os38nb`) for a UHDAS load, and the gallery
tells the two apart on that.

The record matches the Drake Passage one except for the fourth cruise
statistic: there is no crossing to count, so it carries **`deepest_50pct_m`** —
the deepest bin any of the cruise's sonars still fills in half its ensembles,
which is what separates an OS38 cruise from an NB150 one here. `index.html`
picks the drawer's fourth stat card on whichever of the two the track record
carries.

Two `.bft` files need repairing as they are read, which
`repair_identity()` does and reports: RR9901 writes `#SAC_CRUISE_ID:` twice,
the second time empty, so the id is taken from the load directory (in the
JAS-ADCP repository the directory *is* the SAC id); and NH0901 declares its
instrument as `75kHz narrowband` in prose, so the reader returns `os75??` and
the ping type is read out of the header instead, the original kept under
`instruments[].sonar_reported`.

The selection yields **55 cruises over 71 CODAS databases** — 40 archived, one
database each (NB150 throughout, except NH0901's OS75NB), and 15 processed in
house, which run an OS75 on the NOAA ships and an OS38 + OS150 + WH300 together
on R/V Sally Ride.

## Antarctic CODAS section gallery (`data/antarctic_webpy_gallery.json`)

The gallery is built offline by
**`../../science/technical_sadcp/scripts/make_drake_passage_web_gallery.py`**
with the `py_ddt` Conda environment. It uses `site_data.json` and the
measured-track file as the portal identity contract, so every gallery record is
keyed to a map-selectable `cruise.id` / `track_key` pair. It never writes
inside either raw CODAS source tree. `images/` is otherwise ignored by git, but
`images/antarctic-webpy/` is committed — it is reproducible output, and the
published site has to serve it.

A cruise publishes **section figures only** — four panels: `u`, `v`, signal
amplitude and percent good, with the green ship-speed trace over the velocity
panels alone. These are not a `quick_web.py` product: `quick_web.py` has no way
to choose its panel list, so the builder drives
`pycurrents.adcp.panelplotter.plot_data` directly with
`axlist=['u','v','amp','pg']` and `speed=True`, which is what puts speed over
`u` and `v` and leaves amplitude and percent good clean. It also restores the
bottom colorbar that `plot_data` hides for its own default bottom panel.

The `ADCP_vectoverview` cruise map is no longer published, and neither are the
per-section `quick_web` families (`txy`, `vect`, `ddaycont`, `loncont`,
`latcont`) — the complete set for all 422 databases came to roughly 1.8 GB,
past the 1 GB ceiling GitHub Pages puts on a published site. `index.html`
still knows their labels, so an older manifest still renders.

### Which sonars a cruise publishes

One database per *physical* sonar: an Ocean Surveyor logged in both ping modes
leaves an `os38bb` and an `os38nb` database, but it is one instrument, so
`sonar_family()` groups them and only the better one is published.

Within a family the healthy databases are preferred over a deeper-reaching
broken one. A database is healthy when

- it has a depth bin holding valid velocity in half its ensembles,
- at least half its ensembles carry valid `u` and `v`,
- its ensemble count covers at least 80% of the recording time the cruise's
  busiest sonar managed, and
- its first-to-last envelope spans at least 80% of the cruise.

The ensemble-count test is the one that matters in practice: a sonar that went
down for two days mid-cruise keeps a full start-to-end envelope and a
respectable valid fraction, and only its ensemble count gives it away.
`section_windows()` then backstops it — if a surviving sonar still has nothing
to draw in one of the planned windows, it is dropped there and the windows
re-planned without it, so "the same windows for both" always holds.

Where both sonars pass, both are published; where only one does, the other is
recorded under the cruise's `omitted[]` with the reason, and the portal says
so. A cruise where nothing passes still publishes its least bad database rather
than no figures. Over the series that is **161 cruises publishing two sonars,
80 publishing one**, with ten sonars dropped on health.

`--single-sonar` restores the earlier behaviour of publishing only the
deepest-reaching database of each cruise.

### How the sections are chosen

Both sonars of a cruise are read on one yearbase and planned **together**, from
the union of their ensemble times, so the windows are identical figure for
figure: an NB150 panel and the OS38 panel beside it cover exactly the same
hours and can be read against one another.

`plan_sections()` works on *covered* time — wall-clock time with the data gaps
taken out — so each figure carries about the same amount of data however the
cruise was interrupted:

1. count the covered days (gaps longer than `--section-gap-hours`, 6 h, do not
   count) and ask for `ceil(covered / --section-target-days)` figures, clamped
   between `--min-sections` (3) and the ceiling;
2. break the record at every gap longer than `--section-hard-gap-hours` (24 h)
   — a port call or a long science stop — then fold any resulting segment
   holding less than half a figure's worth of data back into its neighbour,
   but only across a gap shorter than one figure's span. Swallowing a
   fortnight alongside would cost more axis than the data it brings. Where
   there are still more unavoidable breaks than figures, join the adjacent
   pair that costs the least axis rather than discarding the gap structure;
3. apportion the figures across the surviving segments, each new figure going
   to whichever segment would otherwise carry the widest ones, and cut inside a
   segment at equal covered time — snapping to a shorter gap when one lies
   close to the cut;
4. spend any unused budget splitting whichever figure still has the most blank
   axis at its own longest gap.

The ceiling is `--max-sections` (6) for a cruise publishing one sonar and
`--max-sections-per-sonar` (5) for a cruise publishing two, so ten figures at
most either way. Across the series that is **985 windows and 1,619 figures for
241 cruises**, averaging 4.3 days per window; the longest spans 11.5 days
(LMG2305, a 50-day cruise) and eight windows in the series run past ten.

### Running it

Run a no-write check first — the dry run prints the planned windows, which
sonars each cruise publishes, and what it omits:

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python scripts/make_drake_passage_web_gallery.py \
    --cruise LMG2304 --dry-run
```

Rebuild the whole gallery — 241 cruises, roughly 45 minutes and about 515 MB:

```bash
conda run -n py_ddt python scripts/make_drake_passage_web_gallery.py
```

Every run renders from the CODAS databases; nothing is reused. After each
cruise, `prune_cruise_assets()` removes whatever that cruise used to publish
and no longer does, so no unreferenced PNG is left in the repository. Use
`--strict` when every selected cruise must succeed and `--keep-scratch` only
while diagnosing a pycurrents failure.

A `--cruise`-filtered run preserves the manifest records of every cruise
outside the filter, so a targeted refresh is safe:

```bash
conda run -n py_ddt python scripts/make_drake_passage_web_gallery.py \
    --cruise LMG2304 --cruise LMG2202
```

Validate the resulting manifest with `python3 -m json.tool
data/antarctic_webpy_gallery.json >/dev/null`, then preview over HTTP. In the
portal, an Antarctic cruise's `Plots` button selects the corresponding gallery;
the next `Plots` selection replaces it. A cruise publishing two sonars lays its
gallery out in two columns, one window per row, the deeper sonar on the left.
Map clicks remain dedicated to the coverage drawer.

The manifest is `schema_version: 3`. Each cruise record carries `sonars[]`,
`section_count`, and `omitted[]`; each plot row carries `section`,
`section_count`, `section_start` / `section_end` (ISO UTC), `section_dday`,
`section_days`, `section_bbox` (`[lat_min, lon_min, lat_max, lon_max]`) and
`n_ens` alongside `family` / `image` / `thumbnail` / `sha256`. Rows are sorted
window first and deeper sonar first, which is the order the gallery shows them.

## CalCOFI CODAS section gallery (`data/calcofi_webpy_gallery.json`)

Built by **`../../science/technical_sadcp/scripts/make_calcofi_web_gallery.py`**,
which imports the section planning, the health rules and the figure rendering
from the Antarctic builder and publishes the same four-panel product under
`images/calcofi-webpy/`. Three things differ.

- **Two source repositories at once.** `instruments[].db_dir` says which: a
  bare five-digit name is a SAC id under `jas_repo_complete/`, anything else is
  a path under `uh_repo_ccs_dbs/`. Both are checked against
  `select_calcofi_dbs.py` before anything is read, so no unrelated SAC
  directory or neighbouring California cruise can be drawn into the gallery.
- **Up to three sonars per cruise,** so the per-sonar ceiling falls as a cruise
  publishes more of them — 6 windows for one sonar, 5 each for two, 4 each for
  three — which keeps any cruise to about a dozen figures.
- **A sonar-family rule that reads the frequency.** The Antarctic builder
  takes a fixed four characters of the sonar name as its physical instrument,
  which is enough for a series running only `os38bb`/`os38nb`; here the family
  is the model and the whole frequency, so a three-digit `os150nb` is not
  filed under a truncated `os15`. Either way `os75bb` and `os75nb` are one
  Ocean Surveyor — SH2103 logged both and publishes the better one.

Figures are published under the sonar directory alone
(`images/calcofi-webpy/SR2105/os38nb/`) rather than the repository path, which
would repeat the cruise; `plots[].database` still records the full `db_dir`.

Across the series that is **263 windows and 323 figures for 55 cruises**,
averaging 3.7 days per window and never passing 5.2; 46 cruises publish one
sonar, 3 publish two and 6 publish three, with one database dropped (SH2103's
`os75bb`, the weaker ping mode of a sonar that is published). At about 124 MB
it sits beside the Antarctic gallery's 518 MB, well inside the 1 GB ceiling
GitHub Pages puts on a published site. A full rebuild takes roughly an hour.

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python scripts/make_calcofi_web_gallery.py \
    --cruise SR2105 --dry-run          # plan only, nothing written
conda run -n py_ddt python scripts/make_calcofi_web_gallery.py
```

As with the Antarctic gallery, a `--cruise`-filtered run preserves the manifest
records of every cruise outside the filter, `prune_cruise_assets()` removes
what a cruise no longer publishes, and the manifest is `schema_version: 3` with
the same row shape. Validate with `python3 -m json.tool
data/calcofi_webpy_gallery.json >/dev/null`, then preview over HTTP.

## Calibration tables (`data/calibrations.json`)

The original portal keeps its calibration history in hand-maintained 1990s
HTML, one page per program. `tools/harvest_calibrations.py` — kept locally,
outside version control — reads those pages and writes
`data/calibrations.json`, which the Documentation page renders under
**Calibrations**, after the CODAS3 processing panel:

| table id | source page | holds |
| --- | --- | --- |
| `lmgould` | `lmgould/lmgould.history.html` | 223 Gould cruises plus 40 refit/cancelled rows, 1999–2021 |
| `calcofi` | `calcofi/calcofi_calib_history.htm` | 43 CalCOFI cruises, 1993–2006 |
| `echo-intensity` | `calcofi/adcp_cal.htm` | per-transducer Erc / K1 / K2 constants, 5 transducers |

```bash
python3 tools/harvest_calibrations.py                       # from the live site
python3 tools/harvest_calibrations.py --from-dir input_info/harvest
```

The pages are also kept under `input_info/harvest/` — the one exception to that
directory being ignored — so the harvest is reproducible after adcp.ucsd.edu is
gone. `--from-dir` reads them by basename.

Three things the parser has to get right, because the source markup fights it:

- **HTML comments hold retracted cells and whole rows.** They are stripped
  before parsing; a parser that ignores them republishes withdrawn values.
- **Rows stop early rather than padding.** The declared column list wins and
  short rows are padded on the right. A row *wider* than the header means the
  columns have shifted, and the harvester raises rather than publishing values
  filed under the wrong heading.
- **`<br>` inside a cell separates two values for one column** — a southbound
  and a northbound calibration, say. It becomes ` / ` in the data and a second
  line in the rendered cell.

A cruise row is `{cells, year, cruise, kind}`. `cells` matches `columns[]` and
is verbatim from the source, shorthand and all — `legend[]` carries the key
that explains it, in the groups the original printed. `year` drives the year
chips. `cruise` is the portal cruise id the row refers to, resolved at harvest
time against `site_data.json` (the old tables say `lg1901` where the portal
says `LMG1901`, and some CalCOFI rows carry the sonar as a suffix); where it
resolves, the id in the table opens that cruise's track and coverage drawer.
`kind` is `"note"` for a row recording a refit or a cancelled cruise rather
than a processed one, which the table shades differently.

Re-run the harvest after adding cruises to `site_data.json`: the `cruise` links
are resolved at harvest time against the cruises the portal then knows. Adding
the CalCOFI series took the `calcofi` table from 1 linked row to 39; the four
that stay unlinked (`sp9712`, `nh0604`, `kn0605_os75nb`, `kn0605_nb150`) were
never submitted to the archive and have no database in either repository.

## Data model (`site_data.json`)

The `_README` key at the top of the file documents the schema. Key points:

- `projects[]` — top-level programs (currently `"antarctic"` and `"calcofi"`). Each project has `id`, `color`, `map_center`, `map_zoom`, and a `cruises[]` array.
- `cruise.track` — array of `[latitude, longitude]` pairs (negative = S/W) forming the map polyline.
- `cruise.stations` — array of `{lat, lng, label}` objects for individual markers.
- `cruise.images[].filename` — basename only; file must exist at `images/<filename>`.
- `cruise.status` — one of `"processed"`, `"archived"`, `"in_review"`, `"pending"`.
- `cruise.jasadcp_url` — optional; renders a purple "JASADCP" button in the data table when present.
- `cruise.track_key` — links the cruise to its measured track in `data/drake_passage_tracks.json` or `data/calcofi_tracks.json`. When it resolves, the measured track replaces `cruise.track` on the map and the row becomes clickable.
- `cruise.CODAS_dbs` — the CODAS database directories the cruise was built from; the table is expected to stay in step with these loads.
- `cruise.sac_id` / `cruise.sac_ids` — the JASADCP (NODC/UH SAC) cruise id of the primary database, and one `{sac_id, sonar}` entry per submitted database. `jasadcp_url` is `https://uhslc.soest.hawaii.edu/sadcp/DATABASE/<sac_id>.html`. Cruises processed in house and not yet submitted have none of these — the Antarctic series from 2019, the CalCOFI series from 2017.
- `cruise.calcofi_cruise` — CalCOFI only: the programme's own name for the cruise (`2107SR` — year, month, ship), which is how CalCOFI indexes the hydrography and plankton data from the same stations.
- `project.plots_link_label` — names the external plot page a cruise row links to *beside* its generated CODAS gallery. Set to `"Atlas"` on CalCOFI, where `cruise.plots_url` is the 2008 CalCOFI ADCP Digital Atlas page of objectively mapped velocity at 50 m and 100 m, which the section figures do not replace. Which cruises have one is read from the atlas's own cruise index, committed at `input_info/harvest/calcofi_all_cruise.htm` — 39 of the 55. Left unset (Antarctic), an external `plots_url` is shown only for cruises with no generated gallery.
- `cruise.ncei_accession` — the bare NCEI accession number behind `ncei_url` (`https://www.ncei.noaa.gov/archive/accession/<n>`). JASADCP submissions up to ~2018 were archived in batches, so many cruises share one accession; from 2019 each Drake Passage season has its own. `../../science/technical_sadcp/scripts/resolve_jasadcp_ncei_accessions.py` rebuilds the SAC-id-to-accession mapping by walking the NCEI archive directories (NCEI's own mapping page went with the GOCD when it was decommissioned in April 2025).
- The gallery manifests are intentionally separate from `cruise.images[]`; they carry generated CODAS section-figure paths, thumbnails, checksums, per-window time and position metadata, and per-cruise availability.
- The CalCOFI cruise rows are generated, not hand-written: `tools/build_calcofi_cruises.py` derives every field from `data/calcofi_tracks.json`, the `select_calcofi_dbs.py` sidecar and the NCEI accession map, and rewrites `projects[].cruises`, `years` and `vessel` for that project while leaving its prose alone.

```bash
python3 tools/build_calcofi_cruises.py \
    --meta       ../../science/technical_sadcp/calcofi_cruises.json \
    --accessions ../../science/technical_sadcp/jasadcp_ncei_accessions.json
```

## index.html JavaScript structure

Key globals and functions:

- `SITE` — populated after `loadData()` resolves; holds the full parsed `site_data.json`.
- `TRACKS` — measured tracks keyed by `site_id`, merged from every file in `TRACK_FILES`; `trackFor(cruise)` / `hasTrack(cruise)` resolve a cruise against it. Cruise ids are unique across the projects, which is what lets the two files share one index.
- `WEBPY_GALLERY` — section-figure manifests keyed by cruise id, merged from every file in `WEBPY_GALLERY_FILES`. `hasCodasGallery(projId)` says which projects have one (`CODAS_GALLERY_PROJECTS`), and `galleryProjId` tracks whose gallery DOM is on screen, since the ids are `gallery-<project>`; a selection is dropped when the project changes. `webpyBadge()` / `webpyTileText()` label each tile from the row's `section_count`, dates and `section_bbox`, and `setGallerySonarColumns()` gives the grid one column per published sonar (`sonars-2`, `sonars-3`) so each row is one window read across its sonars.
- `plotsLinks(p, cruise, track)` — the Plots links of a cruise row and of its coverage drawer: the gallery button, plus the external `plots_url` when the project sets `plots_link_label`, otherwise the button replaces it.
- `coverageFourthStat(t)` — the drawer's fourth stat card, the one thing that differs by series: 60°S crossings where the track record carries `n_drake_crossings`, depth at 50% coverage where it carries `deepest_50pct_m`.
- `mapsInitialized` — keyed by `project.id`; stores the Leaflet `Map` instance to prevent double-init.
- `mapCruiseLayers` — keyed by `project.id` then `cruise.id`; stores per-cruise `LayerGroup` for the toggle checkboxes.
- `mapCruiseLines` — the visible polylines of each cruise, used by `highlightTrack()` to thicken a track when its table row is hovered (and vice versa).
- `initSite()` — runs once after data loads; builds footer, hero buttons, stats, and project cards.
- `showProject(projId)` — builds the full project page HTML (`buildProjectHTML`) and defers map init by 100 ms to let the DOM paint.
- `initProjectMap(p)` — creates the Leaflet map with ESRI Ocean basemap (no API key required) and an OSM fallback layer; draws one `LayerGroup` per cruise for toggling. Measured tracks are drawn solid, one polyline per segment plus a wide transparent hit line; illustrative `cruise.track` arrays stay dashed.
- `toggleCruiseLayer / setCruisesAll / setCruisesYear` — toggle cruise track visibility via the chip bar below each map. With the full series on the map the chips run to a few hundred, so they sit in their own scroll area and `setCruisesYear` (one button per season, from `cruiseYear`) narrows the map to a single year.
- `sacLink(sac, published)` — renders a SAC id as a link to its JASADCP page; used in the coverage drawer's per-sonar cards. Ids that are not five digits (`unsubmitted`) get no link, and an id whose page is not published yet is shown without one.
- `SONAR_COLORS` / `SONAR_NAMES` — one entry per sonar the series runs: `nb150`, the OS38 pair, and the `os75`/`os150`/`wh300` the California Current cruises add.
- `focusCruise(projId, cruiseId)` — zooms to the cruise bbox and opens the coverage drawer; wired to both the table rows and the map tracks.
- `openCoverage()` / `profileChart()` — the drawer and its two depth profiles (coverage %, error-velocity RMS), drawn as inline SVG with a hover readout (`covHover`) and a "show the numbers" table. Under the stat cards, `.cov-extent` reports the measured date range to the day and the latitude and longitude extremes, formatted by `fmtDateRange()` / `fmtLat()` / `fmtLon()` from the track record's `start`, `end` and `bbox`.

- `buildCalibrationCards()` / `showCalibration(id)` — the Documentation page's Calibrations block and the full-width view of one table, with `calFilter()` / `calYear()` behind the search box and year chips. `focusCruiseFromCalibration()` hands a linked cruise id to `showProject()` and then `focusCruise()`.

Navigation is section-based (no URL routing): `showSection(id)` shows/hides `<section id="section-{id}">` elements. The sections are `home`, `project`, `docs` (the Documentation tab) and `calibration` (one calibration table, reached from Documentation).
