# Tracking Integration Boundary

This module contains the Phase 6 Batch I offline-capable Tracking integration foundation.

Implemented:

- Australia Post and StarTrack adapters for the official Track Items API family;
- explicit immutable Provider/Account/Product/Mapping/Release revisions where each Revision ID independently determines its full content;
- environment-only credential resolution through approved credential references;
- injectable synchronous HTTP transport with HTTPS, connect/read timeouts and response-size limits;
- provider-separated batches of at most 10 IDs and a single-process 10 requests/minute guard;
- strict response validation, classified internal diagnostics, raw-status preservation and evidence-based normalized status mapping;
- no automatic retry, no cross-request cache, no tracking persistence and no Shipping Quote behavior.

The adapters are production code paths, not fake adapters, but they are not activated by `backend.main`. The repository does not contain an approved Configuration Release, Mapping Revision, account, credential binding or real secret. Tests inject only synthetic configurations, credentials, transports and responses. No testbed or production Provider call has been performed.

Current activation state: two runtime groups are labelled `StarTrack / Australia Post`, which is not enough to choose a Provider, and no approved Configuration Release exists. Since D-031 the public projection is no longer blocked: the default application injects a Tracking Service with no active release, returns `provider=null` / `unavailable` / `CARRIER_MAPPING_UNRESOLVED` for every unique tracking group, and never issues a Provider request. The adapters stay inactive until an approved release, mapping, account and credentials exist; real testbed/production verification is still BLOCKED.

Never add real keys, secrets, account numbers, tracking IDs or Provider payloads to this directory, tests, logs or documentation.
