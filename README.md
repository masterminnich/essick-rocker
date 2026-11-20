# essick-rocker

Rebuild an ESSICK sculpted rocking chair as a dimensionally accurate 3D model from phone photos and
hand measurements, then produce 1:1 printable part templates. Proof of concept for the method.

- Photos live in Google Drive (folder `1YgIhu9ZJOTl4V7alZy-BeoGzThgM7vd2`), not in git. `manifest.json`
  records each file's Drive id, size and sha1. Re-sync (prints NEW / REMOVED):
  `uv run --no-project --with gdown python tools/sync_drive.py "https://drive.google.com/drive/folders/1YgIhu9ZJOTl4V7alZy-BeoGzThgM7vd2" drive manifest.json`
- `drive/` (photos) and `work/` (derived images, COLMAP databases, scratch) are git-ignored.
- See `PLAN.md` for the method, decisions and conventions.
