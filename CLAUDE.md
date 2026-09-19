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

The site has three source files and eight data files:

- **`site_data.json`** — the single source of truth for all site content. All cruise metadata, image references, and external links live here. Editing this file updates the entire site.
- **`data/drake_passage_tracks.json`**, **`data/calcofi_tracks.json`**, **`data/epac_tracks.json`** — measured ship tracks and depth-coverage statistics extracted from the CODAS databases (see below), one file per programme. All are fetched at runtime alongside `site_data.json` and share one `TRACKS` index, since cruise ids are unique across the projects; absent or unreachable, the site falls back to the illustrative `cruise.track` arrays.
- **`data/antarctic_webpy_gallery.json`**, **`data/calcofi_webpy_gallery.json`**, **`data/epac_webpy_gallery.json`** — generated manifests of the per-cruise CODAS section figures. The gallery fetches all three at runtime; a missing manifest leaves that project's gallery in its unavailable state without affecting the map or coverage drawer.
- **`data/calibrations.json`** — the calibration histories carried over from the original adcp.ucsd.edu portal, produced by `tools/harvest_calibrations.py` (see below). Fetched at runtime by the Documentation page; absent, that page says so and nothing else is affected.
- **`index.html`** — the public-facing portal. Fetches the data files at runtime and builds all UI (Leaflet maps, coverage charts, image gallery, cruise table) via JavaScript. Contains embedded fallback data (`EMBEDDED_DATA`) for `file://` preview.
- **`tools/admin.html`** — a standalone form tool for composing new cruise records. Its output is JSON to copy-paste into `site_data.json`; it does not write files directly. It lives under `tools/` and is *not* published: it serves no purpose on the live site, and keeping it out of the deploy keeps it out of the accessibility scope described below.
`tools/` holds local, uncommitted tooling — `harvest_calibrations.py`, `build_calcofi_cruises.py` and `build_epac_cruises.py` (all below), which need nothing but the web, `site_data.json` and the generated data files. Their output is committed; the scripts are not, like the CODAS builders under `../../science/technical_sadcp/scripts/`.
- **`images/`** — manually curated image files referenced by `site_data.json` (`cruise.images[].filename` paths are relative to this folder) are ignored. The reproducible generated figures under `images/antarctic-webpy/`, `images/calcofi-webpy/` and `images/epac-webpy/` are committed static assets, 739 MB together.
- **`reports/`** — ignored. The accessibility audit (`accessibility-audit.html`, a saved copy of the published Artifact) and `reports/checks/`, the scripts its numbers come from: four jsdom suites over the JavaScript-built DOM, plus the JASADCP search and the spreadsheet merge. `reports/README.md` has the Artifact link and how to re-run everything.
- **`input_info/harvest/`** — the only part of `input_info/` that is committed: the sources the generated data is derived from (the three calibration pages, the CalCOFI atlas cruise index, JASADCP's CalCOFI inventory, the Eastern Pacific inventory extract `jasadcp_epac_inventory.txt` and the accession table `epac_ncei_accessions.csv`), kept so the harvests stay reproducible after adcp.ucsd.edu and uhslc are gone.

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

## Measured tracks — Eastern Pacific (`data/epac_tracks.json`)

Produced by **`../../science/technical_sadcp/scripts/make_epac_web_tracks.py`**,
the third of the series. It imports the geometry, coverage and merging helpers
from the Drake Passage builder and `merge_cruise` from the CalCOFI one, so the
record matches the CalCOFI one field for field — including the fourth cruise
statistic `deepest_50pct_m`, which `index.html` picks on whichever of the two
the track record carries. What differs is the selection, the identity and the
depth ceiling.

**What the project is.** The eastern-Pacific part of the group's NASA cruise
list — the 58 cruises recorded in `input_info/Cryosat Accessions.xlsx` — with
the CalCOFI cruises removed, because those are their own tab. The work was
done for the **NASA Ocean Surface Topography Science Team (OSTST) under awards
NNX17AH53G and 80NSSC21K1822**, which is what the project prose cites. The 58
break down exactly:

| group | n | disposition |
| --- | --- | --- |
| Eastern Pacific, CODAS database found | 39 | published |
| CalCOFI | 15 | the `calcofi` project |
| North Atlantic (AT30_01, AR46, AR60_01, AR69-03) | 4 | out of region |

Three more come from `my_codas_proc` and are not in the spreadsheet at all:
**RR2104, SR2007 and SR2212**. That is **42 cruises with measured tracks over
90 CODAS databases**, spanning 53.5°S to 49.1°N and 171.7°W to 70.3°W — every
cruise on the list, since TN310's databases arrived (below). It is TN310 that
sets the western limit.

**Four cruises the portal had written off were recovered**, three of them from
tarballs. It first listed TN265 and KOK1605 as having no data, KOK1607 as
archive-only, and TN310 as navigation-only. Crawling *every* CODAS database in
the repositories (579 of them, across `uh_repo`, `uh_repo_ccs_dbs`,
`my_codas_proc` and `unprocessed_data`) settled the first three; TN310 was
settled later, when its tarball appeared:

- **KOK1607** is archived as SAC 02518 (`kk1607:wh300`) and the database is in
  `jas_repo_complete/02518`, so it is built from the archive like the other 21.
- **TN265** and **KOK1605** have complete loads inside
  `uh_repo/tarballs/TN265_seaflow.tar.gz` and `kok1605_seaflow.tar.gz` —
  the SeaFlow program's copies, in the standard UHDAS layout. They are
  unpacked to a **new** root, `/work/.../adcp/uh_repo_from_tarballs/`, which
  has its own README saying where each came from; the tarballs are untouched.
  TN265's yearbase reads 2011 straight off the database, confirming exactly
  what its navigation file's timestamp had implied.
- **TN310** had nothing at all when the project was first built — no tarball,
  no directory, no archive entry, only its navigation — and the portal carried
  it as `nav_only` on that basis. On **2026-09-18** a 222 MB `TN310.tar.gz`
  appeared in `uh_repo/tarballs/` — an `os75bb` + `os75nb` UHDAS load — and
  was unpacked to `uh_repo_from_tarballs/TN310/`, so it is now selected,
  measured and published like any other load: 8,016 km over 16 days,
  2014-05-21 to 2014-06-06, 13.7°S–44.0°N and 171.7°W–124.8°W, reaching 745 m
  at 50% coverage. Its `dbinfo.txt` reads `yearbase 2014`, which is the second
  confirmation — after TN265's 2011 — that the year inferred for a
  navigation-only cruise from its file timestamps and the ship's cruise
  numbering was right. It carries `status: "submitted"`: the data went to the
  repository and no accession has come back.

A search of the same crawl for cruises *not* in the spreadsheet found a pool of
about 35 more eastern-Pacific loads under
`unprocessed_data/unprocessed_ccs_cruises_uh_repo/{first_14,
saulo_promising_cruises, home, Anela}` — California Current cruises, mostly
2–12 day transits, with SR2210, SR2323 and SR2418 the most likely genuine
omissions. They are **deliberately not published**: the tree is named
"unprocessed", the cruises were gathered as candidates for other purposes, and
adding them would assert OSTST membership that nothing on disk substantiates.
Revisit that pool if the project list grows.

**Selection.** Membership cannot be decided geographically — the same
spreadsheet holds the North Atlantic cruises and the five repositories hold
several hundred loads belonging to other projects — so it is an explicit list
in **`scripts/select_epac_dbs.py`**, in two tables:

- **ARCHIVED** — 22 cruises, one SAC id per submitted database, 49 databases in
  all. Every id is checked against the committed inventory extract
  `input_info/harvest/jasadcp_epac_inventory.txt`, which also supplies the
  platform, the archive date range and the PI. The script fails rather than
  guessing if an id is absent from the extract or off disk.
- **LOCAL** — 20 cruises that exist only as in-house loads, across `uh_repo`,
  `uh_repo_ccs_dbs`, `my_codas_proc` and `uh_repo_from_tarballs`, 41
  databases. The load directory is *named*, not discovered, because most of
  these loads keep alternate processing beside the publishable product and
  walking the tree would publish both. The table's comments say why each
  choice was made; the two that are easy to get backwards:
  - **SR2006** publishes `.hydrins`, not `.amp_refbins`. The load's own README
    (Hummon, 2020/10/07) calls the first "the usual, with editing, phase, and
    amplitude corrections" and the second "an experimental watertrack
    calculation".
  - **SR2212** publishes `os38nb_orig`, the opposite of SR2007. Its
    reprocessed `os38nb` and `wh300` databases hold their 857 and 2,136
    ensembles but **no navigation and no velocity at all** — every lon, lat,
    `u` and `v` is masked, so `putnav`/`loaddata` never completed. The
    Workhorse has no intact copy anywhere, so SR2212 publishes one sonar.
  - **MV1104** publishes the final 2017 reprocessing (`os150`, `os75`), not
    the 2011 at-sea loads or the first 2017 pass, three generations of which
    sit side by side.

```bash
cd ../../science/technical_sadcp
python scripts/select_epac_dbs.py --meta-out epac_cruises.json > epac_dbs.txt
conda run -n py_ddt python scripts/make_epac_web_tracks.py \
    --db-list epac_dbs.txt \
    --root /work/smullersoares_work/data/adcp/jas_repo_complete \
    --root /work/smullersoares_work/data/adcp/uh_repo \
    --root /work/smullersoares_work/data/adcp/uh_repo_ccs_dbs \
    --root /work/smullersoares_work/data/adcp/my_codas_proc \
    --root /work/smullersoares_work/data/adcp/uh_repo_from_tarballs \
    ../../software/adcp_ucsd/data/epac_tracks.json
```

Pass `--root` once per repository, in any order; each database is named
relative to the root it sits under, so `instruments[].db_dir` is a bare SAC id
(`02499`) for the archive and a path (`cryosat_2023/TN411/os75nb`) for a load.

### Sonar names come from pysadcp, and it needed two fixes

`repair_identity()` calls pysadcp's **`resolve_inst_id`**, which reads the
instrument and ping mode out of the block `quick_adcp.py` embeds in each
database's metadata and only ever makes an id *more* specific. Three of these
loads need it — MV1104's `os150` and `os75`, and SR2204's `os38` — each a
sonar that logged both ping modes and left the choice to processing. Building
this series exposed two bugs in that function, both fixed on the pysadcp branch
**`fix/dbinfo-annotated-pingtype`** (commits `214d4e4` and `1364fdb`), and
**this builder needs a pysadcp carrying them**:

1. `parse_dbinfo_params` located the block by its `## (determined from
   "sonar")` lines and then read only lines of that same shape, so a value
   annotated with any other reason fell through to the comment rule and was
   dropped. That cost the resolver exactly the population it exists for: a
   sonar name omits its ping type *because* two modes were logged, and that is
   the case recorded as `## (mixed pings, chosen from pingpref): pingtype =
   nb`. Without the fix those three publish as `os150`, `os75` and `os38`.
2. `resolve_inst_id` promised that a Workhorse comes back unchanged and did
   not: against a real `wh300` block it returned **`wh300bb`**, a sonar name
   nothing uses. The existing test asserted the right thing but passed for the
   wrong reason — its fixture is an `os75` block, so the instname guard
   tripped and the missing rule was never exercised. `translate_inst_str`'s own
   list of complete names is now hoisted to `COMPLETE_INST_IDS` and used as the
   guard.

**One database still has to be corrected by hand**, in `SONAR_OVERRIDE`:
PS1307's **02527**, which the reader calls `os75bb` when its own block says
`nb` and 02526's prose spells the pair out ("Surveyor 75 kHz in broadband (SAC
ID 02526) and narrowband (SAC ID 02527) modes for deeper ranger"). The JASADCP
inventory carries the same error. `resolve_inst_id` rightly declines to touch
an id that already states a ping type, so this is recorded rather than
inferred. `check_sonars()` backstops it — two databases of one cruise ending up
with the same sonar name is a mislabelling rather than something to guess at,
so it stops the run.

