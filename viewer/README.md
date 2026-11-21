# Model viewer

**Live: https://masterminnich.github.io/essick-rocker/** (GitHub Pages, serving `main`; the site root redirects here).

Plain static files, no server and no build. The page finds the newest model on its own by requesting `../parts/model_vN.glb`
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
