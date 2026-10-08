#!/usr/bin/env python3
"""Copy CalCOFI objective-map images from a legacy-site clone into a deploy clone.

Dry-run first, then apply:

    python3 copy_calcofi_atlas_images.py /path/to/legacy-site /tmp/adcp-portal --dry-run
    python3 copy_calcofi_atlas_images.py /path/to/legacy-site /tmp/adcp-portal --apply

The legacy source is read-only. Images are copied to
images/calcofi-atlas/<year>/<cruise>/ in the deployment clone.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


IMAGE_DEPTHS = (50, 100)


def atlas_assets(site_data):
    calcofi = next(
        (project for project in site_data.get("projects", [])
         if project.get("id") == "calcofi"),
        None,
    )
    if calcofi is None:
        raise ValueError("site_data.json has no CalCOFI project")

    for cruise in calcofi.get("cruises", []):
        plots_url = cruise.get("plots_url") or ""
        path = urlsplit(plots_url).path
        match = re.search(r"/calcofi/(.+)/([^/]+)\.html?$", path, re.IGNORECASE)
        if not match:
            continue

        directory = PurePosixPath(match.group(1))
        if directory.is_absolute() or ".." in directory.parts:
            raise ValueError("Unsafe CalCOFI plots_url: " + plots_url)
        stem = match.group(2).lower()
        relative_directory = Path(*directory.parts)

        for depth in IMAGE_DEPTHS:
            filename = "{}_{}_oa.jpg".format(stem, depth)
            relative_path = relative_directory / filename
            yield cruise.get("id", stem), relative_path


def source_candidates(source_root, relative_path):
    return (
        source_root / "calcofi" / relative_path,
        source_root / relative_path,
        source_root / "images" / "calcofi" / relative_path,
        source_root / "images" / "calcofi-atlas" / relative_path,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="read-only legacy-site clone containing CalCOFI map JPEGs")
    parser.add_argument("deploy", type=Path, help="deployment clone containing site_data.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="copy images; default is dry-run")
    mode.add_argument("--dry-run", action="store_true", help="list planned copies without writing")
    args = parser.parse_args()

    source_root = args.source.expanduser().resolve()
    deploy_root = args.deploy.expanduser().resolve()
    if source_root == deploy_root:
        parser.error("source and deployment directories must be different")
    if not source_root.is_dir():
        parser.error("legacy source directory does not exist")
    site_data_path = deploy_root / "site_data.json"
    if not site_data_path.is_file():
        parser.error("deployment directory must contain site_data.json")

    try:
        site_data = json.loads(site_data_path.read_text(encoding="utf-8"))
        plan = []
        missing = []
        for cruise_id, relative_path in atlas_assets(site_data):
            destination = deploy_root / "images" / "calcofi-atlas" / relative_path
            candidates = source_candidates(source_root, relative_path)
            source = next((candidate for candidate in candidates if candidate.is_file()), None)
            if source is None and destination.is_file():
                continue
            if source is None:
                missing.append((cruise_id, relative_path))
            else:
                plan.append((cruise_id, source, destination))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error("could not build copy plan: " + str(error))

    print("Atlas images to copy:", len(plan))
    for cruise_id, source, destination in plan:
        print("  {}: {} -> {}".format(cruise_id, source, destination))
    if missing:
        print("Atlas images not found in the legacy source:", len(missing))
        for cruise_id, relative_path in missing:
            print("  {}: {}".format(cruise_id, relative_path))

    if not args.apply:
        print("Dry run only. Pass --apply to copy the listed files.")
        return 0
    if missing:
        print("Nothing copied: resolve missing source images, then rerun.", file=sys.stderr)
        return 1

    for _, source, destination in plan:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(destination))
    print("Copied {} CalCOFI objective-map images.".format(len(plan)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
