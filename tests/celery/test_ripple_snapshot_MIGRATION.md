# Ripple Snapshot Test Migration

## Overview

The `test_ripple_snapshot.py` test file has been split into 6 smaller, logically-grouped test files for better organization and maintainability.

## Migration Date

2025-10-13

## New Test Files

### 1. test_ripple_snapshot_core.py (2 tests)
**Purpose**: Tests core snapshot functionality including payload persistence and state bootstrapping.

**Tests**:
- `test_refresh_ripple_snapshots_persists_payloads` - Verifies that stable and danger payloads are correctly persisted to Redis with proper metadata
- `test_bootstrap_rebuilds_stable_state` - Tests the bootstrap mechanism that rebuilds state from source data when existing state is outdated

**Rationale**: These tests cover the fundamental operations of the snapshot system - the ability to persist data and rebuild state from scratch.

---

### 2. test_ripple_snapshot_deltas.py (2 tests)
**Purpose**: Tests delta computation logic including tracking changes between snapshots.

**Tests**:
- `test_refresh_ripple_snapshots_computes_deltas` - Verifies delta computation with newcomers, dropouts, and score changes
- `test_delta_resets_after_followup_snapshot` - Tests that deltas reset appropriately after sufficient time has passed (>1 day)

**Rationale**: Delta tracking is a critical feature for showing player progression. These tests ensure deltas are computed correctly and reset at appropriate intervals.

---

### 3. test_ripple_snapshot_previous_payload.py (3 tests)
**Purpose**: Tests previous payload preservation, fallback, and backfilling mechanisms.

**Tests**:
- `test_refresh_ripple_snapshots_preserves_previous_payload` - Verifies that the previous snapshot is preserved when creating a new one
- `test_refresh_ripple_snapshots_uses_preserved_payload_when_latest_missing` - Tests fallback to preserved payload when latest is unavailable
- `test_refresh_ripple_snapshots_backfills_previous_payload` - Tests database backfill when no previous payload exists in Redis

**Rationale**: The system maintains previous payloads for delta computation. These tests ensure the preservation, fallback, and recovery mechanisms work correctly.

---

### 4. test_ripple_snapshot_score_updates.py (1 test)
**Purpose**: Tests the waiting mechanism for post-event score updates.

**Tests**:
- `test_refresh_ripple_snapshots_waits_for_post_event_scores` - Verifies that the system correctly waits for score calculations after recent events before updating snapshots

**Rationale**: This test covers a complex timing scenario where the system must wait for score calculations to complete before updating. It's separated due to its complexity and distinct functionality.

---

### 5. test_ripple_snapshot_locks.py (1 test)
**Purpose**: Tests the lock mechanism that prevents concurrent snapshot updates.

**Tests**:
- `test_refresh_ripple_snapshots_skips_when_locked` - Verifies that refresh operations are skipped when a lock is present

**Rationale**: Lock handling is a critical safety mechanism. This test ensures concurrent operations are properly prevented.

---

### 6. test_ripple_snapshot_errors.py (2 tests)
**Purpose**: Tests error handling and retry logic.

**Tests**:
- `test_refresh_snapshots_async_retries_on_interface_error` - Tests successful retry after a database interface error
- `test_refresh_snapshots_async_gives_up_after_max_retries` - Tests that the system stops retrying after max attempts

**Rationale**: Error handling and retry logic are essential for reliability. These tests ensure the system gracefully handles transient errors while not retrying indefinitely.

---

## Test Count Summary

- **Original file**: 11 tests
- **New files**: 11 tests (distributed across 6 files)
- Core: 2 tests
- Deltas: 2 tests
- Previous Payload: 3 tests
- Score Updates: 1 test
- Locks: 1 test
- Errors: 2 tests

## Running Tests

### Run all new test files:
```bash
pytest tests/celery/test_ripple_snapshot_*.py -v
```

### Run a specific group:
```bash
pytest tests/celery/test_ripple_snapshot_core.py -v
pytest tests/celery/test_ripple_snapshot_deltas.py -v
pytest tests/celery/test_ripple_snapshot_previous_payload.py -v
pytest tests/celery/test_ripple_snapshot_score_updates.py -v
pytest tests/celery/test_ripple_snapshot_locks.py -v
pytest tests/celery/test_ripple_snapshot_errors.py -v
```

### Run original file (for backwards compatibility):
```bash
pytest tests/celery/test_ripple_snapshot.py -v
```

## Migration Plan

**Phase 1 (Current)**: Both old and new test files coexist
- The original `test_ripple_snapshot.py` remains intact
- New split files are available for use
- All 11 tests pass in both configurations

**Phase 2 (Future)**: Deprecate original file
- Add deprecation warning to `test_ripple_snapshot.py`
- Update CI/CD to use new test files
- Update developer documentation

**Phase 3 (Future)**: Remove original file
- Once all teams are using the new structure
- Remove `test_ripple_snapshot.py`
- Update this migration document

## Benefits of Split Structure

1. **Better Organization**: Tests are grouped by functionality, making it easier to find relevant tests
2. **Faster Test Execution**: Can run specific test groups instead of entire suite
3. **Easier Maintenance**: Smaller files are easier to understand and modify
4. **Parallel Execution**: Test groups can run in parallel for faster CI/CD
5. **Clearer Test Failures**: Failures in specific groups immediately indicate which functionality broke
6. **Better Documentation**: File names serve as documentation for what functionality is being tested
