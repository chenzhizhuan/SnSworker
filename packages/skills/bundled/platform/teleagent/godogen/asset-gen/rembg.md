---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '48965f44-f90d-4a31-9050-033054c765c1'
  PropagateID: '48965f44-f90d-4a31-9050-033054c765c1'
  ReservedCode1: '3d8b7ef9-08cf-4544-968e-240941052e5a'
  ReservedCode2: '3d8b7ef9-08cf-4544-968e-240941052e5a'
---

---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '582314a5-914a-49da-a02d-2ffbac1347d6'
  PropagateID: '582314a5-914a-49da-a02d-2ffbac1347d6'
  ReservedCode1: 'dea1dab2-e8a2-4384-aaac-1bd1c20f50da'
  ReservedCode2: 'dea1dab2-e8a2-4384-aaac-1bd1c20f50da'
---

# Background Removal

Matte a solid background out of an asset that needs transparency.

Applies to: characters, props, icons, UI, animated sprite frames.
Does NOT apply to: textures, backgrounds, 3D model references (Tripo3D needs the solid bg).

**Never prompt for a "transparent background" — the generator draws a checkerboard. Prompt a solid color, then remove it.**

## BG color strategy

Pick a prompt bg color that is (1) **distinct from the subject** so the mask separates cleanly, and (2) **close to the expected in-game environment** so residual fringe blends. Forest → `dark-green`; sky/water → `steel-blue`; dungeon → `dark-gray`; generic → `medium-gray`. Avoid pure chromakey (`#00FF00`) — it leaves unnatural fringing.

```
{name}, {description}. Centered on a solid {bg_color} background.
```

## CLI

Deps in `C:/Users/meepo/.config/TeleAgent/skills/godogen/asset-gen/tools/requirements.txt` (`pip install rembg[gpu,cli]`, or `rembg[cpu,cli]`). The script auto-detects CUDA and falls back to CPU with a warning.

```bash
# single image — always pass --preview
python C:/Users/meepo/.config/TeleAgent/skills/godogen/asset-gen/tools/rembg_matting.py img/car.png -o img/car_nobg.png --preview
# batch (video frames): BiRefNet loads once, bg sampled per-frame for color drift
python C:/Users/meepo/.config/TeleAgent/skills/godogen/asset-gen/tools/rembg_matting.py --batch frames/ -o clean/
```

## Modes

`-m auto` (default) selects by mask coverage:

| Mode | Auto when | Behavior |
|------|-----------|----------|
| `trust` | 5–70% mask fg | Keep all mask-fg pixels, aggressively remove bg |
| `adapt` | >70% mask fg | Adaptive threshold — fg pixels can be removed if bg-colored |
| `color` | <5% mask fg | Color matting only, no mask — rough fallback |

Output reports `BG color`, `Mask: fg=… (%)`, and the selected `Regime`. If the bg color is wrong (corners aren't bg) or `Transparent: 0`, regenerate the image with the subject centered on a solid bg.

## QA verification

Always pass `--preview` — it writes a `_qa.png` (the result composited on a contrasting color). the agent cannot judge transparency from a raw PNG; reading the `_qa` is the only reliable check. Delete it after inspection.

## Fixing results

- **Background remnants** → `--bg-thresh 0.03` (lower = more aggressive; also reduces fringing).
- **Missing foreground** → `-m trust`, or in adapt `--fg-thresh 0.30` (higher = more protective).
- **Fringing** (colored halo) → `-m adapt --fg-thresh 0.10`; if it persists, the bg is too close to the subject — regenerate with a more distinct color.

Tune `--bg-thresh`/`--fg-thresh` together. For batches, tune on one frame, then apply the flags to the whole set.

> AI生成

> AI生成