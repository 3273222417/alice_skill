# Storyboard and Shot Language

## Required Shot Fields

| Field | Purpose |
|---|---|
| `shot_id` | Stable shot key such as `SH001` |
| `sequence_id` | Parent sequence |
| `duration` | Playable seconds within the sequence |
| `action` | Observable dominant event |
| `dialogue` | Spoken content and speaker |
| `shot_size` | ECU/CU/MCU/MS/MLS/LS/ELS |
| `camera_angle` | eye-level, low, high, overhead, profile, POV |
| `camera_move` | locked, pan, tilt, dolly, truck, crane, orbit, handheld |
| `lens_mm` | Visual compression/FOV anchor |
| `lighting` | Motivated source and surface response |
| `palette` | Shot-specific color state |
| `transition` | cut, match cut, whip, dissolve, occlusion, sound bridge |
| `start_state` | Exact inherited visual/spatial state |
| `end_state` | Exact handoff state |
| `asset_refs` | Stable IDs used in the shot |
| `backend` | Seedance or local backend |

## Time Design

Every time block must contain a visible change. Allocate time for anticipation, contact, reaction, settling, and the handoff hold. A 4–30 second Seedance sequence can contain multiple short storyboard shots; validate the sequence total, not a minimum of four seconds for every internal shot.

Useful patterns:

- one emotional beat: `0–3s / 3–8s / 8–12s`;
- reveal: setup → evidence → recognition → reaction → hold;
- action: anticipation → acceleration → contact → consequence → recovery;
- dialogue: speaker line → listener reaction → reply → unresolved visual ending.

## Camera Selection

Choose movement from drama:

- locked frame: pressure, awkwardness, observation;
- slow push: realization, threat, intimacy;
- pull-back: isolation, revelation of context;
- lateral track: travel, pursuit, relationship geometry;
- orbit: power shift, spectacle, disorientation;
- handheld correction: urgency and embodied presence;
- crane/rise: scale, release, transition to overview;
- whip/occlusion: motivated transition with a clear bridge object.

Do not stack several camera moves in one short shot unless the movement is physically continuous and easy to visualize.

## Performance Direction

Drive acting from motive and mechanics:

- eye line moves before the head;
- breath changes before speech;
- shoulders and hands reveal suppressed intent;
- contact has compression, drag, and release;
- clothing/hair/environment respond with slight delay;
- listener reactions receive screen time;
- micro-expression resolves into a new state rather than looping.

Avoid emotion labels alone. Write the visible signs of the emotion.

## Light and Environment

Name motivated sources and where they land. Example: “cold window edge light catches the right cheek and jacket seam; warm practical spill dies across the rear wall as the door closes.” Include environmental motion only when it supports the beat.

## Start and End States

An end state must be concrete:

- subject position and facing;
- gaze target;
- hand/prop state;
- camera position and movement state;
- lighting/weather state;
- active sound tail;
- empty-frame or occlusion bridge if used.

Continuation inherits this state. Story continuation can start from a recreated keyframe; boundary-continuous footage uses `video_extension`.

## Board Separation

- **Machine keyframe:** clean image, no text, one shot composition.
- **Machine contact sheet:** clean cells, no captions.
- **Director board:** exact shot IDs, timing, lens, movement, and notes rendered by Pillow.
- **Prompt packet:** textual asset-role mapping; it should not rely on tiny labels baked into images.

## Quality Checks

- Avoid three consecutive shots with identical shot size and camera move unless intentional.
- Keep one dominant action per shot.
- Remove contradictory camera/lens language.
- Ensure referenced characters and props exist in the manifest.
- Ensure dialogue duration includes breathing and listener reaction.
- End with a stable state the next shot can inherit.

