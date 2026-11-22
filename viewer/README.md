# Model viewer

**Live: https://masterminnich.github.io/essick-rocker/viewer/** (GitHub Pages, serving `main`; the site root redirects here).
Plain static files, no server and no build. Locally: `python3 -m http.server 8000` in the repo root, then open
http://localhost:8000/viewer/.

There are two pages:

- **The review app** (`index.html`, `review.js`, `review.css`, `scene.js`, `store.js`, `inches.js`): for the person checking the
  model against the real chair. Big type and big buttons, inches first. Three tabs:
  - **Look**: the chair in 3D (Front / Side / Back / Top / Corner; Solid, See-through, or *Next to a photo* with a wipe bar
    between the photo and the model drawn through that photo's solved camera). Tap a part: its sizes are listed on a card and
    drawn on the part as dimension lines (extension lines, arrows, a vermilion label with the row's number); tap a row to pick
    out its line. *Looks right* saves that; *Something is off here* drops a numbered pin and opens a note (Too thick / Too thin /
    Too long / Too short / Curve is wrong / Something else, free text, photos from the camera or library).
  - **Measurements**: one size at a time, drawn the same way, in three groups (we guessed / tape and photos disagree / from photos
    and tape) plus the slat-turn question. *Right*, *Wrong* or *Not sure*. *Wrong* opens a sheet: whole inches - / +, one row of
    eighths, *Finer* for + 1/16 and + 1/32, or type it (`1 7/8`, `1-7/8`, `1.875`, `47mm`, `4.7 cm`). *Print this list* prints a
    sheet with a picture of each size and a blank for the reading.
  - **Templates**: the printable templates in `templates/out/` (Letter tiles, one big sheet, DXF).
  - **My notes** lists everything given on this device; *Send to Joe* makes one file of it (share sheet, else a download).
  - Deep links: `#look`, `#measure`, `#measure/<dimension id>`, `#templates`, `#notes`. Every screen shows its ID
    (`er.look`, `er.look.part`, `er.look.note`, `er.look.photo`, `er.measure`, `er.measure.wrong`, `er.templates`, `er.notes`).
- **The workbench** (`workbench.html`, `app.js`, `style.css`, `cloud.js`): every older tool (orthographic views, click-to-measure,
  photo projected behind the model, measured points against the model). Reached from the small *Workbench* link, or
  `index.html?workbench`.

## Sizes shown in the review app: `parts/model_vN_dimensions.json`

Made by `tools/dimensions.py` (`tools/py.sh tools/dimensions.py --model 24`; `--check` prints the table without writing). Needs the
gitignored `work/parts/rocker{L,R}/o_plane.json` from the main checkout (found through git's common dir). Each entry:
`id`, `part` (mesh name), `name` (shop words), `kind` (`length` | `height` | `radius`), `p1`, `p2` (chair frame mm; for `height`
the line runs from `p1` straight down to the table; for `radius` p1 = p2 = the corner and 0 means sharp in the model), `value_mm`
(measured on the model), `source` (`taped` | `photos` | `guess`), `tolerance_mm`, `group`, `file` / `file_key` / `file_value_mm`
(the parts-file number it must agree with; `agrees_mm` is the difference), `mirror` (also drawn on the left twin, x -> -x),
`note` (where to put the tape), `reading` (the M-number in HUB_HANDOFF.md), `look_from` (direction the camera turns to).
`questions` holds yes/no questions (slat turn); `left_out` lists sizes with no honest end points on the model. The review app
uses the newest model that has a dimensions file, so a new model number needs this file re-made before the app shows it.

## Saving

All saving goes through `store.js`. Today everything stays on the device: IndexedDB database `essick-rocker-review`, stores
`records` (key `id`) and `photos` (key `id`, JPEG blobs downscaled on the device to about 1600 px on the long side). It survives
reloads; clearing the browser's site data deletes it, which is why *Send to Joe* exists.

Records (`type`):

| type | id | fields |
|---|---|---|
| `answer` | `answer-<dimension id>` (one per size; a new answer replaces it) | `dimId`, `name`, `verdict` (`right` / `wrong` / `unsure`), `value_mm` (the reader's size; for right/unsure the model's), `model_mm`, `typed` (the text typed, if any) |
| `question` | `question-<question id>` | `qid`, `name`, `choice` (`flat` / `turned` / `unsure`) |
| `note` | `note-…` | `n` (the pin number), `part`, `point` (chair frame mm, where the pin is), `camera` (photo key if left in *Next to a photo*), `what`, `text`, `photos` ([photo id]), `view` (camera direction) |
| `part_ok` | `ok-…` | `part` |

Every record also has `model` (`v24`), `at` (ms, first saved) and `updated`.

**Export file** (*Send to Joe*): `essick-rocker-notes-YYYY-MM-DD.json` =
`{ what, exported, model, device, records: [...], photos: { <photo id>: "data:image/jpeg;base64,..." } }`.

**Remote (off):** set `REMOTE_URL` in `store.js` to a small service (a Cloudflare Worker with KV + R2 would do) and every save is
also sent; anything not yet sent is retried on the next load. The service needs:

- `PUT {REMOTE_URL}/records/{id}`: JSON body = the record (without `synced`); store it under `id`, replacing any earlier copy. 2xx = saved.
- `PUT {REMOTE_URL}/photos/{id}`: body = the JPEG (`content-type: image/jpeg`). 2xx = saved.
- `DELETE {REMOTE_URL}/records/{id}`: the reader deleted it.
- CORS for the Pages origin (`https://masterminnich.github.io`), methods PUT and DELETE, header `content-type`.
- Nothing else is read back; the device stays the source of truth. Anyone with the URL can write, so keep it unlisted, or add a
  shared key in a header on both sides.

## The workbench
The workbench finds the newest model on its own by requesting `../parts/model_vN.glb`
with N counting up, and keeps checking every 20 s for the next version. A model therefore shows up about a minute after it reaches
`main` (the time GitHub takes to republish the site), and the page switches to it without moving the camera. The version line links to the
commit that brought the model in.

Locally: `python3 -m http.server 8000` in the repo root, then open http://localhost:8000/viewer/ (it shows the models in
your checkout's `parts/`, committed or not).

- **Views**: 3D orbit; square-on orthographic Front / Right / Left / Back / Top (click two points to measure, mm and inches);
  *Through a photo*, which draws the model through the solved camera of any of the 93 photos. This is exact at every depth.
- **Photo behind the model** (X / Y / Z planes): the most square-on photo for the side you are looking from is flattened onto a
  plane at the depth you set (GPU projective texturing through the solved camera). Wood at that depth lines up exactly;
  wood nearer or farther shifts by parallax, so slide the depth to the part you are checking.
- **Model**: opacity slider (0 = outlines only), outline toggle, parts on/off.
- **Measured points vs model**: the measured 3D points drawn in the scene, each coloured by its signed distance to the model
  that is showing (rust = inside the model, so the model is too big there; grey = on it; blue = outside, so the model is too
  small there). The rail shows the median distance, the 90 % figure and a per-part table (points, median, bias = median
  signed distance, 90 %), worst part first. Hover a dot for its distance, part, photo count and reprojection error; a line
  runs to the nearest model surface. Point sets: *Matched points* (`work/dense/chair_dense.npy`, tools/densify.py tracks),
  *Solve points* (the COLMAP solve's own points, off by default) and *Seat dots* (seat/dots.csv). Points farther than the
  *Hide past* distance from every part (default 25 mm) are left out of the figures and the picture, and so are the points of
  parts switched off. Distances are worked out in the browser (three-mesh-bvh) each time a model loads, so a new model needs
  no export. Inside/outside: ray parity for closed parts, the nearest face's normal for open ones (the seat). While the dots
  are coloured by distance the model is drawn in neutral grey so its part colours don't read as distance.

`viewer/photos/` is made by `tools/viewer_photos.py`: each photo undistorted, upright, resampled to a pinhole camera with the
principal point at the centre (1600 px), plus `cameras.json`. Re-run it only if the camera solve or photo set changes.
`viewer/cloud/` is made by `tools/viewer_cloud.py` (`tools/py.sh tools/viewer_cloud.py`): the three point sets in the chair
frame as small binary files plus `index.json`. Re-run it only when the dense cloud, the solve or the seat dots change.
`.nojekyll` in the repo root makes Pages publish the files as they are (no Jekyll pass).
