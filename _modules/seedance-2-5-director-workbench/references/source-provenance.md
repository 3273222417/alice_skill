# Source Provenance and Decisions

## Preserved Local Sources

This skill was created as a new standalone directory. It does not modify:

- `C:\Users\Administrator\.codex\skills\higgsfield-seedance-2-5`
- `C:\Users\Administrator\Documents\xwechat_files\wxid_jg1ih4kjfg3l22_58a5\msg\file\2026-08\cinematic-video-prompt-engineer(1).rar`

Snapshot SHA-256 values recorded during integration:

- source `SKILL.md`: `1BC19380EA86F2485453A43EC47EC8537FA3BAEB058BBA2235A4BF308F6648AE`
- source `MODE-PLAYBOOKS.md`: `D879732B7B786E5870123DFB15C34932A393601273ADDF68C513A227258DD3AC`
- source `VFX-PIPELINE.md`: `B54A6A07431314C03D3CAF8655B2B44E09DAF95BEE191A09168CC976764E0BEA`
- supplied RAR: `BEB6CE26D1B58316C37CF0CBFF9512E5584BF82FA1124BFEAE465CFF158A9115`

The supplied cinematic skill contributed story diagnosis, duration reasoning, performance/camera/light language, continuation discipline, visual-reference prompts, and the large searchable style-pattern library.

The installed Seedance skill contributed the four-mode router, explicit reference roles/exclusions, 4–30 second and 720p surface, timestamped end states, edit/extension semantics, and images-first VFX discipline. Broken sibling-skill references and invalid extra frontmatter were not copied.

## Public Sources Adopted

- [Higgsfield official skills](https://github.com/higgsfield-ai/skills) — Seedance generation modes and Higgsfield-facing workflow.
- [OSideMedia Higgsfield prompt skill](https://github.com/OSideMedia/higgsfield-ai-prompt-skill) — character anchors, location/product views, and reusable asset discipline (MIT).
- [AI Visual Director](https://github.com/jijiutong/ai-visual-director) — shot schema, patch/dependency workflow, and small storyboard-panel discipline (MIT).
- [Storyboarder](https://github.com/wonderunit/ducks-storyboarder) — practical shot/time/action/dialogue/layer project concepts.
- [PhotoMaker](https://github.com/TencentARC/PhotoMaker) — multi-photo, training-free identity-preserving still generation; Apache-2.0; documented minimum around 11GB VRAM.
- [PuLID](https://github.com/ToTheBeginning/PuLID) — prompt-editable single-image identity route and official 12GB configuration; Apache-2.0.
- [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) — portrait animation; MIT code. Default InsightFace model terms require separate review, especially for commercial work.
- [ConsisID](https://github.com/PKU-YuanGroup/ConsisID) — identity-preserving text-to-video; Apache-2.0; high default VRAM with slower CPU-offload/VAE optimization routes.
- [InfiniteYou](https://github.com/bytedance/InfiniteYou) — retained as a future high-memory/cloud option, not a 12GB default.

## Explicit Decisions

Image quality and restoration sources:

- [Fooocus style definitions](https://github.com/lllyasviel/Fooocus/blob/main/sdxl_styles/sdxl_styles_fooocus.json) — practical positive/negative prompt patterns and evidence that cinematic presets may intentionally inject `film grain`/`grainy`.
- [AUTOMATIC1111 negative prompt](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Negative-prompt) and [features](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features) — negative conditioning and Highres Fix are separate controls.
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) — general restoration/upscale route with denoising-strength control and optional face enhancement.
- [SwinIR](https://github.com/JingyunLiang/SwinIR) — explicit color/grayscale denoising and JPEG artifact-reduction routes.
- [CodeFormer](https://github.com/sczhou/CodeFormer) — blind face restoration for damaged face regions.

1. Seedance face-upload rejection is treated as a service routing constraint, not a prompt bypass target.
2. Original and synthetic actors use Codex imagegen and may become Seedance omni references.
3. Consented recognizable identity stays in the local identity pipeline.
4. Scripts manage state, validation, composition, and command/job packets; they do not call hidden image APIs or vendor services.
5. Machine references contain no labels; director boards use deterministic Pillow text.
6. Failures preserve inputs, prompts, job state, and logs; outputs are never fabricated.
