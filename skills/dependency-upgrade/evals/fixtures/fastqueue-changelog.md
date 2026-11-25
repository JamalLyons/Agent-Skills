# fastqueue changelog (excerpt, synthetic)

## 5.0.0

### Breaking

- Remove deprecated `queue.onFailed(cb)`. Use `queue.on('failed', cb)`.
- `retry.attempts` now counts total attempts including the first run (was retries after the first).

## 4.0.0

### Breaking

- Drop Node 16 support; Node 18.18+ required.
- `queue.add(name, data, opts)`: `opts.delay` renamed to `opts.delayMs`.
- `queue.drain()` removed; use `await queue.idle()`.

### Deprecated

- `queue.onFailed(cb)`; use `queue.on('failed', cb)`.

## 3.5.2

### Security

- Fix prototype pollution in job data merge (GHSA-xxxx-synthetic, affects >=3.0.0 <3.5.2).
