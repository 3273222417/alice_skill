# Director Workflow

## Production Contract

The workbench turns a story or brief into five linked layers:

1. **Story layer** — filmable beats, causality, duration, and ending state.
2. **Asset layer** — versioned characters, locations, props, wardrobe, palette, audio, and source media.
3. **Shot layer** — one controlled visual event per shot with explicit camera and timing.
4. **Board layer** — clean keyframes for machines and labeled boards for humans.
5. **Delivery layer** — Seedance prompt/parameters or a local identity job packet.

Do not skip directly from prose to a giant video prompt when continuity matters.

## Phase 1: Diagnose the Story

Extract:

- emotional core and conflict;
- strongest filmable event;
- visible cause and effect;
- required dialogue and playable pauses;
- locations, time changes, and continuity-sensitive objects;
- final state that the next segment must inherit.

Estimate runtime from screen action, not source length. Count physical actions, dialogue time, reactions, travel, scene changes, reveals, camera reframing, and the final hold. Split at an emotional turn, location change, action phase, or reveal/aftermath boundary rather than accelerating everything.

## Phase 2: Establish Visual DNA

Lock a compact visual system before generating assets:

- format and aspect ratio;
- era, production design, and texture;
- palette and contrast structure;
- motivated key/fill/practical light sources;
- lens family, depth of field, and camera behavior;
- motion cadence and editing rhythm;
- atmospheric motion and sound identity.

Save this as a palette/style asset. Reuse it by role, not by vague instructions such as “same style.”

## Phase 3: Build Reusable Assets

Use an asset when it establishes identity, continuity, geometry, scale, or appears in at least three shots. Images come before video.

Recommended order:

1. identity anchor;
2. front/side/back character sheet;
3. six-view character sheet;
4. location views including reverse angle;
5. prop/product geometry and scale;
6. material/wardrobe states;
7. hero frame;
8. per-shot keyframes.

Generate separate clean images first. Compose contact sheets afterward. For a face-lock asset, provide one unambiguous face source rather than several conflicting face crops.

## Phase 4: Design Shots

Each shot should describe one dominant visual event. State:

- initial spatial state;
- subject action and physical consequence;
- camera framing, angle, movement, and lens;
- light and environmental response;
- visible emotional performance;
- dialogue/sound with timing;
- transition and final state.

Write physical pictures. Replace “more natural” with observable mechanics: weight transfer, delayed shoulder follow-through, contact compression, cloth drag, breath, blinking, eye-line correction, foot placement, object inertia, or camera operator correction.

## Phase 5: Generate Keyframes

Create one clean keyframe per shot. A keyframe controls composition, light, pose, and spatial relationships; it should not contain captions or arrows. If a shot needs start and end anchors, register both as separate assets and declare their temporal role in the final prompt.

## Phase 6: Build Director Boards

Use Pillow to place verified keyframes and exact labels. Director boards may include shot ID, time, lens, movement, asset IDs, and notes. Machine references remain clean. Generated storyboard grids should contain at most four panels; deterministic composition can create six- or nine-cell planning sheets without asking the image model to render text.

## Phase 7: Route the Video Backend

- Seedance `t2v`: no references.
- Seedance `omni_reference`: original/synthetic character, location, keyframe, audio, or motion references.
- Seedance `video_edit`: source video timeline is retained while content is changed.
- Seedance `video_extension`: footage continues before/after a source boundary.
- Local still identity: PhotoMaker V2, then PuLID-FLUX fallback.
- Local portrait animation: LivePortrait.
- Local full identity video: ConsisID slow/offload route.

Real-person upload rejection is a routing signal, not a prompt-writing problem.

## Phase 8: Prompt and Preflight

The final prompt packet must include:

1. mode and parameters;
2. asset-to-role mapping;
3. Identity/Character Anchor;
4. Scene/Visual DNA;
5. Motion Block;
6. timestamped timeline;
7. sound/dialogue block;
8. end state and continuity locks;
9. exclusions for every reference;
10. local identity commands/job files when relevant.

Run `director_preflight.py`. Fix missing files, broken asset IDs, incompatible identity routing, invalid duration/resolution, and edit/extension source requirements.

## Failure Recovery

- Preserve the failed prompt and job state under `logs/` or `jobs/`.
- Change one variable at a time.
- If the same defect appears in four batches, revise the source/keyframe/prompt instead of batching again.
- If motion has no source anchor, create a stronger keyframe or switch from footage transformation to image-driven generation.
- If scale drifts, add a dedicated scale-reference frame and attach it to every affected shot.
- If a reverse angle invents the environment, build an explicit reverse-angle location asset.
- If only wardrobe/hair/one prop changes, bump that asset and dependent shots, not the entire project.

## Continuation

Load the previous `project.json` and ending state. Keep locked identity, wardrobe, location geometry, props, palette, and audio identity. Create only new assets. Continue the story with a new sequence or shots. Use Seedance `video_extension` only when the new footage must attach to an existing video's boundary; otherwise use ordinary generation with continuity references.

