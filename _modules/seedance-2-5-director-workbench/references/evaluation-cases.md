# Evaluation and Regression Cases

## E1 — Original Virtual Actor

**Input:** “设计一个原创女侦探，做三视图、六宫格、8 个镜头，再给 Seedance 2.5 提示词。”

**Expected:** `fictional` + `codex_imagegen`; versioned CHR/OUT/LOC/KFR/SBD assets; clean machine references; Pillow director board; `omni_reference`; 720p and 4–30 second sequence preflight.

## E2 — Prompt Only

**Input:** “只给我 12 秒 Seedance 提示词，不要生成图。”

**Expected:** no imagegen call and no fabricated file path; correct mode, timeline, end state, and paste-ready prompt.

## E3 — Consented Multi-Photo Identity

**Input:** “用我授权的演员 4 张照片，做不同服装的身份一致关键帧。”

**Expected:** `consented_local_identity`; PhotoMaker V2 recommended on RTX 3060 12GB; character asset `seedance_eligible=false`; job JSON with source hashes/paths; no repeated Seedance upload.

## E4 — Single-Photo Identity Fallback

**Input:** “只有一张授权头像，要更强的提示词可编辑性。”

**Expected:** PuLID-FLUX shown as fallback with 12GB/FP8/offload route; no InfiniteYou local recommendation.

## E5 — Close-Up Animation

**Input:** “让这张授权肖像说话、眨眼、轻微转头。”

**Expected:** LivePortrait route with source/driving inputs and InsightFace model-license warning; not ConsisID by default.

## E6 — Full Local Identity Video

**Input:** “必须本地生成保持真人身份的完整短视频。”

**Expected:** ConsisID slow experimental route, CPU offload + VAE slicing/tiling recommendations, explicit job state, no fabricated success.

## E7 — Seedance Upload Rejection

**Input:** recognizable face was rejected by Seedance.

**Expected:** asset flips to `seedance_eligible=false`; character shot routes local; camera/scene/motion/sound plan retained; identity-independent plate may remain Seedance.

## E8 — Video Edit

**Input:** “把现有视频里的红外套改成黑色皮衣，其他都不变。”

**Expected:** `video_edit`; source video required; timeline, camera, motion, contact, occlusion, and unaffected regions locked; no new duration/aspect promise.

## E9 — Boundary Extension

**Input:** “从这个视频最后一帧继续向前延长 8 秒。”

**Expected:** `video_extension`, `forward`, source required, inherited boundary state, 8-second extension timeline, explicit new ending state.

## E10 — Story Continuation, Not Extension

**Input:** “续写上一集，但从第二天早上新场景开始。”

**Expected:** continuation workflow with reused locked assets and new sequence; not automatically `video_extension`.

## E11 — Surgical Asset Revision

**Input:** “只把主角发型改短，其他镜头不要重做。”

**Expected:** bump CHR version, retain previous files, mark only dependent keyframes/shots for review.

## E12 — Broken Reference

**Input state:** a shot references missing `LOC099` or a managed file was removed.

**Expected:** preflight error and nonzero exit; no final “ready” claim.

## E13 — Board Accuracy

**Input:** six keyframes and six labels.

**Expected:** 3×2 director board at requested size with exact labels; machine mode has no text; output file exists and dimensions are verified.

## E14 — Hardware Probe

**Environment:** RTX 3060 12288 MiB.

**Expected:** PhotoMaker recommended; PuLID available as 12GB edge route; InfiniteYou insufficient; ConsisID optimized slow route.

## E15 — Validation

**Expected:** `quick_validate.py` passes; SKILL frontmatter contains only `name` and `description`; all local reference/script links exist; source skill/archive hashes remain unchanged.

## E16 — Noise, Blur, and Mosaic Quality Lock

**Input:** “画面有噪点、细节糊、JPEG 块和马赛克；保持构图与人物不变。”

**Expected:** classify scene particles versus digital/compression artifacts; select `clean_reference` or `clean_cinematic`; remove accidental film-grain cues; emit a backend-appropriate quality lock; preserve PNG; route severe existing degradation to Real-ESRGAN/SwinIR and face-only damage to CodeFormer; never overwrite the original asset version.
