# Avatar prompting rules

Use this compact rule set for every OpenClaw expert avatar prompt.

## Required style

- Square app avatar, polished 2D cartoon illustration.
- Chinese professional expert character when the title contains `师`, `专家`, `顾问`, `教练`, `运营`, `策略`, `分析`, `开发`, or similar role language.
- Use icon/abstract object avatars only when the role is clearly not a person; most Workbuddy experts should use a person.
- Cute professional, clean UI asset, rounded-app-icon feel.
- Do not use photorealism, real-person portraits, text, watermark, brand logos, or platform logos.

## Diversity rules

Every new prompt must vary:

- face shape: round, oval, square, heart, angular, long, broad
- age impression: young, mature, senior, neutral
- hairstyle: bob, ponytail, buns, curly, side-part, buzz/short, silver hair, etc.
- clothing: hoodie, blazer, cardigan, vest, turtleneck, shirt, jacket
- scene: domain-specific workplace, not the same generic dashboard for everyone
- palette: rotate warm/cool/dark/pastel and avoid repeating adjacent colors
- props: exactly 1-3 clear props tied to the role

## Prompt skeleton

```text
Use case: stylized-concept
Asset type: 1 square expert avatar for OpenClaw app
Primary request: <title> avatar, <short role/persona>
Scene/backdrop: <domain-specific scene, no readable text/logos>
Subject: <distinct 2D cartoon Chinese character: face, hair, clothing, prop>
Style/medium: polished 2D cartoon app-avatar illustration, cute professional, NOT realistic, NOT photo
Composition/framing: square close-up icon, head and shoulders, clear silhouette, generous padding
Lighting/mood: <mood>
Color palette: <distinct palette>
Constraints: single avatar only, no text, no watermark, no logos, no photorealism, no real-person portrait, do not repeat previous character designs
```
