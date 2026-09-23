# Consented Local Identity Pipeline

## Routing Principle

Use this pipeline only for the user or an explicitly authorized recognizable performer. It solves identity consistency locally; it is not a prompt trick for a Seedance upload scan.

Project state:

```yaml
identity_mode: consented_local_identity
generation_backend: photomaker_v2 | pulid_flux | liveportrait | consisid
seedance_eligible: false
```

Identity-independent locations, props, wardrobes, abstract inserts, and background/action plates may remain Seedance-eligible. Record hybrid composition sources in the manifest.

## Backend Matrix

| Backend | Best use | Input | RTX 3060 12GB route | License note |
|---|---|---|---|---|
| PhotoMaker V2 | default identity-consistent stills, outfits, scenes, views | multiple identity photos preferred | supported around the documented 11GB minimum | Apache-2.0 code |
| PuLID-FLUX | single-photo fallback, stronger prompt editability | one identity photo | official 12GB/FP8/offload route | Apache-2.0 code |
| LivePortrait | close-up animation, blink, speech, expression, small turns | source portrait + driving video/template | Windows/NVIDIA practical | MIT code; default InsightFace models have noncommercial constraints |
| ConsisID | full identity-preserving local text-to-video | identity image + prompt | enable CPU offload, VAE slicing/tiling; slow experimental mode | Apache-2.0 code |
| InfiniteYou | cloud/high-memory expansion | identity reference | local 12GB route not recommended; optimized use remains about 16GB | keep as future extension |

Model code licenses do not automatically grant rights to third-party checkpoints, face detectors, or training data. Record the exact downloaded model and its license in commercial workflows.

## Photo Intake

Prefer 3–5 authorized photos:

- frontal neutral;
- left/right three-quarter;
- stable lighting and no heavy filter;
- no occluding sunglasses or hands;
- adequate face resolution;
- avoid mixing ages, hairstyles, makeup states, or multiple people unless those differences are intentional.

Hash and register each input. Keep originals outside generated outputs. A generated identity sheet must cite its source asset IDs.

## Still Workflow

1. `local_identity_adapter.py probe`.
2. Create a `character` asset with `seedance_eligible=false`.
3. Register authorized input photos in `v001`.
4. `recommend --task still --reference-count N`.
5. Build a job JSON with prompt, source paths, expected output, hardware profile, and license warnings.
6. Run the selected repository manually or through an explicitly ready launcher.
7. Verify identity, anatomy, clothing, and view accuracy.
8. Register accepted outputs and compose three-/six-view boards.

PhotoMaker is the default on 12GB. Use PuLID when a single reference or prompt editability performs better. Do not silently swap a local authorized identity for a synthetic face.

## Portrait Animation

LivePortrait is suitable for:

- talking-head dialogue;
- blinking and subtle gaze shifts;
- expression transitions;
- small head turns.

Use a high-quality accepted portrait as source and a licensed driving video/template. It is not the default for full-body locomotion, complex camera travel, or large occlusions.

## Full Video

ConsisID is optional and slow on 12GB:

- CPU offload;
- VAE slicing;
- VAE tiling;
- reduced concurrency;
- explicit output and job logs;
- no fabricated completion path if generation fails.

Use it only when full identity-preserving local video is more important than speed.

## Hybrid Seedance Workflow

When complex environment motion is needed:

1. generate a background/action plate without recognizable identity dependence;
2. create local identity stills/animation for the authorized performer;
3. composite or edit in a local post pipeline;
4. register plate, identity render, masks, and composite as separate asset versions;
5. document which system generated each layer.

Do not attach a `seedance_eligible=false` face asset to a Seedance shot. Preflight treats that as an error.

