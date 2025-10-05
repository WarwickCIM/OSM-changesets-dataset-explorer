#!/usr/bin/env python3
"""
dev.py — one-stop CLI for OSM-hashtag-explorer

Uses your existing scripts as-is (no rewrites):
  - reset_database_connection.py (optional)
  - make_database.py
  - extract_hashtags.py
  - get_users.py
  - update_database.py

The builder expects these filenames in the working directory:
  - changesets-latest.osm.bz2
  - osm_changesets.duckdb

You can pass --infile / --db to point to other paths, we will create a symlink
(or copy, if symlinks are not available) to those expected names before running.
"""

from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# scripts (relative to repo root)
SCRIPTS = {
    "reset": "reset_database_connection.py",
    "make": "make_database.py",
    "extract": "extract_hashtags.py",
    "users": "get_users.py",
    "update": "update_database.py",
}

EXPECTED_INFILE = "changesets-latest.osm.bz2"
EXPECTED_DB     = "osm_changesets.duckdb"


def _exists_script(key: str) -> Path | None:
    p = REPO_ROOT / SCRIPTS[key]
    return p if p.exists() else None


def _ensure_named_file(src: Path, dest_name: str, workdir: Path) -> Path:
    """
    Ensure a file named dest_name exists in workdir by linking or copying from src.
    Returns the path to workdir/dest_name.
    """
    target = workdir / dest_name
    if target.exists():
        # already correct name, do nothing
        return target
    if not src.exists():
        raise SystemExit(f"Missing required file: {src}")

    # Try symlink first and fall back to copy on platforms without perms.
    try:
        target.symlink_to(src)
    except Exception:
        shutil.copy2(src, target)
    return target


def _run_py(script: Path, workdir: Path):
    print(f"\n> Running: {script.name}")
    proc = subprocess.run([sys.executable, str(script)], cwd=workdir)
    if proc.returncode != 0:
        raise SystemExit(f"{script.name} failed with exit code {proc.returncode}")


def cmd_make(args):
    workdir = REPO_ROOT
    # Map alternate input/output paths to expected names
    infile = Path(args.infile).resolve() if args.infile else (workdir / EXPECTED_INFILE)
    dbfile = Path(args.db).resolve() if args.db else (workdir / EXPECTED_DB)

    #Ensure expected names for scripts that read constants
    _ensure_named_file(infile, EXPECTED_INFILE, workdir)
    # For DB (output), if an alternate location is provided, we copy any existing DB to expected
    #name before build and copy back after, otherwise scripts will create at expected name.
    db_expected = workdir / EXPECTED_DB
    if args.db:
        if db_expected.exists():
            db_expected.unlink()
        #if you want a fresh rebuild, delete the external file first. here we just let scripts create
        pass

    # 1) reset (optional)
    reset = _exists_script("reset")
    if reset:
        _run_py(reset, workdir)

    # 2) make_database
    _run_py(REPO_ROOT / SCRIPTS["make"], workdir)

    # 3) extract_hashtags
    _run_py(REPO_ROOT / SCRIPTS["extract"], workdir)

    # 4)get_users (materialized tables/views)
    _run_py(REPO_ROOT / SCRIPTS["users"], workdir)

    # If user asked for a different DB path, copy the built DB back out
    if args.db:
        shutil.copy2(db_expected, Path(args.db))

    print("\nFull build complete.")


def cmd_update(args):

    print("\n > Running incremental update. Please ensure the changeset file to update the database is small. Maximum a months worth of changestes. Otherwise it would be quicker to remake the database on full changes.")
    workdir = REPO_ROOT
    #Ensure expected names exist in workdir
    if args.infile:
        _ensure_named_file(Path(args.infile).resolve(), EXPECTED_INFILE, workdir)
    if args.db:
        #If you pointed to an external DB, bring it into expected name first
        _ensure_named_file(Path(args.db).resolve(), EXPECTED_DB, workdir)

    # reset (optional)
    reset = _exists_script("reset")
    if reset:
        _run_py(reset, workdir)

    # incremental update
    _run_py(REPO_ROOT / SCRIPTS["update"], workdir)

    # If external DB was used, copy it back to the given path
    if args.db:
        shutil.copy2(workdir / EXPECTED_DB, Path(args.db))

    print("\n Incremental update complete.")


def cmd_stats(args):
    workdir = REPO_ROOT
    # Minimal DuckDB stats via a tiny inline Python
    py = r"""
import duckdb, sys
db = sys.argv[1] if len(sys.argv) > 1 else 'osm_changesets.duckdb'
con = duckdb.connect(db, read_only=True)
tot = con.execute('select count(*) from changesets').fetchone()[0]
mn, mx = con.execute('select min(created), max(created) from changesets').fetchone()
try:
    ht = con.execute('select count(*) from changeset_hashtags').fetchone()[0]
except Exception:
    ht = None
try:
    u = con.execute('select count(distinct uid) from changesets where uid is not null').fetchone()[0]
except Exception:
    u = None
print(f'DB: {db}')
print(f'changesets: {tot:,}')
print(f'created: {mn} -> {mx}')
print(f'hashtag rows: {ht if ht is not None else "(table missing)"}')
print(f'distinct uids: {u if u is not None else "(n/a)"}')
"""
    db = args.db if args.db else str((workdir / EXPECTED_DB))
    proc = subprocess.run([sys.executable, "-c", py, db], cwd=workdir)
    if proc.returncode != 0:
        raise SystemExit("stats failed")


def build_parser():
    p = argparse.ArgumentParser(description="Dev entry point for OSM-hashtag-explorer")
    sub = p.add_subparsers(dest="cmd", required=True)

    # fresh build
    m = sub.add_parser("make", help="Fresh build: make_database -> extract_hashtags -> get_users (reset first if present)")
    m.add_argument("--infile", help="Path to changesets-latest.osm.bz2 (optional)")
    m.add_argument("--db", help="Path to osm_changesets.duckdb (optional)")
    m.set_defaults(fn=cmd_make)

    # incremental update
    u = sub.add_parser("update", help="Incremental update: update_database.py (reset first if present)")
    u.add_argument("--infile", help="Path to changesets-latest.osm.bz2 (optional)")
    u.add_argument("--db", help="Path to osm_changesets.duckdb (optional)")
    u.set_defaults(fn=cmd_update)

    #quick stats
    s = sub.add_parser("stats", help="Quick DB stats (counts, min/max dates)")
    s.add_argument("--db", help="Path to osm_changesets.duckdb (optional)")
    s.set_defaults(fn=cmd_stats)

    return p

def main():
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
