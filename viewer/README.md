# Model viewer

`npm run dev` (no dependencies; PORT/HOST from the environment, default 127.0.0.1:8765) serves a browser viewer that always
shows the newest `parts/model_vN.glb`. It checks every 5 s and swaps the model in place when a new version is written.

- **Model folders**: `parts/` of this checkout, plus one path per line in `viewer/model-dirs.local` (git-ignored) and
  `ESSICK_MODEL_DIRS`. Point `model-dirs.local` at the working checkout's `parts/` to see a model before it is committed.
- **Views**: 3D orbit; square-on orthographic Front / Right / Left / Back / Top (click two points to measure, mm and inches);
  *Through a photo*, which draws the model through the solved camera of any of the 93 photos. This is exact at every depth.
- **Photo behind the model** (X / Y / Z planes): the most square-on photo for the side you are looking from is flattened onto a
  plane at the depth you set (GPU projective texturing through the solved camera). Wood at that depth lines up exactly;
  wood nearer or farther shifts by parallax, so slide the depth to the part you are checking.
- **Model**: opacity slider (0 = outlines only), outline toggle, parts on/off.

`viewer/photos/` is made by `tools/viewer_photos.py`: each photo undistorted, upright, resampled to a pinhole camera with the
principal point at the centre (1600 px), plus `cameras.json`. Re-run it only if the camera solve or photo set changes.