The Drake Passage builder's `disambiguate_sonars()` is deliberately **not**
used: its relabel-from-depth-range rule guesses from the Drake sonar set, and
given PS1307's two OS75 databases it renames them `nb150` and `os38nb`.

### The depth ceiling is 2000 m here, not 1200

The other two series extract coverage to 1200 m and neither reaches it —
CalCOFI tops out at 1148 m. The Kilo Moana OS38 narrowband fills bins right up
to 1200, so at that ceiling KM1415, KM1417 and KM1606 all reported a clipped
`deepest_50pct_m` of 1199 m. At 2000 m the real reach shows: 1295 m, 1319 m
and 1487 m, with the deepest bin anywhere in the series at 1988 m. Clipping
real data is worse than matching an axis, and the coverage chart's axis is
per-cruise anyway.

### TN310, the cruise that was navigation-only until its tarball arrived

Until **2026-09-18** TN310 had no CODAS database anywhere, and it was the one
cruise `tools/build_epac_cruises.py` described on its own rather than from a
measured track: its navigation under
`tracks_nav_data_uh_repo/thompson/TN310/proc/<sonar>/nav/a_tt.gps` became an
illustrative `cruise.track`, drawn dashed, the row carried no `track_key` and
so had no coverage drawer, and its status was **`nav_only`** rather than
`submitted`, because only the track was available.

