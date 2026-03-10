# TA-MQTT — Lessons Learned

## L-001 — paho-mqtt loop model vs Splunk's modular input lifecycle

**Problem**: `client.loop_forever()` blocks indefinitely and prevents the
modular input framework from stopping the process cleanly.

**Resolution**: Use `client.loop_start()` (background thread) combined with
an explicit `while not shutdown_evt.is_set()` loop in `collect_events()`.
Stop with `client.loop_stop()` in the `finally` block.

---

## L-002 — SSL context + paho-mqtt: `tls_set()` vs `tls_set_context()`

**Problem**: `client.tls_set(ca_certs=None)` requires a file path; it cannot
accept an in-memory PEM string for the CA cert.

**Resolution**: Build an `ssl.SSLContext` manually and pass it via
`client.tls_set_context(ctx)`.  Use `ctx.load_verify_locations(cadata=pem_str)`
to load a CA cert from a string without writing a file.

---

## L-003 — Client cert + key still require temp files

**Problem**: `ssl.SSLContext.load_cert_chain()` only accepts file paths, not
strings.  There is no equivalent of `cadata=` for client credentials.

**Resolution**: Write cert and key to `tempfile.mkstemp()` files, load them
into the context, then delete them in the `_TLSSetup.__exit__` cleanup path.
The context manager pattern ensures cleanup even on exception.

---

## L-004 — UCC checkbox values are stored as strings "0"/"1"

**Problem**: `broker_cfg.get("use_tls")` returns `"0"` or `"1"` (string),
not `False`/`True`.  A naive `if broker_cfg.get("use_tls")` always evaluates
to `True` because non-empty strings are truthy in Python.

**Resolution**: Use the `_is_true()` helper that normalises to a set of
truthy string values: `{"1", "true", "yes", "on"}`.

---

## L-005 — Event writing must happen in the main thread

**Problem**: Calling `ew.write_event()` from paho's network thread (inside
`on_message()`) can cause race conditions or silent drops.

**Resolution**: `on_message()` pushes dicts onto a `queue.Queue`; the main
thread drains the queue and calls `ew.write_event()` inside the poll loop.

---

## L-006 — `interval = -1` in inputs.conf means "run once, not on a schedule"

**Problem**: Setting `interval = -1` in `inputs.conf` tells Splunk to run the
input script once and not reschedule it — which is correct for a blocking
MQTT loop.  However this means Splunk will NOT restart the script if it
exits unexpectedly; the internal reconnect loop handles that instead.

**Resolution**: The `collect_events()` loop never returns under normal
operation.  Reconnection on broker disconnect is handled by sleeping
`interval` seconds (from the input parameter, default 30) and calling
`client.connect()` again.
