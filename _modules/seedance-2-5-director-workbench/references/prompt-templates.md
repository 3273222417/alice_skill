# Prompt and Job Templates

## Seedance 2.5 Production Packet

```text
MODE: omni_reference
PARAMETERS: 720p, 16:9, 15 seconds

ASSET ROLE MAP
@Image 1 / CHR001 v003 — defines [identity role] at [fidelity]; do not copy [background/pose/light].
@Image 2 / OUT001 v002 — defines [wardrobe/material]; do not change [identity/body].
@Image 3 / LOC001 v001 — defines [geometry/light]; do not copy [people/text].
@Image 4 / KFR001 v001 — defines [composition/start state]; do not freeze motion or reproduce board labels.

IDENTITY / CHARACTER ANCHOR
[stable synthetic/original character description, proportions, hair, wardrobe state, performance motive]

SCENE / VISUAL DNA
[location geometry, era, palette, motivated light, texture, atmosphere, lens family]

MOTION BLOCK
[subject biomechanics, object weight/contact, environmental response, camera mechanics]

TIMELINE
[0.0–3.0s] ... End state: ...
[3.0–9.0s] ... End state: ...
[9.0–13.5s] ... End state: ...
[13.5–15.0s] final hold and sound tail ...

AUDIO
[Dialogue: speaker, exact line, timing, voice]
[SFX: event and timing]
[Ambience/Music: rhythm, level, transition]

POSITIVE LOCKS
[identity, geometry, scale, continuity, spelling, no unwanted reference leakage]

IMAGE QUALITY LOCK
[clean focal subject; stable fine geometry; localized atmospheric FX; no digital noise, JPEG blocking, pixelation, mosaic, banding, ringing, smeared detail, or accidental blur]
```

## `t2v`

Remove the asset-role map. Fully specify visible subject, scene, camera, motion, light, timeline, sound, and ending state. Do not invent media references.

## `video_edit`

```text
MODE: video_edit
SOURCE: @Video 1 is the timeline and motion source.
KEEP: camera path, timing, subject movement, contact, occlusion, perspective, and unaffected regions.
CHANGE: [precise subject/region/property].
INHERITANCE: the replacement follows source motion, light, shadow, depth, blur, and interactions frame by frame.
SCOPE: [where and when the edit begins/ends].
AUDIO: [keep/change details].
```

Do not state a new arbitrary duration/aspect ratio.

## `video_extension`

```text
MODE: video_extension
EXTENSION_MODE: forward | backward
SOURCE: @Video 1 defines the exact boundary state and inherited camera/aspect.
BOUNDARY STATE: [subject position, pose, gaze, prop, camera, light, active sound].
NEW ACTION: [physically continuous action].
TIMELINE: [...]
FINAL STATE: [clean handoff].
```

## Local Identity Job

```json
{
  "identity_mode": "consented_local_identity",
  "backend": "photomaker_v2",
  "task": "still",
  "source_images": ["<authorized-photo-1>", "<authorized-photo-2>"],
  "prompt": "<view, wardrobe, scene, lighting, output constraints>",
  "negative_prompt": "identity drift, duplicate person, lowres, blurry, noisy, digital noise, chroma noise, jpeg artifacts, blocking, pixelated, mosaic, banding, smeared details, waxy skin, text, labels, collage",
  "output": "<managed project asset path>",
  "seedance_eligible": false,
  "provenance": {"project_asset_id": "CHR001", "version": 2}
}
```

## Final Delivery Checklist

- mode and model parameters;
- asset role/version table;
- complete prompt or local job JSON;
- generated/managed paths that actually exist;
- preflight status;
- unresolved warning and next exact command.