`uh_repo/tarballs/TN310.tar.gz` then appeared and was unpacked to
`uh_repo_from_tarballs/TN310/`, an ordinary UHDAS load with `os75bb` and
`os75nb` databases. TN310 is now selected by `select_epac_dbs.py` like any
other in-house load, measured by `make_epac_web_tracks.py`, drawn solid from
its valid-velocity ensembles, and publishes five section figures from the
narrowband database; its row carries `status: "submitted"`. Both databases
name their own ping type, so nothing here needs `SONAR_OVERRIDE`.

**The year inference was right, and this was its second test.** That navigation
directory recorded no yearbase — no `dbinfo.txt`, no `cruise_info.txt`, no
`.bft`, only `a_tt.gps` — so 2014 had been fixed by two facts that agreed: the
`.gps` modification time (2014-06-06), which falls on the day of the last fix,
and the Thompson's cruise numbering, which the archive pins at TN189 in 2006
and TN320 in 2015. The recovered load's `dbinfo.txt` reads `yearbase 2014`, and
the measured track starts 2014-05-21 and ends 2014-06-06 — the same last day.
TN265's recovered database confirmed 2011 the same way. Both cruises the method
was used on have now been checked against a real load and both were right,
which is worth knowing the next time only navigation survives.

`NAV_ONLY` in `tools/build_epac_cruises.py` is consequently empty and the
nav-reading code below it unused. It is kept rather than deleted: that script
is local, uncommitted tooling, so deleting it would lose it for good, and
`tracks_nav_data_uh_repo` holds navigation for cruises whose databases may
never turn up. The portal keeps `nav_only` in its status vocabulary for the
same reason — `processed` and `pending` are likewise unused by any current
row, so the caption and filter list the closed vocabulary, not the statuses in
use.

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

