# Critique, pass 1: model v22 against every solved photo

This is phase 6, pass 1. It measures and ranks only; it changes nothing in the model.

- **Tools:** `tools/critique/` (see its README).
- **Data:** `reports/critique_v22.json`.
- **Figures:** `figures/critique/`.
- **Sign everywhere:** **+ means the model sticks out beyond the wood; − means the model lies inside the wood.**

## How it measures

1. **Find the outline points.** For each of the 93 solved photos (one decoded at a time):
   - Render the joined `parts/model_v22.glb` through the solved camera, with lens distortion. The render is a painter's render of part id and depth at half resolution. All 23 parts are drawn, so the Dominos and every other part hide what they hide.
   - Take each wooden part's outline every 3 mm. That means its silhouette edges, plus visible sharp edges (creases) over 30°.
   - Keep a point only if the render shows its own part inside and nothing outside for 1.0–5.5 mm along the image normal. This drops edges seen against another part.
   - Also drop a point where the edge runs within 25° of the line of sight, where the photo has under 1.5 px/mm, or where the search band reaches within 4 mm of the table.
2. **Find the wood edge.** Sample the photo in Lab colour along the outward normal, from −5 to +5 mm at 0.1 mm steps, averaged over ±1.5 mm along the edge. Take the strongest colour step, refined to sub-pixel with a parabola.
   - On a silhouette, the colour step only counts where the colour moves *away* from that part's own wood colour going outward. That colour is the part's median 2–5 mm inside, in that photo.
   - Reject the point if the contrast is under 10, if there is a second peak at 0.7 or more of the best at least 1 mm away, or if the peak sits at the end of the band.
3. **Store the gap.** The signed gap is in mm at the part, measured square to the line of sight. Each point is stored with its 3D position on the part.
4. **Summarise.** For each region (member × silhouette/crease × edge × 50 mm stretch) and side:
   - Each photo gives the median of its points. The region's value is the median over photos, with spread = 1.4826 × MAD.
   - **Symmetric part** = (L+R)/2. This is what the symmetric model can fix, and it is what gets ranked.
   - **Antisymmetric part** = (L−R)/2. This is the chair's own asymmetry. It is reported, not ranked.
   - **Tolerance:** 0.8 mm where most points lie within 20 mm of another part (joints and hard points); 1.6 mm on free curves.
   - **Ranking:** by |symmetric| / tolerance, using silhouettes only and non-held-out photos only.
   - Neighbouring stretches of one edge that are out of tolerance, have the same sign and lie beyond 2 standard errors are merged into one **item** (`items.py`).

**Photos.** 93 solved photos.
- 15 are held out on a fixed, committed list (`tools/critique/holdout.json`). It has one photo per 30° view sector, plus high and low views on each side.
- Of the remaining 78, 76 give points. IMG_1494 and IMG_1556 give none.
- Each region reports the held-out median next to the main value.

**Run.** 99 s, peak memory 0.88 GB, about 1 s per photo. 2.25 M outline candidates; 0.57 M clean in the render; 0.39 M measured.

## Sanity checks

**1. Known-good parts come back small** (symmetric part, mm):

