## Plan: Search-Friendly Static Data Pages

Prepare SEO and indexing support for the future `adcp.ucsd.edu` deployment without changing the existing interactive portal behavior. The site is not yet ready for institutional deployment, so separate repository work that can be implemented and validated locally from production activation that must wait for UCSD/SIO hosting. Keep `index.html` as the interactive application, add stable crawlable project/cruise documents generated from `site_data.json`, and emit matching JSON-LD metadata from the same source data. The intended public identity is UCSD / Scripps Institution of Oceanography / Chereskin Lab.

**Steps**
1. **Separate preparation from deployment**
   - Record `https://adcp.ucsd.edu/` as the intended production origin, but do not require DNS, HTTPS, redirects, or domain ownership during repository implementation.
   - Make the site origin configurable in the generator and templates, for example `--origin https://adcp.ucsd.edu/` for production artifacts and `--origin http://localhost:8000/` for local preview.
   - Use relative internal links where possible so local pages work without pretending that `localhost` is the canonical public site.
   - Confirm the UCSD/SIO institutional wording, preferred logo/image assets, citation language, and whether NCEI/JASADCP links are the authoritative distribution URLs before production release.
   - Keep local `python3 -m http.server` preview working throughout; do not submit the local preview to search engines.

2. **Prepare crawl/indexing foundations** (*implementable before deployment*)
   - Extend the current `<head>` in `index.html` with a concise description, configurable canonical URL, Open Graph metadata, Twitter card metadata, and an appropriate `theme-color`.
   - Add a root-level `robots.txt` template whose production form points to `https://adcp.ucsd.edu/sitemap.xml`; document that it should be published only with the intended public deployment.
   - Add a generated `sitemap.xml` containing the home page, project pages, and every valid cruise page URL. Exclude `admin.html`, internal fallback-only states, and duplicate query/hash URLs.
   - Add a stable social/share image only if an actual asset is available; do not reference missing image files.
   - Keep `href="#"` behavior in the current application unchanged during this phase, or replace it only with event handlers that call `preventDefault()` and preserve the existing section navigation.

3. **Define a canonical page model and generator** (*implement and test locally before deployment*)
   - Add a small generation script outside the browser runtime, using `site_data.json` as the source of truth and `data/drake_passage_tracks.json` as optional enrichment.
   - Generate stable pages at `/antarctic/`, `/calcofi/`, and `/antarctic/{cruise-id}/` or `/calcofi/{cruise-id}/`; verify that the eventual institutional host can serve these directory-style URLs before release.
   - Normalize identifiers and URL segments consistently, and detect duplicate IDs, missing required fields, invalid links, and track-key mismatches before writing output.
   - Generate pages into a clearly separated output directory or deployment artifact so generated files do not overwrite `index.html`, `admin.html`, `site_data.json`, or track data.
   - Include breadcrumbs, title, description, dates, vessel, region, PI, instrument/sonar, status, data links, citation, and related project/cruise links as ordinary HTML.
   - Include measured-track summaries only when the referenced track exists; label records without measured tracks honestly rather than inventing values.
   - Use descriptive image `alt` text and omit image markup when the referenced asset is unavailable.

4. **Preserve and connect the existing interactive experience**
   - Leave `initSite()`, `showProject()`, `buildProjectHTML()`, `initProjectMap()`, `focusCruise()`, coverage charts, layer toggles, and gallery behavior in `index.html` intact unless a small link integration is required.
   - Add visible links from the generated pages back to the interactive portal, with project/cruise context passed through a non-breaking mechanism such as a hash or query parameter.
   - If deep-linking is added to `index.html`, parse the URL only after `loadData()` finishes, then call existing `showProject()` / `focusCruise()` functions. Do not initialize maps twice; preserve `mapsInitialized` and the deferred Leaflet initialization.
   - Ensure a generated page remains useful if JavaScript is disabled, while the interactive portal remains the richer map experience when JavaScript is available.
   - Avoid moving the existing map into generated pages in the first implementation. That would duplicate Leaflet state, increase page weight, and create a second interaction path likely to drift from the current one.

5. **Add dataset structured data**
   - Emit JSON-LD on the home page for the portal/collection and on each project/cruise page using `Dataset` where the page describes an identifiable data resource.
   - Populate JSON-LD from the same normalized record used for visible HTML: name, description, identifier, URL, creator/publisher, temporal coverage, spatial coverage, variable/instrument context where appropriate, citation, and distribution URLs.
   - Use UCSD/SIO and Chereskin Lab organization names consistently and avoid claiming ownership, licensing, or permanent accession status unless the data record supports it.
   - Do not place JSON-LD only in the client-side DOM after page load; it must be present in the generated HTML response.
   - Validate generated JSON-LD with Schema Markup Validator and Google Rich Results Test, treating warnings separately from errors.

