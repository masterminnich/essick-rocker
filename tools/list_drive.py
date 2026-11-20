"""USAGE: uvx --from gdown python list_drive.py <folder_url>
Lists files in a public Drive folder (names + ids) without downloading."""
import sys, json, gdown
files = gdown.download_folder(url=sys.argv[1], skip_download=True, quiet=True)
out = [{"id": f.id, "path": f.path} for f in files]
print(json.dumps(out, indent=1))
