# Seedance 2.5 Modes

## Parameter Surface

Use the Higgsfield Seedance 2.5 surface represented by the source skill:

- modes: `t2v`, `omni_reference`, `video_edit`, `video_extension`;
- generation duration: 4–30 seconds;
- output: 720p for this workbench;
- no Seedance 2.0-style `start_image`, `end_image`, `genre`, or 4K promise;
- `video_edit` takes source-video timeline/aspect behavior and ignores ordinary generation duration/aspect controls;
- `video_extension` inherits source aspect and requires forward/backward extension direction.

## Mode Router

### `t2v`

Use when no media reference is required. Prompt from the story, visual DNA, motion, timeline, and sound. Do not list imaginary `@Image` references.

### `omni_reference`

Use when original/synthetic identity, location, prop, keyframe, audio, or motion/video references guide a new generation. Declare each material's role and exclusion.

Example role grammar:

```text
@Image 1 defines the synthetic lead's face, hair, and facial proportions at high fidelity;
do not copy its gray background, neutral lighting, or pose.
@Image 2 defines wardrobe cut and fabric response;
do not replace the identity from @Image 1 or copy the mannequin stance.
@Image 3 defines the location geometry and motivated window light;
do not copy people or signage from it.
```

If a source video only supplies motion/performance for a transformed new shot, it may be used as an `omni_reference` motion source. If the existing timeline itself must be edited, use `video_edit`.

### `video_edit`

Use for subject/background/wardrobe/audio or written-scope changes inside an existing video while retaining its timeline. State:

1. what must remain unchanged;
2. what region/subject changes;
3. how the replacement inherits motion, occlusion, perspective, light, contact, and timing;
4. the exact source video role.

Do not promise a new arbitrary duration or aspect ratio.

### `video_extension`

Use only for direct boundary continuation. State `forward` or `backward`, identify the source video, describe the inherited boundary state, and specify new action and final state. Additional materials may define new objects/locations but must not contradict the source boundary.

## Reference Budget

Every reference must earn a role. Prefer a few unambiguous assets over many conflicting sheets. Resolve conflicts explicitly:

- face source outranks full-body face detail;
- full-body source defines proportion and wardrobe;
- location source defines geometry/light, not characters;
- motion video defines timing/biomechanics, not identity or costume;
- audio defines voice/rhythm, not visual appearance.

## Long-Form Timeline

For longer sequences, use timestamped stages and end states:

```text
[0.0–2.0s] Establish ... End with ...
[2.0–7.0s] The lead ... Camera ... End with ...
[7.0–12.0s] Reaction and consequence ...
[12.0–15.0s] Final hold ... sound tail ...
```

Each section should advance action, gaze, spatial relation, light, or sound. Reserve a short final hold for clean continuation or editing.

## Audio and Text

Declare dialogue, voice, ambience, music, and SFX with timing. Keep on-screen text minimal and exact; generate critical typography separately for post rather than relying on video-model spelling.

## Pre-Submission Checklist

- Correct mode chosen before prompt writing.
- 4–30 second generated sequence and 720p.
- Every referenced asset exists and has a role plus exclusion.
- No consented real-person asset marked Seedance-ineligible is attached.
- Timeline has visible changes and an explicit final state.
- Edit/extension has a real source video and correct inherited controls.
- Prompt does not expose director-board labels as machine visual references.

