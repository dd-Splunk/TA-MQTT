# improve/payload-decode-fallback

## Goal
Improve payload decode fallback behavior for non-UTF MQTT payloads.

## Scope
- Refine `on_message` payload decoding path.
- Preserve searchability while avoiding opaque-only payload representations.
- Keep existing UTF-8 flow unchanged.

## Implementation Checklist
- [ ] Define event schema for fallback metadata (encoding indicator).
- [ ] Implement robust decode/fallback logic.
- [ ] Validate with binary and malformed payload samples.
- [ ] Confirm backward compatibility for current dashboards/search.

## PR Checklist
- [ ] Event schema change explained.
- [ ] Sample events (UTF-8 vs fallback) included.
- [ ] Migration/compatibility note included.

## Done Criteria
- [ ] Non-UTF payloads are safely indexed with explicit metadata.
- [ ] No callback crashes or silent data loss.
