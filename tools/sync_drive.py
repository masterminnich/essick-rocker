"""USAGE: uv run --no-project --with gdown python sync_drive.py <folder_url> <dest_dir> <manifest.json>
Syncs a public Drive folder: lists files, downloads any not yet in the manifest,
and records id/name/size/sha1/first_seen. Re-run any time; prints NEW and REMOVED files."""
import sys, json, os, hashlib, datetime, gdown
url, dest, man_path = sys.argv[1:4]
os.makedirs(dest, exist_ok=True)
man = json.load(open(man_path)) if os.path.exists(man_path) else {"folder": url, "files": {}}
listing = gdown.download_folder(url=url, skip_download=True, quiet=True)
seen = set()
new = []
for f in listing:
    seen.add(f.id)
    rec = man["files"].get(f.id)
    out = os.path.join(dest, os.path.basename(f.path))
    if rec and os.path.exists(out) and os.path.getsize(out) == rec["size"]:
        continue
    try:
        gdown.download(id=f.id, output=out, quiet=True)
    except Exception as e:
        print("FAILED", f.path, e, flush=True); continue
    if not os.path.exists(out):
        print("FAILED", f.path, flush=True); continue
    h = hashlib.sha1(open(out, "rb").read()).hexdigest()
    man["files"][f.id] = {"name": os.path.basename(f.path), "size": os.path.getsize(out), "sha1": h,
                          "first_seen": datetime.date.today().isoformat()}
    new.append(os.path.basename(f.path))
    json.dump(man, open(man_path, "w"), indent=1)
removed = [r["name"] for i, r in man["files"].items() if i not in seen]
man["last_sync"] = datetime.datetime.now().isoformat(timespec="seconds")
man["listed_count"] = len(listing)
json.dump(man, open(man_path, "w"), indent=1)
print(f"listed={len(listing)} new={len(new)} removed_from_drive={len(removed)}")
for n in new: print("NEW", n)
for n in removed: print("REMOVED", n)
