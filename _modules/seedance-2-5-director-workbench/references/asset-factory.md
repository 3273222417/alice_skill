# Asset Factory

## Stable Asset Types

| Type | Prefix | Typical output |
|---|---|---|
| `character` | `CHR` | identity anchor, three-view, six-view, face crop |
| `location` | `LOC` | wide, medium, detail, reverse, lighting states |
| `prop` | `PRP` | geometry, scale, interaction, material |
| `wardrobe` | `OUT` | front/back/detail and worn state |
| `palette` | `PAL` | visual DNA and material/light palette |
| `camera` | `CAM` | blockout, lens/FOV, motion path |
| `keyframe` | `KFR` | one clean shot anchor |
| `storyboard` | `SBD` | labeled director board |
| `audio` | `AUD` | voice, music, ambience, SFX |
| `video` | `VID` | source, plate, edit target, extension source |

Use stable IDs and append versions. Never reuse an ID for a different conceptual asset.

## Version Rules

- `current_version` points to `v001`, `v002`, and so on.
- A version owns its prompt, sources, files, hashes, status, and change note.
- `draft` may change; `reviewed` is accepted for current work; `locked` is a continuity contract; `deprecated` stays for provenance but is no longer selected.
- A change to identity, geometry, scale, wardrobe, or lighting creates a new version.
- Bump only dependent shots. Do not invalidate unrelated assets.

## Character Production

### Identity Anchor

Generate a neutral, unambiguous base image:

- single subject;
- neutral expression and pose;
- unobstructed face;
- controlled soft lighting;
- plain gray background;
- stable age range and facial proportions for fictional/synthetic actors;
- no text, labels, UI, collage, or environmental story.

### Three-View

Generate three separate files, then compose:

1. front orthographic full body;
2. true side profile full body;
3. back orthographic full body.

Lock identity, hair, wardrobe, body proportions, camera height, focal length, neutral pose, exposure, and background. Do not ask one image-model call to render accurate labels.

### Six-View

Use six independent images:

1. front full body;
2. three-quarter full body;
3. back full body;
4. waist-up performance view;
5. hands/accessory detail;
6. clean face close-up.

The face close-up is the highest-fidelity identity source; the full body defines proportions and clothing, not facial detail.

## Location Production

Build at least:

- establishing wide;
- subject-height medium;
- reverse angle;
- material/detail view;
- alternate lighting/time state.

For a 3×3 sheet, add entrances/exits, overhead spatial map, hero composition, and transition/stitch angle. Keep geometry and light direction consistent.

## Product and Prop Production

For important products create:

- front/back/left/right/top/bottom or useful eight-view geometry;
- material macro;
- scale reference beside a known object or hand;
- interaction state;
- logo/text isolated from machine video references if lettering accuracy matters.

Words do not reliably preserve scale. A scale-reference frame is an asset and should be attached to every affected shot.

## Imagegen Prompt Shape

Use this role-oriented structure:

```text
Create one clean [asset type] reference image.
SUBJECT/GEOMETRY: ...
IDENTITY ROLE: use [reference] only for ...; do not copy ...
WARDROBE/MATERIAL ROLE: ...
POSE/VIEW: ...
CAMERA: ...
LIGHTING: ...
BACKGROUND: ...
CONTINUITY LOCKS: ...
IMAGE QUALITY PROFILE: clean_reference | clean_cinematic | intentional_film
IMAGE QUALITY LOCK: ...
OUTPUT: one image, no text, no labels, no arrows, no UI, no collage.
```

One call should produce one distinct asset. Use an edit call for one controlled change to an accepted source.

Use `clean_reference` for asset sheets and `clean_cinematic` for hero/keyframe images. Read `image-quality-recovery.md` for the full blocks. Never add `film grain`, `grainy`, `Kodak`, or `found footage` by habit when the required output is clean. Spatially bind rain, fog, dust, sparks, and hologram particles so they do not become full-frame noise.

## Dependency Rules

- Character keyframes depend on the current character and wardrobe versions.
- Location keyframes depend on location and palette versions.
- Product shots depend on product geometry, material, and scale assets.
- Director boards depend on keyframes but do not replace them as machine references.
- Video prompts reference stable asset IDs and resolved current files.

When bumping an asset, mark dependent shots for review and regenerate only their keyframes/boards.