## Eastern Pacific CODAS section gallery (`data/epac_webpy_gallery.json`)

Built by **`../../science/technical_sadcp/scripts/make_epac_web_gallery.py`**,
which imports the section planning, the health rules and the figure rendering
from the Antarctic builder and the sonar-family rule, the instrument selection
and the per-sonar ceiling from the CalCOFI one, and publishes the same
four-panel product under `images/epac-webpy/`. Two things differ.

- **Five source repositories at once.** `instruments[].db_dir` says where a
  database lives but not which repository: a bare five-digit name is a SAC id
  under `jas_repo_complete/`, and anything else is a path that may sit under
  `uh_repo`, `uh_repo_ccs_dbs`, `my_codas_proc` or `uh_repo_from_tarballs`, so
  `locate_database` tries each in turn. Every candidate is checked against
  `select_epac_dbs.py` before it is read — which matters more here than in
  either other series, because these five repositories hold several hundred
  cruises belonging to other projects, the whole CalCOFI series among them.
  `--load-root` is given four times, in the selector's order, or not at all.
- **Half the cruises publish two sonars.** An Ocean Surveyor logged in both
  ping modes is one physical sonar, so a cruise running an OS75 pair plus a
  Workhorse publishes two families, not three.

Across the series that is **187 windows and 277 figures for 42 cruises** — 21
publishing one sonar, 20 two and 1 three — averaging 3.4 days per window. At
**97 MB** it sits beside the Antarctic gallery's 518 MB and CalCOFI's 124 MB,
for a published total of **739 MB**, leaving about 285 MB under the 1 GB
ceiling GitHub Pages puts on a published site. A full rebuild takes roughly
half an hour.

One cruise is worth knowing about. **SR2206 publishes only its WH300**: both
OS38 databases fail the ensemble-count health test, the sonar having been down
for most of a six-day cruise, so a 300 kHz Workhorse reaching ~80 m is all
there is. Every cruise in the series now resolves to
`availability: "available"` — TN310 was the one exception, `"unavailable"` with
the reason `no measured track record`, until its databases arrived on
2026-09-18; it publishes five `os75nb` windows.

```bash
cd ../../science/technical_sadcp
conda run -n py_ddt python scripts/make_epac_web_gallery.py \
    --cruise TN320 --dry-run          # plan only, nothing written
conda run -n py_ddt python scripts/make_epac_web_gallery.py --dry-run
conda run -n py_ddt python scripts/make_epac_web_gallery.py
```

As with the other two galleries, a `--cruise`-filtered run preserves the
manifest records of every cruise outside the filter, `prune_cruise_assets()`
removes what a cruise no longer publishes, and the manifest is
`schema_version: 3` with the same row shape. Validate with `python3 -m
json.tool data/epac_webpy_gallery.json >/dev/null`, then preview over HTTP.

The dry run reports the planned window and figure totals before anything is
written, which is the cheap way to check the size budget: at the 393 kB per
figure the CalCOFI gallery measured, 277 figures predicted ~107 MB against the
97 MB actually produced.


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

