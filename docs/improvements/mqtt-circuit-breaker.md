# improve/mqtt-circuit-breaker

## Goal
Add reconnect resilience controls with circuit-breaker style behavior.

## Scope
- Introduce bounded/exponential reconnect backoff controls.
- Add cool-down behavior after repeated connection failures.
- Improve operational logs for prolonged outage states.

## Implementation Checklist
- [ ] Define thresholds and cooldown policy.
- [ ] Add configurable settings with safe defaults.
- [ ] Implement state transitions (normal, degraded, cooldown).
- [ ] Validate recovery behavior when broker returns.

## PR Checklist
- [ ] Failure-state timeline documented.
- [ ] Config defaults and tuning guidance included.
- [ ] Rollback behavior described.

## Done Criteria
- [ ] Repeated failures no longer spam rapid retries.
- [ ] Recovery transitions are automatic and observable in logs.
