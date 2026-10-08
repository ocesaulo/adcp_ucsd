#!/usr/bin/env python3
"""Prune a disposable clone to the files needed by the HTTP-served portal.

Run this script from the source checkout and pass a separate clean clone:

    python3 trim_files_for_deployment.py /tmp/adcp-portal --dry-run
    python3 trim_files_for_deployment.py /tmp/adcp-portal --apply

The generated CODAS gallery PNGs and thumbnails are retained. This does not
build images; it preserves the static assets that the website displays.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


DATA_FILES = {
    "data/antarctic_webpy_gallery.json",
    "data/calcofi_tracks.json",
    "data/calcofi_webpy_gallery.json",
    "data/calibrations.json",
    "data/drake_passage_tracks.json",
    "data/epac_tracks.json",
    "data/epac_webpy_gallery.json",
}
ROOT_FILES = {"index.html", "site_data.json", ".nojekyll"}
ROOT_DIRS = {"data", "images"}
HARDCODED_IMAGES = {"branding/adcp-instrument.gif"}


def add_image_reference(references, value):
    if not isinstance(value, str) or not value:
        return
    if value.startswith(("http://", "https://", "data:")):
        return

    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe image path in site data: " + value)
    parts = path.parts[1:] if path.parts[:1] == ("images",) else path.parts
    if parts:
        references.add(PurePosixPath(*parts).as_posix())


def collect_image_references(root):
    references = set(HARDCODED_IMAGES)
    site_data = json.loads((root / "site_data.json").read_text(encoding="utf-8"))

    for project in site_data.get("projects", []):
        for key in ("header_image", "logo", "illustration_image"):
            add_image_reference(references, project.get(key))
        for cruise in project.get("cruises", []):
            for image in cruise.get("images", []):
                add_image_reference(references, image.get("filename"))
            if project.get("id") == "calcofi":
                url_path = urlsplit(cruise.get("plots_url") or "").path
                match = re.search(r"/calcofi/(.+)/([^/]+)\.html?$", url_path, re.IGNORECASE)
                if match:
                    directory = PurePosixPath(match.group(1))
                    if directory.is_absolute() or ".." in directory.parts:
                        raise ValueError("Unsafe CalCOFI plots_url: " + cruise["plots_url"])
                    stem = match.group(2).lower()
                    for depth in (50, 100):
                        add_image_reference(
                            references,
                            "calcofi-atlas/{}/{}_{}_oa.jpg".format(
                                directory.as_posix(), stem, depth
                            ),
                        )

    for name in (
        "antarctic_webpy_gallery.json",
        "calcofi_webpy_gallery.json",
        "epac_webpy_gallery.json",
    ):
        manifest = json.loads((root / "data" / name).read_text(encoding="utf-8"))
        for cruise in manifest.get("cruises", []):
            for plot in cruise.get("plots", []):
                add_image_reference(references, plot.get("image"))
                add_image_reference(references, plot.get("thumbnail"))

    return references


def files_below(directory):
    if not directory.is_dir():
        return []
    return [path for path in directory.rglob("*") if path.is_file()]


def remove_empty_directories(directory):
    if not directory.is_dir():
        return
    for path in sorted(
        (item for item in directory.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        try:
            path.rmdir()
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clone", type=Path, help="separate, disposable Git clone")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="delete unneeded files; without this option, only show the plan",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="show the pruning plan without deleting anything (the default)",
    )
    args = parser.parse_args()

    root = args.clone.expanduser().resolve()
    source_root = Path(__file__).resolve().parent
    if root == source_root:
        parser.error("refusing to prune the checkout containing this script")
    if not (root / ".git").is_dir():
        parser.error("target must be a standalone Git clone with a .git directory")
    if not (root / "index.html").is_file() or not (root / "site_data.json").is_file():
        parser.error("target does not look like the ADCP portal repository")

    for name in DATA_FILES:
        if not (root / name).is_file():
            parser.error("required runtime data file is missing: " + name)

    try:
        image_references = collect_image_references(root)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error("could not read runtime image references: " + str(error))

    image_root = root / "images"
    data_root = root / "data"
    image_files = files_below(image_root)
    data_files = files_below(data_root)
    images_to_remove = [
        path for path in image_files
        if path.relative_to(image_root).as_posix() not in image_references
    ]
    data_to_remove = [
        path for path in data_files
        if path.relative_to(root).as_posix() not in DATA_FILES
    ]
    root_to_remove = [
        path for path in root.iterdir()
        if path.name not in ROOT_FILES and path.name not in ROOT_DIRS
    ]
    missing_images = sorted(
        name for name in image_references if not (image_root / name).is_file()
    )

    print("Target clone:", root)
    print("Referenced image files to keep:", len(image_references) - len(missing_images))
    print("Unreferenced image files to remove:", len(images_to_remove))
    print("Unneeded data files to remove:", len(data_to_remove))
    print("Unneeded root entries to remove:", ", ".join(sorted(p.name for p in root_to_remove)) or "none")
    if missing_images:
        print("Image references already missing from this clone:")
        for name in missing_images:
            print("  images/" + name)
    if not args.apply:
        print("Dry run only. Pass --apply to prune this clone.")
        return 0

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ).stdout
    if status.strip():
        parser.error("refusing to prune a clone with tracked or untracked changes")

    for path in images_to_remove + data_to_remove:
        path.unlink()
    remove_empty_directories(image_root)
    remove_empty_directories(data_root)

    for path in root_to_remove:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    print("Pruned clone. Kept index.html, site_data.json, .nojekyll, runtime data, and referenced images.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
