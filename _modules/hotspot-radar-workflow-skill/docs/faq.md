# FAQ

## Does this guarantee viral content?

No. It surfaces high-signal candidate topics based on available metrics and evidence. It does not predict guaranteed virality.

## Why is play count missing?

Some provider responses may not include play count, completion rate, follower count, transcript, or OCR. Missing fields are marked explicitly.

## Can I use one keyword only?

Yes. Give one broad theme or keyword. The Skill expands it into related search keywords automatically.

## Why did the second run return fewer than 10 topics?

Same-theme deduplication excludes candidates already returned in previous checklists. If too few new candidates remain, broaden the theme or run new searches.

## Where is my Token stored?

On macOS, the setup script stores it in Keychain service `hotspot_radar_tikhub_api_token` under your current local user.

## Can I use another API provider?

Not directly in 0.1.0. The current scripts use TikHub. You can adapt another provider by producing the same normalized candidate fields described in `docs/api-provider.md`.

