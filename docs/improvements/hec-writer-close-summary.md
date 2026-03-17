# improve/hec-writer-close-summary

## Goal
Complete HEC batch writer shutdown behavior and summary logging.

## Scope
- Finalize `_HecBatchWriter.close()` flow.
- Ensure final flush and deterministic summary metrics.
- Keep behavior unchanged outside HEC close/flush path.

## Implementation Checklist
- [ ] Review `_HecBatchWriter.flush()` and `.close()` interactions.
- [ ] Ensure buffered events are flushed on shutdown.
- [ ] Emit complete writer summary counters.
- [ ] Validate with controlled shutdown test.

## PR Checklist
- [ ] Root cause and expected behavior documented.
- [ ] Before/after shutdown logs included.
- [ ] Risk and rollback noted.

## Done Criteria
- [ ] No dropped buffered events on normal shutdown.
- [ ] Summary log includes complete batch/event/retry counters.
