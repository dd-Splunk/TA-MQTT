# improve/configurable-queue-size

## Goal
Make MQTT event queue capacity configurable with validation and observability.

## Scope
- Add queue size setting to input configuration.
- Validate min/max bounds.
- Wire runtime queue construction to configured value.

## Implementation Checklist
- [ ] Add setting in globalConfig and REST/input validation.
- [ ] Apply setting in `collect_events()` queue initialization.
- [ ] Extend health logs to include configured capacity.
- [ ] Validate behavior under backpressure.

## PR Checklist
- [ ] Default and bounds rationale documented.
- [ ] Backward compatibility confirmed.
- [ ] Performance/backpressure evidence included.

## Done Criteria
- [ ] Operators can tune queue size safely.
- [ ] Runtime metrics reflect configured capacity.