- `projects[]` — top-level programs (currently `"antarctic"`, `"calcofi"` and `"epac"`). Each project has `id`, `color`, `map_center`, `map_zoom`, and a `cruises[]` array. **A project gets its own nav tab automatically** — `initSite()` builds the project tabs from this array, so nothing has to be added to the markup. `epac` carries no branding images, which the card and hero layouts fall back gracefully on.
- `cruise.track` — array of `[latitude, longitude]` pairs (negative = S/W) forming the map polyline.
- `cruise.stations` — array of `{lat, lng, label}` objects for individual markers.
- `cruise.images[].filename` — basename only; file must exist at `images/<filename>`.
- `cruise.status` — one of `"processed"`, `"archived"`, `"submitted"`, `"in_review"`, `"pending"`, `"nav_only"`. The vocabulary is closed and lives in three places that must agree: the `statusBadge` map, the `.status-caption` definition list and the filter `<select>` options. `"nav_only"` means the ship track survives but the velocity databases do not — it is deliberately not `"processed"`, which promises the data is available in house on request. The Eastern Pacific project uses `archived` where an accession exists, `submitted` otherwise and `in_review` for SR2212 alone (processing complete, pending final manual review); it never uses `processed`. `cruise_status()` in `tools/build_epac_cruises.py` is the only place that decides this, with `IN_REVIEW` naming the exception. **No row carries `nav_only` any more** — TN310 was the only one and its databases arrived on 2026-09-18 — and no row has ever carried `processed` or `pending`, so those three are vocabulary the portal can render rather than statuses in use. They stay in all three places in `index.html`: dropping one would make the next cruise in that state a three-place edit instead of a one-word one.
- `cruise.jasadcp_url` — optional; renders a purple "JASADCP" button in the data table when present.
- `cruise.track_key` — links the cruise to its measured track in `data/drake_passage_tracks.json` or `data/calcofi_tracks.json`. When it resolves, the measured track replaces `cruise.track` on the map and the row becomes clickable.
- `cruise.CODAS_dbs` — the CODAS database directories the cruise was built from; the table is expected to stay in step with these loads.
- `cruise.sac_id` / `cruise.sac_ids` — the JASADCP (NODC/UH SAC) cruise id of the primary database, and one `{sac_id, sonar}` entry per submitted database. `jasadcp_url` is `https://uhslc.soest.hawaii.edu/sadcp/DATABASE/<sac_id>.html`. Cruises processed in house and not yet submitted have none of these — the Antarctic series from 2019, the CalCOFI series from 2017.
- `cruise.calcofi_cruise` — CalCOFI only: the programme's own name for the cruise (`2107SR` — year, month, ship), which is how CalCOFI indexes the hydrography and plankton data from the same stations.
- `project.plots_link_label` — names the external plot page a cruise row links to *beside* its generated CODAS gallery. Set to `"Atlas"` on CalCOFI, where `cruise.plots_url` is the 2008 CalCOFI ADCP Digital Atlas page of objectively mapped velocity at 50 m and 100 m, which the section figures do not replace. Which cruises have one is read from the atlas's own cruise index, committed at `input_info/harvest/calcofi_all_cruise.htm` — 39 of the 55. Left unset (Antarctic), an external `plots_url` is shown only for cruises with no generated gallery.
- `cruise.ncei_accession` — the bare NCEI accession number behind `ncei_url` (`https://www.ncei.noaa.gov/archive/accession/<n>`). For the recent CalCOFI cruises the numbers come from `input_info/harvest/Cryosat Accessions.xlsx`, the group's own submission record; four of the fifteen in-house cruises are archived (OC1911A `0316807`, RL2001 `0314048`, RL2101 `0314054`, RL2302 `0314049`, each verified against its NCEI ISO landing page by ship and date range), and the other eleven — SH1704, SR1717, SR1808, SR1815, SR2004, SR2008, SH2103, SR2105, SR2112, SH2204, SR2211 — are listed in that spreadsheet with a blank accession, meaning not yet submitted. The accessions are **not** a contiguous block and cannot be guessed by range — `0314051` is an RRS Discovery North Atlantic cruise, `0314047` is a Ryofu Maru III GO-SHIP leg, `0314055` is a Himawari-9 SST granule. The eleven were searched for exhaustively and are genuinely unarchived: **R/V Sally Ride and NOAA Ship Bell M. Shimada do not appear in the JASADCP ship inventory at all** (`http://uhslc.soest.hawaii.edu/sadcp/ship.html`), so none of the SR/SH cruises can have reached NCEI through an old JASADCP batch; R/V Oceanus *is* indexed there but its inventory stops at OC1610A in October 2016.

  **How to search the archive exhaustively.** Each ship's page has a companion `.inv` plain-text inventory (`.../sadcp/INVNTORY/<ship>.inv`, 72 of them, 2,561 rows covering the whole 718-cruise database) listing SAC id, project, dates, position range and the `cruise:sonar` name. Download them all and grep — that is a complete search of JASADCP in one pass, and far better than reading the HTML pages one at a time. Match on the cruise stem as well as the full name, because the archive writes `rb1702_leg2:os75bb` where a local load is `RB1702_leg2`, and one submitted cruise becomes one SAC id *per sonar*. Map a SAC id to its accession with `scripts/resolve_jasadcp_ncei_accessions.py` (below), or — faster when you only need one — grep its page cache for `href="<sac>/"`.

  **Result of that search, September 2026.** Of the 37 cruises in the spreadsheet with a blank accession, **15 are in fact archived, all in accession `0223175`** — the JASADCP batch `ADCP_to_NCEI_202012`, which holds 156 SAC directories spanning 02430–02585: KM1606, MGL1115, MV1218, ps1240, ps1307, rb1401, rb1402, RB1702_leg2, RB1703_leg1, RR1610, tn188_calib, tn188_transit, tn189_glued, tn320 and tn340 (34 SAC ids in total, each verified present in the accession's own directory listing). None of the 15 is a portal cruise, so `site_data.json` is unchanged; the table is written to `input_info/harvest/cryosat_accessions_resolved.csv` for merging back into the spreadsheet. The remaining 22 — every SR and SH cruise, plus mv1104, SKQ2014, TN265, TN310, TN411, OC1911X, RR1710 and RR2105 — are in neither JASADCP nor NCEI. NCEI's own JASADCP-to-accession mapping page (`.../global-ocean-currents-database/jasadcp/ncei_accns.html`) now 404s, as expected — it went with the GOCD. Re-check the spreadsheet when cruises are submitted.

  **Three corrections to that search, found while building the Eastern Pacific
  project (September 2026).** The paragraph above is wrong on three points, and
  the spreadsheet columns written from it are wrong the same way:

  - **SKQ2014 *is* archived.** It is in the JASADCP inventory as
    `skq201400l601`, SAC 02549 and 02550, which the accession map puts in batch
    `0223175`. `reports/checks/jassearch.py` missed it because its match
    pattern ends in `(?![A-Za-z0-9])` and the archive's cruise name continues
    `...2014` with a `0`. So the batch holds **16** of the spreadsheet's cruises,
    not 15, over 36 SAC ids. Any future search of that inventory should match a
    cruise stem as a prefix, not as a whole token.
  - **KOK1607 is archived and has a database on disk.** It is SAC 02518
    (`kk1607:wh300`), and `jas_repo_complete/02518` holds it, so it is a
    published Eastern Pacific cruise rather than a metadata-only row.
    **KOK1605** is absent from the archive — there is no `kk1605` anywhere in
    the 2,569-cruise inventory — but it does have a complete `wh300` load
    inside `uh_repo/tarballs/kok1605_seaflow.tar.gz`, and so does **TN265**
    (`TN265_seaflow.tar.gz`, os75bb + os75nb). Both are now published; see the
    Eastern Pacific tracks section. **TN310** was the only cruise in the list
    with no database anywhere, until `TN310.tar.gz` appeared in the same
    directory on 2026-09-18; it is absent from the archive too, so it is
    published as an in-house load.
  - **Nine cruises have per-cruise JASADCP accessions that post-date the
    batch**, found by searching NCEI's geoportal for the title template
    "Current velocity profiles taken by shipboard ADCP" (the `Soares` search).
    Each was matched on platform plus the exact date range in the accession
    title and confirmed against the cruise's measured extent — 0317530's
    bounding box, for instance, is RB1702_leg2's track to three decimals. Seven
    are Eastern Pacific cruises and are recorded in
    `input_info/harvest/epac_ncei_accessions.csv`: PS1240 `0317755`, PS1307
    `0317754`, RB1402 `0317532`, RB1702_leg2 `0317530`, RB1703_leg1 `0317533`,
    OC1911X `0317756`, RR2105 `0317531`. The other two are **CalCOFI** cruises
    that `site_data.json` still records as processed-but-not-submitted:
    **SR1717 `0317529`** and **SR1808 `0317528`**. Those two are noted at the
    foot of that CSV and have deliberately *not* been applied — they belong to
    the other project's rows.

  These are the JASADCP route, not a third-party holding: 0317529's cited
  authors are Dan Schuller (UCSD) and Julia Hummon (UH) with JASADCP named as a
  collaborating organisation, so they mean the same thing `0223175` does and are
  appropriate as `ncei_accession`. Where a cruise has both, the portal links the
  per-cruise accession — it lands on that cruise's own package rather than on a
  156-directory batch — and the cruise note says the data is archived twice.

  **Still not archived anywhere**, after searching both the JASADCP ship
  inventories and NCEI: MV1104, RR1710, SR2006, SR2204, SR2206, TN265, TN310,
  TN411, and the three `my_codas_proc` cruises **RR2104, SR2007 and SR2212**.
  The live `rrevelle.inv` ends at SAC 02548 (rr1610, September 2016) and
  `thompson.inv` at 02560 (tn340, April 2016), and Sally Ride is absent from the
  ship inventory altogether — so there is nothing newer in JASADCP for these
  ships. Note the ASCII inventory for Revelle is `rrevelle.inv`, not
  `revelle.inv`. These eleven carry `status: "submitted"` in the portal (with
  SR2212 `in_review`), so their rows say the data went to the repository and
  no accession has come back yet — do not read the absence of an accession as
  an absence of a submission.

  **The spreadsheet now records all of this.** `input_info/Cryosat Accessions.xlsx` (and its committed copy under `harvest/`) gained four columns — `SAC IDs (JASADCP)`, `JASADCP accession`, `NCEI link` and `Archive status (resolved Sept 2026)` — filled for all 58 rows; the untouched original is kept beside it as `Cryosat Accessions (pre-merge original).xlsx`. Fifteen blank `Accession #` cells were filled from the JASADCP batch and their `Comment` set to `Published`, which is one of the three values column D's own dropdown allows — anything else would break the validation, which is why the explanatory text went into a new column instead. Five rows that already carried an accession turn out to be archived **twice**, once directly and once through JASADCP (at26_26, km1415, km1416, km1417, MGL1703), so their existing `Accession #` was left alone and the JASADCP copy recorded separately. Accessions stored as floats (`314052.0`) were normalised to `0314052`. The merge is `reports/checks/merge_xlsx.py`, which rewrites only `sheet1.xml` and its relationships and copies every other part of the workbook byte for byte, so the styles, the drawing and the dropdown survive.

  Separately, NOAA's OMAO ship-data pages *do* list cruise records matching SH1704, SH2103 and SH2204 by date (e.g. cruise `332220170319`, 2017-03-19 to 2017-04-20, project "CalCOFI - Spring"), and there is an OMAO ADCP accession `0279675` for a July 2019 Shimada leg. These are NOAA's own underway ADCP holdings, **not** this lab's processed CODAS submission, so they are deliberately not used as `ncei_accession` — that field means "where this portal's processed data is archived". Note these four were written into `site_data.json` by hand, because `tools/build_calcofi_cruises.py` needs `calcofi_cruises.json` and `jasadcp_ncei_accessions.json` from `../../science/technical_sadcp/`, which are not present — a regeneration without them would drop the links. JASADCP submissions up to ~2018 were archived in batches, so many cruises share one accession; from 2019 each Drake Passage season has its own. `../../science/technical_sadcp/scripts/resolve_jasadcp_ncei_accessions.py` rebuilds the SAC-id-to-accession mapping by walking the NCEI archive directories (NCEI's own mapping page went with the GOCD when it was decommissioned in April 2025).
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
- `TRACKS` — measured tracks keyed by `site_id`, merged from every file in `TRACK_FILES` (three of them now); `trackFor(cruise)` / `hasTrack(cruise)` resolve a cruise against it. Cruise ids are unique across the projects, which is what lets the files share one index — and it is why `select_epac_dbs.py` emits upper-case site ids: `read_db_list()` upper-cases the second column, so a mixed-case `RB1702_leg2` in the selection would never join its `RB1702_LEG2` track record.
- `WEBPY_GALLERY` — section-figure manifests keyed by cruise id, merged from every file in `WEBPY_GALLERY_FILES`. `hasCodasGallery(projId)` says which projects have one (`CODAS_GALLERY_PROJECTS`), and `galleryProjId` tracks whose gallery DOM is on screen, since the ids are `gallery-<project>`; a selection is dropped when the project changes. `webpyBadge()` / `webpyTileText()` label each tile from the row's `section_count`, dates and `section_bbox`, and `setGallerySonarColumns()` gives the grid one column per published sonar (`sonars-2`, `sonars-3`) so each row is one window read across its sonars.
- `plotsLinks(p, cruise, track)` — the Plots links of a cruise row and of its coverage drawer: the gallery button, plus the external `plots_url` when the project sets `plots_link_label`, otherwise the button replaces it.
- `coverageFourthStat(t)` — the drawer's fourth stat card, the one thing that differs by series: 60°S crossings where the track record carries `n_drake_crossings`, depth at 50% coverage where it carries `deepest_50pct_m`.
- `navTo(id, el)` / `isProjectId(id)` — the nav bar. The project tabs are built by `initSite()` from `SITE.projects` and each carries `data-nav="<id>"`; `navTo` finds the tab to activate by that attribute and asks `isProjectId()` whether to route to `showProject` or `showSection`. All three used to be hard-coded to the first two projects — a positional map (`{home: 0, antarctic: 1, calcofi: 2, docs: 3}`) for the popstate case, an `id === 'antarctic' || id === 'calcofi'` test for the routing, and, worst, a second nav updater inside `showProject` that lit whichever tab's text contained "antarctic" for anything that was not CalCOFI. That last one is why a third project's tab looked wrong even when the routing was right, and it fires from the hero buttons and the calibration table too, not only from `navTo`.
- **Every cruise track is visible when a project page opens.** Three places agreed on the old default of the 2000 season alone (the chip's `checked` state, `lg.addTo(map)` in `initProjectMap`, and a `setCruisesYear(p.id, '2000')` call), which left both projects that have no year-2000 cruise with an empty map. The chip bar now defaults to on, every `LayerGroup` is added, and the year buttons and `None` narrow it from there. Once the map exists it is the authority (`map.hasLayer(lg)`), so re-rendering the bar keeps the user's selection.
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

## Accessibility

The portal is a UC public-facing site, so it is held to **WCAG 2.1 Level A and
AA** by the DOJ's ADA Title II rule (28 CFR Part 35); the Title II compliance
date is **26 April 2027**. Two rules follow from that and are easy to undo by
accident:

- **A control is a `<button>` or an `<a href>`, never a `<div onclick>`.** The
  portal's interactive surface is built by JavaScript, and a click handler on a
  `<div>`, `<span>` or `<tr>` is invisible to the keyboard. So the coverage
  control in the Data Access cell, the gallery tiles, the year-group
  disclosures, the lightbox close and the two in-popup actions are all real
  buttons, and the logo is a real link. Mouse-only conveniences layered *on
  top* of a keyboard route are fine — the `<tr data-track onclick>` row click
  and the Leaflet track click both duplicate the row's Coverage button, which
  is why they may stay as they are. A control that is the *only* route to
  something must be focusable.
- **A toggle that is a checkbox still has to answer to Enter.** A checkbox
  responds to Space and ignores Enter; the cruise chips read as "show this
  cruise on the map", and keyboard users reach for Enter first and conclude the
  control is broken. The global `keydown` handler turns Enter on a chip
  checkbox into a toggle plus a `change` event. The control stays a checkbox —
  that is the right role for one of a few hundred independent on/off choices,
  and it is what a screen reader announces; this only widens how it can be
  operated.
- **A control that hides its own input must clip it, not remove it.** The
  cruise chips are a `<label>` wrapping a checkbox; `display: none` on that
  checkbox (the original styling) took a few hundred map toggles out of the tab
  order and the accessibility tree at once. The chip clips the box instead
  (`position:absolute; clip:rect(0 0 0 0)`) so it still focuses and still
  announces its state. The pill is a `<span class="chip-pill">` rather than the
  label itself, so the focus ring is drawn by `input:focus-visible +
  .chip-pill` — a plain sibling selector with no `:has()` dependency, tracing
  the pill's own rounded shape. `.cruise-chips` needs its padding and
  `scroll-padding`: it is a `max-height` scroll box, and without them the ring
  on the first or last visible row is clipped, which reads as "tabbing does
  nothing".

Other pieces worth not regressing: the `.skip-link` is the first focusable
element and moves focus to `<main id="main" tabindex="-1">` in script rather
than navigating, because a bare `#main` hash jump pushes a stateless history
entry and `popstate` reads a null state as "go to Overview" (see 33af5c4); one
global `:focus-visible` rule provides the focus ring, with a pale-teal override
for controls on `--navy` surfaces, and nothing may set `outline: none` without
replacing the indicator; `setYearExpanded()` is the only writer of the
year-group disclosure state, because that state lives in three places (the
tbody class, the header class and the button's `aria-expanded`) and both
`toggleYearGroup()` and `filterTbl()` change it.

### The palette is measured, not eyeballed

`tools/check_contrast.py` reads the tokens out of `index.html`'s `:root` block
and checks the 38 pairs the site actually renders — it exits non-zero on a
failure, so it can gate a commit. **Run it after touching any colour.**

```bash
python3 tools/check_contrast.py        # 38 pairs, 0 below threshold
python3 tools/check_contrast.py -v     # list the passes too
```

Two things it encodes that are easy to get wrong. First, a token has to clear
its threshold against *every* ground it lands on, which is why `--light` is
`#5c6d86` rather than something lighter: it reads on white at 5.27:1 but the
table headers sit on `--sand`, where it is 4.67:1. Same for `--teal`, which is
both link text on white and the ground under white button text — one value has
to serve both, and `--teal-hover` exists because `--teal-lt` under white text
was 2.2:1.

Second, **`--border` and `--border-ui` are not interchangeable.** `--border`
(`#d6dfe8`) is a decorative rule between rows. `--border-ui` (`#7789a1`) is the
visible boundary of something you can click or type into, which 1.4.11 holds to
3:1. A new input, select, chip or outline button takes `--border-ui`.

A project's identity colour is a third case. `project.color` is picked to read
on a map basemap, and `#c9832e` is only 3.10:1 on white — so map tracks, legend
dots and accent bars keep the identity colour (1.4.3 governs text, not
graphics) while anything rendering it *as type* goes through `textSafe()` in
`index.html`, which darkens it until it clears. `tint()`/`text_safe()` in the
checker mirror that function; if one changes, change both.

### Headings, names and announcements

Three more contracts, all verifiable:

- **Each view has exactly one `h1` and its outline never skips a level.** The
  view's own title is the `h1` (`.sec-title` on the project and Documentation
  pages, the hero heading on Overview); each `.panel-title` and each
  `.info-panel` heading is an `h2` under it; things nested inside those are
  `h3`. `.sec-title` pins `font-weight: 400` because it is a heading now and
  would otherwise come out bold in the serif face.
- **Every `<th>` declares a `scope`.** The calibration table is the one that
  matters: its sticky first column is a `<th scope="row">`, which is why the
  sticky-top rule is scoped `.cal-tbl thead th` — an unscoped `.cal-tbl th`
  would make every row header try to stick to the top as well.
- **Anything that silently changes a result count is a live region.** The
  cruise table (`#tbl-count-<proj>`), the gallery count and `.cal-count` all
  carry `role="status"`; `filterTbl()` tallies matches and writes the count,
  and clears it when nothing is filtered so the region does not nag.

The three filter controls carry `aria-label` (a placeholder is not a name).

### Overlays, titles and the rest

- **Both overlays are modal dialogs.** `role="dialog" aria-modal="true"` with a
  label, focus moved in on open and returned to the opener on close
  (`openOverlay()` / `closeOverlay()`), and `trapTab()` keeping Tab inside.
  The closed drawer takes `visibility: hidden` — `aria-hidden` alone left it
  rendered and focusable off-screen, so a keyboard user tabbed into controls
  screen readers had been told did not exist. The `visibility` transition is
  delayed by the slide duration so the animation still plays.
- **Each view sets `document.title`.** `setTitle()` runs from `showSection()`
  and `showProject()`; the four views are separate history entries and separate
  bookmarks, so they cannot share one title (2.4.2).
- **New-window links are decorated by a `MutationObserver`,** not at each
  render site. `markExternalLinks()` adds `rel="noopener noreferrer"` and a
  visually-hidden "(opens in a new window)" to any `a[target="_blank"]`; the
  portal rebuilds large blocks of HTML as you navigate, so remembering to call
  it everywhere would not have survived.
- `prefers-reduced-motion: reduce` neutralises the smooth scrolling and the
  drawer slide; a `max-width: 620px` block stacks the header, which used to
  overflow a 320px viewport (1.4.10); and the map legend distinguishes a track
  from a station by shape (`.leg-line` vs `.leg-dot`) as well as colour (1.4.1).

**Every blocking, serious and moderate finding from the September 2026 audit is
now closed.** Re-verify with `python3 tools/check_contrast.py` and a tab-through
with the mouse unplugged before changing any of the above.