6. **Deployment and institutional integration** (*blocked until hosting is ready*)
   - Confirm the UCSD/SIO hosting layout, DNS ownership, HTTPS certificate, redirect policy, and whether generated files should be deployed beside the current source files or from a separate build artifact.
   - Configure the web server or institutional hosting to serve generated pages, `robots.txt`, `sitemap.xml`, and assets with correct content types and UTF-8 encoding.
   - Add redirects from any previous public URL variants to `https://adcp.ucsd.edu/` where UCSD/SIO controls them.
   - Ensure the deployment includes `site_data.json`, `data/drake_passage_tracks.json`, and the image directory without exposing unintended administrative or source-only files.
   - Only after DNS/HTTPS is live, add the portal to Google Search Console and Bing Webmaster Tools, verify the domain property, and submit the sitemap.
   - After deployment, seek authoritative links from the SIO/UCSD lab page, NCEI records, JASADCP records, relevant project pages, and publications.

**Relevant files**
- `/home/smullersoares/projects/software/adcp_ucsd/index.html` — preserve current runtime app; add head metadata using the intended production origin without making deployment a prerequisite, and add optional deep-link parsing only after data loading.
- `/home/smullersoares/projects/software/adcp_ucsd/site_data.json` — single source for visible metadata, page text, identifiers, links, and dataset structured data.
- `/home/smullersoares/projects/software/adcp_ucsd/data/drake_passage_tracks.json` — optional measured-track and coverage enrichment for generated cruise pages.
- `/home/smullersoares/projects/software/adcp_ucsd/CLAUDE.md` — document the generator command, output/deployment layout, canonical domain, and verification workflow.
- `/home/smullersoares/projects/software/adcp_ucsd/robots.txt` — new production indexing policy/template; do not enable public indexing before deployment is ready.
- `/home/smullersoares/projects/software/adcp_ucsd/sitemap.xml` or its generated deployment output — new crawl map; prefer generated output to avoid stale URLs.
- `A new generator script, location to be chosen during implementation` — produces project/cruise HTML, sitemap, and JSON-LD from the data files, with a configurable `--origin` for local versus production artifacts.
- `A generated output directory, location to be chosen during implementation` — contains crawlable pages and must not replace the existing application source files.

**Verification**
1. Validate `site_data.json` and track JSON before generation; fail generation on malformed JSON, duplicate page IDs, missing required identifiers, or invalid internal links.
2. Run the generator twice with a local origin and confirm deterministic output, stable URLs, and no unrelated source-file modifications.
3. Start `python3 -m http.server` from the generated local output root and verify the home page, both project pages, representative cruise pages, `robots.txt`, and `sitemap.xml` return successfully.
4. Use browser smoke tests to confirm existing overview navigation, project navigation, map pan/zoom, track hover highlighting, track click behavior, layer toggles, coverage drawer, gallery/lightbox, and external links still work.
5. Verify that hovering or panning the map does not change document scroll position; only intentional cruise selection may scroll to the map.
6. Test generated pages with JavaScript disabled: titles, descriptions, identifiers, links, breadcrumbs, and citations must remain available.
7. Inspect the raw local HTML response, not only the post-rendered DOM, to confirm descriptions, social metadata, and JSON-LD are present; confirm canonical URLs are configurable and correct for the selected origin.
8. Validate JSON-LD with Schema Markup Validator and Google Rich Results Test using generated artifacts before deployment; submit the sitemap in Search Console only after production deployment.
9. Check mobile layout, keyboard focus, accessible names, image alt text, and absence of accidental `noindex` directives locally; check HTTPS, redirects, and production canonical consistency after hosting is live.

**Decisions**
- Scope is limited to recommendations 2, 4, and 5: indexing metadata/foundations, crawlable stable pages, and dataset structured data. Backlink outreach and broader performance work are deployment follow-ups, not prerequisites for the implementation.
- `https://adcp.ucsd.edu/` is the intended production canonical origin, but the site is not yet ready for DNS, hosting, or search-engine activation.
- Repository implementation must support a local preview origin such as `http://localhost:8000/` without presenting it as the production canonical site.
- DNS, HTTPS, redirects, Search Console/Bing verification, sitemap submission, and institutional backlinks are post-deployment tasks.
- The current interactive `index.html` remains the primary application and is not replaced by static pages.
- `site_data.json` remains the authoritative content source; generated pages are derived artifacts.
- No server-side application or database is required for the first version.
- Pages for records with incomplete scientific metadata must expose the known state rather than filling gaps with guessed content.
- `admin.html` is excluded from the public sitemap and should not become an indexed dataset page.

**Further Considerations**
1. Decide whether generated pages should live beside the current root files, under a `pages/` directory with hosting rewrites, or in a separate deployment directory. Recommendation: use a generated `public/` artifact only if the hosting workflow can deploy it reliably; otherwise generate directly into stable `antarctic/` and `calcofi/` directories while keeping source files untouched.
2. Decide whether deep links should restore a selected project/cruise inside `index.html`. Recommendation: add this only after static pages work, using `history.replaceState` or a hash without changing existing map initialization.
3. Confirm the official SIO/UCSD organization name, institutional logo/share image, data license, and preferred citation before adding them to JSON-LD.
4. Before deployment, confirm the final institutional hosting contract, URL rewrites, DNS/HTTPS ownership, and whether production metadata should use absolute `https://adcp.ucsd.edu/` URLs or be resolved by the host.
