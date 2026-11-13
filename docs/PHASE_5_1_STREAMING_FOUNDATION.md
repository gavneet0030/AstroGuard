# AstroGuard Phase 5.1 — Streaming Foundation

## Objective

Establish transport-independent event contracts, topic definitions,
configuration and a bounded asynchronous local broker.

## Components

- `streaming/contracts.py`: versioned EventEnvelope.
- `streaming/topics.py`: centralized topic registry.
- `streaming/config.py`: validated environment configuration.
- `streaming/broker.py`: broker protocol and in-memory implementation.

## Event contract

Each event carries:

- event_id: unique UUID
- event_type: namespaced event type
- schema_version: positive integer
- occurred_at: timezone-aware timestamp
- source: producer identifier
- channel: optional A-1 or P-1 channel
- partition_key: optional ordering/partition hint
- payload: JSON-compatible domain payload

## Topics

- astroguard.telemetry.raw
- astroguard.telemetry.validated
- astroguard.anomalies.detected
- astroguard.events.dead-letter

## Local broker limitations

The in-memory broker is bounded and asynchronous.

It provides:
- topic validation
- event type validation
- backpressure through bounded queues
- explicit local acknowledgement
- queue depth inspection

It does NOT provide:
- disk durability
- replication
- cross-process communication
- consumer-group coordination
- persistent offsets
- distributed ordering guarantees

It is a development/test transport only.

## Configuration

- ASTROGUARD_STREAMING_ENABLED
- ASTROGUARD_STREAMING_TRANSPORT
- ASTROGUARD_STREAMING_QUEUE_CAPACITY
- ASTROGUARD_STREAMING_PUBLISH_TIMEOUT
- ASTROGUARD_STREAMING_BATCH_SIZE

Streaming remains disabled by default.

## Safety boundaries

This phase does not:
- change the existing database schema
- execute migrations
- change existing telemetry ingestion
- change Phase 3 ML inference
- publish real NASA data
- start Docker containers

## Acceptance

- Python compilation passes.
- Focused streaming tests pass.
- Full backend regression passes.
- pip check passes.
- Existing Phase 3 and Phase 4 behavior remains intact.