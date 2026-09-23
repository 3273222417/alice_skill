# Image Quality and Artifact Recovery

Use this reference when an image is noisy, grainy, blurry, pixelated, blocky, over-smoothed, or missing usable detail. Diagnose before rewriting the prompt.

## Classify the Failure

| Symptom | Likely cause | First action |
|---|---|---|
| Random colored speckles in shadows | digital/chroma noise | `clean_cinematic` quality lock; denoise if already rendered |
| Fine monochrome grain across the frame | explicit film/analog grain style | remove `film grain`, `grainy`, `Kodak`, `found footage`, and texture-overlay cues |
| 8x8 blocks, ringing, mosquito noise | JPEG/video compression | preserve as PNG; use SwinIR JPEG artifact reduction for existing media |
| Large square regions or mosaic | low-resolution source, aggressive compression, or model failure | regenerate from the clean source; restoration cannot recover factual missing pixels |
| Soft face but sharp clothing/background | face/detail allocation failure | closer face reference or crop; then CodeFormer/face restoration if needed |
| Waxy/plastic skin | excessive denoise or face restoration | preserve pores and natural micro-contrast; lower restoration strength |
| Rain, dust, sparks mistaken for noise | atmospheric FX distributed over the whole image | spatially bind FX to background/depth and keep face/skin/hero object clean |

## Quality Profiles

### `clean_reference`

Use for identity anchors, three-view sheets, props, products, locations, and machine references.

```text
IMAGE QUALITY — CLEAN REFERENCE:
Create a clean high-resolution source image with clearly resolved silhouette edges, stable fine geometry, coherent material micro-texture, natural local contrast, smooth tonal gradients, and even controlled exposure. Keep the focal subject uniformly legible from edge to edge.
No film grain, analog grain, sensor noise, chroma noise, random speckles, texture overlay, rain on lens, fogged lens, bloom haze, JPEG blocking, macroblocking, pixelation, mosaic artifacts, banding, posterization, ringing, aliasing, over-sharpening halos, smeared detail, muddy textures, or accidental motion blur. Preserve natural skin pores; avoid waxy or plastic smoothing.
Output lossless PNG. One image only; no text, labels, borders, arrows, UI, watermark, or collage.
```

### `clean_cinematic`

Use for hero frames and shot keyframes that need atmosphere without dirtying the image.

```text
IMAGE QUALITY — CLEAN CINEMATIC:
Render a clean cinematic frame with a sharply resolved focal subject, coherent facial features and hand geometry, readable material separation, controlled local contrast, smooth shadow gradients, and physically plausible fine detail. Depth of field is intentional: the focal plane is crisp and only distant depth falls off naturally.
Keep rain, mist, dust, sparks, hologram particles, and bokeh physically localized in depth and away from the face, eyes, hands, and hero object. Do not distribute particles as a full-frame texture.
No digital noise, chroma noise, random speckling, coarse grain, JPEG artifacts, blocking, macroblocking, pixelation, mosaic, banding, posterization, ringing, aliasing, smeared detail, muddy texture, over-sharpening halos, fake HDR, or accidental blur. No film grain unless explicitly requested.
```

### `intentional_film`

Use only when grain is a deliberate art direction. Keep it subtle and add it last:

```text
Fine, uniform 35mm-style luminance grain at low intensity, no chroma noise, no compression blocks, no loss of facial detail, no grain clumping in shadows, and no grain over text or hard geometry.
```

Do not combine `intentional_film` with a requirement for a perfectly clean machine reference.

## Stable Diffusion / FLUX Negative Prompt

Use a compact failure-specific list rather than an indiscriminate token dump:

```text
lowres, low detail, blurry, out of focus, accidental motion blur, noisy, digital noise, chroma noise, random speckles, coarse grain, jpeg artifacts, compression artifacts, blocking, macroblocking, pixelated, mosaic, banding, posterization, ringing, aliasing, oversharpened, sharpening halos, smeared details, muddy textures, waxy skin, plastic skin, text, watermark
```

For SD WebUI/Fooocus, place this in the negative-prompt field. For Codex imagegen, translate it into the natural-language quality lock above; do not paste weighting syntax such as `(term:1.4)` unless the backend supports it.

## Positive Detail Block

Append concrete visual properties instead of relying on `8K`, `masterpiece`, or repeated `ultra detailed` tokens:

```text
clearly resolved subject edges, stable fine geometry, coherent micro-texture, natural skin texture with visible pores, smooth tonal gradients, controlled local contrast, readable material separation, clean shadow transitions, crisp focal plane, physically plausible detail
```

Specify what must be detailed: eyelids, glove joints, engraved metal edges, wet glass boundary, fabric weave, product seams, or architectural joins. Avoid demanding maximum sharpness everywhere when using depth of field.

## Existing Image Edit Prompt

```text
Restore this image while preserving the exact composition, identity, pose, camera, lighting, palette, object geometry, and scene content. Remove digital noise, chroma speckles, JPEG blocking, pixelation, mosaic artifacts, ringing, banding, and muddy or smeared texture. Reconstruct clean edges and coherent local detail without inventing new objects, changing facial identity, altering hands, adding text, or creating waxy skin. Keep intentional rain and atmospheric depth, but confine them to their physical locations and keep the face, eyes, hands, and hero object clean. Return a lossless PNG.
```

Prompt editing can suppress generated artifacts but cannot faithfully reconstruct factual detail that the source never contained. For severe existing degradation, route by failure:

- **General real-world upscale/denoise:** Real-ESRGAN; use the general model and tune denoising strength instead of forcing maximum smoothing.
- **Color noise or JPEG blocks:** SwinIR color denoising / color JPEG compression artifact reduction.
- **Damaged face:** CodeFormer after general restoration; compare fidelity settings and reject identity drift.

Always preserve the original, write restoration output as a new asset version, and visually compare at 100% and 200% zoom.

## Source Basis

- Fooocus official style JSON uses `blur`, `blurry`, `grainy`, `jpeg artifacts`, `noisy`, `soft`, and `glitch` in negative prompts. Its cinematic/photo styles also add `film grain`/`grainy`, which must be removed for a clean-source workflow.
- AUTOMATIC1111 exposes Negative Prompt and Highres Fix as separate controls; prompt constraints do not replace sufficient generation resolution.
- Real-ESRGAN targets practical general image/video restoration and exposes denoising strength plus optional face enhancement.
- SwinIR explicitly supports color/grayscale denoising and JPEG compression artifact reduction.
- CodeFormer is a blind face-restoration route, not a general scene-detail verifier.
