# Critique: the joined model against every solved photo

Phase 6 tool. For each solved photo it renders the model's visible outline through the solved camera, finds the wood's
edge next to it in the photo, and stores the signed gap in mm. Then it turns those gaps into a ranked list of places
where the model misses the wood. It measures only and never changes the model.

**Sign:** + means the model sticks out beyond the wood. − means the model lies inside the wood.

## Rerun for a later model

```
tools/py.sh -t 30 tools/critique/measure.py parts/model_vN.glb work/critique/vN           # ~100 s, peak ~0.9 GB
work/toolkit/rk.sh tools/critique/stats.py work/critique/vN work/critique/vN_stats.json   # held-out list: holdout.json
python3 -I tools/critique/items.py work/critique/vN_stats.json work/critique/vN_items.json
python3 -I tools/critique/report_json.py work/critique/vN_stats.json work/critique/vN_items.json reports/critique_vN.json \
    work/critique/shift_*.json
tools/py.sh tools/critique/fig_rank.py work/critique/vN_items.json figures/critique/ranked_vN.png
```

To compare a fix, rerun on the new model and look at the same region keys in both reports. The held-out medians count
most, because no fix was tuned on those photos.

## The scripts

| file | does |
|---|---|
| `common.py` | loads the GLB (one part can be shifted for the self-test), classifies the outline edges, builds the render mesh |
| `measure.py` | per photo, one at a time: painter's render (part id + depth), outline points every 3 mm, edge search, gap. Status codes are in its docstring |
| `stats.py` | per region and side: median over photos, spread, se; symmetric (L+R)/2 and antisymmetric (L−R)/2; tolerance; rank |
| `items.py` | merges neighbouring out-of-tolerance stretches of one edge into fix items and names whose file would fix each |
| `report_json.py` | writes the committed summary `reports/critique_vN.json` |
| `holdout.json` / `holdout.py` | the fixed held-out list: 15 of 93 photos, one per view sector. Do not regenerate it |
| `shift_check.py` | self-test: run `measure.py --shift PART DX DY DZ` on a few photos, then check that the gaps move by the shift |
| `fig_rank.py`, `fig_overlay.py` | the overview chart, and the single-photo check of one stretch (`--near X Y Z --radius R --pxmm 10`) |

## Region key

A region key is `MEMBER|kind|edge|stretch`.

- **MEMBER** is the left/right pair or the halved part: ARM, FLEG, BLEG, ROCKER, SLAT_LR, SEAT, CREST, SLAT_C.
- **kind** is `sil` (silhouette against the background) or `crease` (a visible sharp edge between two lit faces). Only
  silhouettes are ranked. A crease on an eased arris is a tone edge that moves with the light.
- **edge** names the classes of the edge's two faces in the part's mirrored frame. For example, `bottom/outer` is the
  outer bottom arris. A single word means a silhouette across a smooth face.
- **stretch** is 50 mm of y, z or |x|.
