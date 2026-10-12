"""Download Spotify playlists as MP3 (via spotDL) and copy them onto Shokz headphones.

Usage:
    python sync.py              # download everything in playlists.txt, then copy to headphones
    python sync.py --no-copy    # only download
    python sync.py --drive E:   # copy to a specific drive instead of auto-detecting
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAYLISTS_FILE = HERE / "playlists.txt"
MUSIC_DIR = HERE / "music"
SYNC_DIR = HERE / ".sync"  # spotDL's per-playlist state, so re-runs only fetch new songs
SHOKZ_LABEL_HINTS = ("SWIM", "SHOKZ", "OPENSWIM")
KEYS_FILE = HERE / "spotify_keys.txt"  # your own Spotify app keys; the shared default ones get rate-limited


def read_keys():
    """Return [--client-id, ..., --client-secret, ...] from spotify_keys.txt, or [] if not set up."""
    if not KEYS_FILE.exists():
        return []
    keys = {}
    for line in KEYS_FILE.read_text(encoding="utf-8-sig").splitlines():
        name, sep, value = line.partition("=")
        if sep and not name.strip().startswith("#"):
            keys[name.strip().lower()] = value.strip()
    if keys.get("client_id") and keys.get("client_secret"):
        return ["--client-id", keys["client_id"], "--client-secret", keys["client_secret"],
                "--cache-path", str(SYNC_DIR / "spotify_token")]
    return []


def read_playlists():
    if not PLAYLISTS_FILE.exists():
        sys.exit(f"Missing {PLAYLISTS_FILE.name}. Add one Spotify playlist/album URL per line.")
    entries = []
    for line in PLAYLISTS_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    if not entries:
        sys.exit(f"{PLAYLISTS_FILE.name} has no playlists in it yet.")
    return entries


def sync_name(entry):
    if entry.lower() == "saved":
        return "liked-songs"
    match = re.search(r"(playlist|album|track|artist)/([A-Za-z0-9]+)", entry)
    return f"{match.group(1)}-{match.group(2)}" if match else re.sub(r"\W+", "_", entry)[:50]


def download(entry):
    SYNC_DIR.mkdir(exist_ok=True)
    save_file = SYNC_DIR / f"{sync_name(entry)}.spotdl"
    # Once a save file exists, spotDL syncs from it (adds new songs, removes ones taken off the playlist).
    query = str(save_file) if save_file.exists() else entry
    cmd = [
        sys.executable, "-m", "spotdl", "sync", query,
        "--save-file", str(save_file),
        "--format", "mp3",
        "--bitrate", "192k",
        "--output", str(MUSIC_DIR / "{list-name}" / "{artists} - {title}.{output-ext}"),
        "--threads", "2",  # gentler on YouTube for big libraries
    ] + read_keys()
    if entry.lower() == "saved":
        if not read_keys():
            print(f"\nSkipping Liked Songs: it needs your own Spotify keys in {KEYS_FILE.name} "
                  "(the shared default keys are almost always rate-limited). "
                  "See spotify_keys.example.txt.")
            return
        cmd.append("--user-auth")  # Liked Songs needs you to log in to Spotify in the browser
    print(f"\n=== Syncing {entry} ===", flush=True)
    subprocess.run(cmd, check=False)


def find_shokz_drive():
    """Return the root of a removable drive whose label looks like Shokz headphones."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Volume | Where-Object DriveLetter | ForEach-Object { \"$($_.DriveLetter)|$($_.FileSystemLabel)|$($_.DriveType)\" }"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    removable = []
    for row in out.splitlines():
        letter, label, kind = (row.split("|") + ["", ""])[:3]
        if kind.strip() != "Removable":
            continue
        if any(hint in label.upper() for hint in SHOKZ_LABEL_HINTS):
            return Path(f"{letter}:\\")
        removable.append((letter, label))
    if len(removable) == 1:  # only one USB drive plugged in: assume it's the headphones
        letter, label = removable[0]
        print(f"Using the only removable drive {letter}: ({label or 'no label'})")
        return Path(f"{letter}:\\")
    return None


def drive_path(arg):
    # Accept "E", "E:" or "E:\" as well as a full folder path.
    letter = arg.rstrip(":\\")
    return Path(f"{letter}:\\") if len(letter) == 1 else Path(arg)


def copy_to_drive(drive):
    copied = skipped = 0
    for src in sorted(MUSIC_DIR.rglob("*.mp3")):
        dest = drive / src.relative_to(MUSIC_DIR)
        if dest.exists() and dest.stat().st_size == src.stat().st_size:
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(drive).free
        if free < src.stat().st_size + 5_000_000:
            print("Headphones are full; stopping copy.")
            break
        print(f"Copying {src.relative_to(MUSIC_DIR)}")
        shutil.copy2(src, dest)
        copied += 1
    print(f"\nCopied {copied} new song(s) to {drive} ({skipped} already there).")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-copy", action="store_true", help="download only, don't copy to headphones")
    parser.add_argument("--no-download", action="store_true", help="copy already-downloaded songs only")
    parser.add_argument("--drive", help="drive letter of the headphones, e.g. E:")
    args = parser.parse_args()

    MUSIC_DIR.mkdir(exist_ok=True)
    if not args.no_download:
        for entry in read_playlists():
            download(entry)

    if args.no_copy:
        return
    drive = drive_path(args.drive) if args.drive else find_shokz_drive()
    if not drive or not drive.exists():
        print("\nHeadphones not found. Plug them in and run again (or pass --drive E:).")
        print(f"Your MP3s are in {MUSIC_DIR}")
        return
    copy_to_drive(drive)


if __name__ == "__main__":
    main()
