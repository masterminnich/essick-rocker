"""Front-leg Domino across the leg face (hub, Joe's fix-list item 3). The scripts run from the repo root on the scratch folder
work/fdom/ (copy this folder's .py files there; data/ holds the committed inputs and results):
  1 tools/domino_ortho.py parts/model_v18_shapes.glb work/fdom/ortho 19 FLEG_R,FLEG_L ; cache.py (clean 0.1 mm/px orthos, planes.json)
  2 grid.py / shear.py: gridded straightened views to seed by eye -> data/seed_dom_*.json ; domfit.py -> data/dom_*.json (matched filter)
  3 measure.py LEG data/seeds_*.json OUT max -> data/m_*.json (arris edges per v-band) ; edgeview.py to check each reading on one photo
  4 analyse.py -> data/analysis.json (per photo and per leg) ; dcheck.py MODEL_PREFIX (model's Domino end vs its flat outer face)
  5 fig_overlay.py, fig_chart.py -> figures/front_domino/ ; cmp.py A.glb B.glb (part-by-part identity check)"""
