# Shokz Spotify Sync

Downloads Spotify playlists as MP3s (using [spotDL](https://github.com/spotDL/spotify-downloader), which finds each song on YouTube Music) and copies new songs onto Shokz OpenSwim headphones, which need local files because Bluetooth doesn't work underwater.

## Setup

```
pip install spotdl
python -m spotdl --download-ffmpeg
```

## Usage

1. Copy `playlists.example.txt` to `playlists.txt` and put Spotify playlist/album links in it, one per line. `playlists.txt` is git-ignored.
2. Plug in the headphones and run `Sync Shokz.bat` (or `python sync.py`).

Re-running only downloads new songs and only copies files that aren't already on the headphones.

| Option | What it does |
|---|---|
| `--no-copy` | Download only |
| `--no-download` | Copy already-downloaded songs only |
| `--drive E:` | Copy to this drive instead of auto-detecting the headphones |

## Liked Songs

Writing `saved` in `playlists.txt` downloads your Liked Songs, but it needs your own Spotify app keys (spotDL's shared keys are rate-limited). Copy `spotify_keys.example.txt` to `spotify_keys.txt` and follow the steps inside. `spotify_keys.txt` is git-ignored.

## License

[MIT](LICENSE)