| part, PR | stretch | symmetric | antisymmetric | held-out |
|---|---|---|---|---|
| arm underside, outer edge (#27/#28) | y 200 / 250 / 300 / 350 | −0.07 / +0.03 / +0.13 / −0.16 | +2.1 to +2.8 | −0.6 / −0.5 / −1.0 / +0.2 |
| rocker bottom, outer edge (#29) | y −500 … +50 (11 stretches) | −1.16 … +0.52, median −0.48 | −0.1 to −2.2 | mostly within ±1.3 |
| rocker bottom, outer edge (#29) | y 300 … 600 | −1.41 … −0.01 | +0.1 to +1.1 | |
| rocker tail end (#23) | outer/back y −500; bottom y −450/−500 | +0.73; +0.31 / +0.52 | | +1.96; +0.17 / +0.79 |
| rocker nose end (#23) | outer/front y 600 | −1.27 | +0.03 | −0.20 |
| seat side edge, top (#30) | y 50 … 400 | −1.44 … +0.93 | −0.9 to +0.05 | |

What these show:
- **Arm.** The arm's large antisymmetric part is the known lean: the left arm's underside sits higher than the right one in the photos. The design is the L/R mean, so its symmetric part is near zero, which is what PR #27/#28 claimed.
- **Rocker tail.** The tail's top/outer edge reads +0.7 to +1.8 at y −300…−100, against a bottom of about −0.7. Together that means the whole tail sits about 1 mm lower than the model at the same height. This matches PR #29's open note that the absolute bottom may be 0.7 mm high.
- **Seat side.** All seat-side stretches fall within the 1.6 mm free-curve tolerance.

**2. Shift test** (`shift_check.py`). One part was moved 2 mm and the photos were rerun. The gaps should move by the shift projected on each point's measuring direction.

| moved | photos | kind | points | median measured / expected | residual (mm) | within 0.5 mm |
|---|---|---|---|---|---|---|
| right arm, +2 mm up | 12 | silhouette | 856 | 0.995 | −0.01 ± 0.05 | 84% |
| right arm, +2 mm up | 12 | crease | 620 | 0.994 | −0.01 ± 0.04 | 92% |
| right rocker, +2 mm in x | 14 | silhouette | 6616 | 0.980 | −0.03 ± 0.09 | 91% |
| right rocker, +2 mm in x | 14 | crease | 3277 | 1.001 | −0.00 ± 0.03 | 94% |

The least-squares slope is 0.67–0.82. A few points snap to a different edge after the move (6–16% fall outside 0.5 mm), and those pull the slope down. The robust ratio is 1.0. Because of these outliers, the report uses medians at every step.

**3. By eye** on single photos (`figures/critique/`). The photos give only 2.4–4 px/mm at the part (the orbit was shot from about 1 m), so each crop is enlarged to 10 px/mm. No photo of these stretches is natively at 10 px/mm.

| figure | what it shows |
|---|---|
| `top_back_leg_foot_IMG_1503.jpg` | Back-leg foot. On both side edges the model's outline lies in the background, about 1.5 mm outside the wood each side. The foot is about 3 mm narrower than the model. The found edges are the real, crisp wood edges. |
| `top_front_leg_back_edge_IMG_1519.jpg` | Front leg, z 250–450. One edge reads about +3, the other about −2: the model sits to one side of the wood rather than being too thick. In the stats, the back edges are − and the front edges + (items 8, 18, 23). Rejected (orange) points sit where the wrench and a light board meet the edge. |
| `top_rocker_inner_IMG_1562.jpg` | Rocker, inner bottom edge. The rocker's shaded inner face shows as a dark band, and the model's outline falls inside it (−2 to −3). The opposite edge in the same photo reads +2.5, so in this one photo part of the gap is the camera's own error. The per-photo spread here is large; see item 5. |
| `top_crest_bottom_front_IMG_1538.jpg` | Crest, bottom front edge between the slats. Only 4 points survive in this photo. Where the model's crest edge lies, the photo shows background (+4). The wood edge found may belong to the crest's rounded arris or to the slat meeting it. Low confidence. |
| `good_arm_underside_IMG_1558.jpg` | Arm underside, outer edge, y 250: the model is on the wood edge within about 0.5 mm along the whole stretch. |
| `good_rocker_bottom_IMG_1525.jpg` | Rocker bottom, outer edge, y 0: on the edge within about 0.5 mm. The table contact shadow is left out (grey). |

### Known traps and how each is handled

- **Eased arrises.** A rounded arris of radius r puts the true silhouette k·r inside the model's sharp corner. Each region reports k (`ease_k`, typically about 0.3), so a 3 mm round biases a region by about +1 mm. Creases (tone edges on eased arrises) are measured but not ranked.
- **Shadows under the chair.** No search band may come within 4 mm of the table (status 14). This rule was added after the first run showed the rocker bottom reading −2 at the contact shadow. On silhouettes, a colour step only counts going away from the part's own wood colour, so a shadow further out does not win. A second edge of similar strength rejects the point as ambiguous.
- **A dark face against a dark background.** Contrast under 10 Lab is rejected. Such points cluster on the rockers' shaded inner faces and under the seat; they appear as `low_contrast` counts in the JSON. Item 5 (rocker inner face) still has a large per-photo spread for this reason.
- **Reflections on the seat's front roll.** A highlight gives a second edge, so the point is rejected as ambiguous. In practice the roll's front silhouette (`SEAT front/back`) gives no measurements at all: 0 of 40,540 candidates. It is listed under blind spots below.
- **Slats seen through each other.** A silhouette is kept only if the render shows nothing for 1.0–5.5 mm outward, so a slat with another slat behind it is dropped (status 10). A crease is kept only where its own part shows on both sides and the depth agrees.

## Ranked items

These are silhouettes only, ranked by |symmetric| / tolerance. "Photos" counts photo-stretches. "One side" means only that side was measured well enough, so the value is that side's median and no antisymmetric part exists. The full list of 42 items is in the JSON, and the chart is `figures/critique/ranked_v22.png`.

| # | where | symmetric (mm) | antisymmetric | photos | held-out (median) | tolerance |
|---|---|---|---|---|---|---|
| 1–3, 9, 13 | **back-leg foot**, z 0–100, every edge | +2.1 … +4.1 | −0.1 … +0.8 (1, 2 one side) | 9 / 12 / 23 / 44 / 54 | +3.5, +2.9, +2.8, +2.3 | 0.8 |
| 4, 20 | front leg top, where it meets the arm (z 600–650) | +3.2 (R only), +1.5 | −0.9 | 9, 23 | +2.6, −0.2 | 0.8 |
| 5 | **rocker inner face, bottom edge**, y −250…+100 | −3.15 | −0.5 … +0.1 | 288 | −3.2 (7 stretches −1.8 … −3.6) | 0.8 |
| 6, 11 | **crest bottom**, front edge x 0–100, back edge x 50–250 | +2.9, +2.4 | −0.3, 0.0 … +0.6 | 21, 115 | +1.0, +1.1 | 0.8 |
| 7, 12 | front-leg foot z 50–100 (R only) | −2.9, −2.3 | — | 7, 9 | −3.0, −2.9 | 0.8 |
| 8 | **front leg, back edge**, z 150–600 | −2.7 (−1.8 … −3.9) | −0.2 … +0.9 | 201 | −3.5 (−2.1 … −4.3) | 0.8 |
| 10 | arm top, outer edge, y 0–50 (at the back leg) | −2.5 | −1.1 | 20 | −2.6 | 0.8 |
| 14 | **rocker inner face, top edge**, y −50…450 | −2.0 | −1.0 … +1.7 | 369 | −2.0 | 0.8 |
| 15 | seat top, back edge (slat line), x 0–200 | +1.8 | −0.9 … +0.1 | 75 | +1.4 | 0.8 |
| 16 | **seat front corner, outer side, y 500–550 (the PR #30 lead)** | −3.3 (R only) | — | 7 | −1.3 | 1.6 |
| 17 | rocker inner/outer, y −350 (L only) | −3.3 | — | 21 | −1.2 | 1.6 |
| 18, 23 | front leg, front edge, z 250–300 and 400–450 | +2.6, +1.6 | −0.3, −1.2 | 23, 29 | +3.5, +0.8 | 1.6 / 0.8 |
| 21, 38, 40 | **side slats, inner front edge**, z 450–550, 650–700, 850–1000 | +1.7, +1.8, +2.9 | −1.5 … −0.1 | 47, 27, 103 | +2.0 (top) | 1.6 |
| 22, 29 | arm underside, inner edge, y 50–100 and 400–450 | +1.4, +1.1 | −0.6, −0.4 | 41, 44 | +1.7, +0.1 | 0.8 |
| 24, 28 | seat front roll, underside edge, x 0–50 and 200–250 | −2.2, −2.5 | +0.3, +1.3 | 24, 21 | −3.8 | 1.6 |
| 26, 30, 36 | rocker top, nose y 450–650, middle y 200–300 | −2.1 … −2.2, −1.9 | −1.4 … −0.2 | 35–98 | −0.6 … −3.2 | 1.6 |
| 31, 35 | back leg, front and back edges, z 150–400 | +2.1, +1.9 | −0.8 … +0.9 | 115, 144 | +2.1, +1.8 | 1.6 |
| 33 | rocker tail top, y −500…−350 | +2.0 | −0.4 … −0.2 | 36 | +2.4 / −0.5 | 1.6 |

### The top items: where, how big, how sure, likely cause, whose file

1. **Back-leg foot (z 0–100): the model is about +2 to +4 mm too big on every edge. Sure.**
   - Evidence: the held-out photos agree (+2.3 to +3.5) and the overlay shows both side edges outside the wood. The narrowest stretches (items 1 and 2) are measured on the left only, with few photos. Items 3, 9 and 13 have both sides and 23–54 photos.
   - Likely cause: the real leg narrows (or is rounded off) at the foot where it enters the rocker, and the model carries its full section down to the rocker.
   - Owner: back-leg outline and feet belong to the **joinery session** (`tools/joinery.py` and the back-leg outline are frozen here). This goes to them as a request.
2. **Rocker inner face (items 5 and 14): the model's inner face lies 2–3 mm inside the wood, top and bottom edges alike, while the outer face fits (sanity table). Fairly sure.**
   - Evidence: the held-out stretches agree (−1.8 to −3.6). Per-photo values scatter widely, because the inner face is shaded and seen at 1.6–2.8 px/mm.
   - Likely cause: the rocker is thicker across than the model's 31 mm, by about 2–3 mm.
   - Owner: the **hub**, through the rocker block's thickness in `tools/build_model.py` (`parts/rocker_profile.json` does not change). Check with a caliper reading before moving anything.
3. **Front leg (items 8, 18 and 23): the back edge reads −2.7 (201 photo-stretches, held-out −3.5) and the front edge +1.6 to +2.6. Sure about the size.**
   - Likely cause: opposite signs on opposite edges mean the model's front leg sits about 2 mm *forward* of the wood, or is tilted. The leg is not the wrong thickness. The overlay on IMG_1519 shows both edges moved the same way.
   - Owner: leg placement belongs to the **joinery session**, so this is a request. If they find the placement right, the hub's front-leg outline is the other place to look.
4. **Crest bottom (items 6 and 11): +2.4 to +2.9 mm along both bottom edges. Less sure.**
   - Evidence: the held-out photos say only +1.0 to +1.1, and the points sit near the slat junctions.
   - Likely cause: the crest's lower edge in the model is about 2 mm too low, or its bottom arrises are rounded more than the model.
   - Owner: `parts/crest.json` is frozen, so this is a **doubt** for whoever owns the crest data.
5. **Side slats, inner front edge (items 21, 38 and 40): +1.7 to +2.9 mm, rising towards the top (z 850–1000, 103 photo-stretches, held-out +1.3 to +3.0). Sure.**
   - Likely cause: the slats are narrower, or turned more, near the crest than the model has them.
   - Owner: the **hub** (slats in `tools/build_model.py`).
6. **Seat front corner (item 16, the PR #30 lead).**
   - The outer side at y 500–550 reads −3.3 on the right only (7 photos, held-out −1.3).
   - The corner's top silhouette at y 500 reads −1.2 symmetric and +0.2 antisymmetric, within the 1.6 tolerance.
   - Taken point by point over the whole corner (|x| > 230, y 490–540), the per-photo medians scatter ±3 mm. The overall left median is −0.1 and the right −1.5. The left again reads higher, by about 0.7 mm per side, as PR #30 found.
   - Conclusion: the method **does not settle** whether the top rounds down over its last 16 mm. The corner is a compound curve seen against the front leg and the arm. It stays open and needs a tape or profile-gauge reading at y 500–530.
   - Owner: the **hub** (`tools/build_model.py` SEAT, `parts/seat_*.json`).

The other items above tolerance:
- **Hub-owned:** the seat's back top edge at the slats (+1.8), the seat roll's underside (−2.2 to −2.5), the arm underside's inner edge (+1.1 to +1.4), and the rocker top at the nose (−2.1) and tail (+2.0).
- **Joinery or frozen files:** the front-leg top at the arm (+3.2 / +1.5), the front-leg foot (R only, −2.3 to −2.9), the arm top at the back leg (`parts/arms.json`, −2.5), and the back leg at z 150–400 (+1.9 to +2.1).

## What this method cannot see or measure

Each blind spot below has many outline candidates and no (or almost no) measured points:

- **The seat's front roll from the front** (`SEAT front/back`, 0 of 40,540). Its silhouette lies against the legs, rockers and its own underside, and its highlights are ambiguous.
- **The seat's sides at the legs** (`outer/back`, `outer/inner`: 0 of 80,000) and the seat's top centre, x 0–150.
- **The joints themselves:** feet in the rockers, leg tops under the arms, the slats' ends in the seat and the crest, the crest ends, the arm ends, and the back leg above the crest (z 1000–1100). In these places another part touches the outline, so the clean-silhouette rule drops them by design. Joints are judged here only by the stretch next to them.
- **The crest's front (concave) face** (`CREST front`, 0 of 6,743) and its outer ends.
- **Faces seen flat-on:** the slats' front and back faces, the front leg's inner face, and the arm's inner, outer, top and bottom faces as smooth silhouettes. These have few or no silhouette points. Only their arrises are measured.
- **The rockers' flat middle,** top and bottom, y −300…+300, except at the arrises. The bottom at y 100–250 is also lost to the table rule.
- **Anything under the seat or between the rockers** that only shows in shadow, below 10 Lab contrast.
- **Creases are measured but not ranked:** they are tone edges and move with the light on eased arrises.
- **Sub-millimetre accuracy is not available.** The photos give 1.5–5 px/mm, the per-photo spread is typically 0.5–1.5 mm, and pose error moves single photos by 1–3 mm. Values near the 0.8 mm tolerance are not significant unless the held-out photos agree.
