# Phase 5.3 — Telemetry Producer & Ingestion

## Scope

This phase adds an application-level producer over the existing Phase 5.1
BrokerProtocol and Phase 5.2 topic registry.

## Components

- `producer.py`: bounded producer, serialization, topic routing and results.
- `TelemetryProducer`: sequential publish and batch publish.
- `PublishResult`: one event delivery result.
- `BatchPublishResult`: bounded batch summary.
- `serialize_event`: canonical UTF-8 JSON serialization.
- `deserialize_event`: structural and timestamp validation.

## Topic routing

| Event type | Topic |
|---|---|
| telemetry.raw | astroguard.telemetry.raw |
| telemetry.validated | astroguard.telemetry.validated |
| anomaly.detected | astroguard.anomalies.detected |
| dead_letter | astroguard.events.dead-letter |

## Delivery semantics

An accepted result means the configured broker's publish coroutine returned
successfully. It does not mean that an external Kafka cluster replicated or
persisted the event.

The current in-memory broker is development/test infrastructure only.

## Resource limits

- Default maximum message size: 256 KiB.
- Default publish timeout: 3 seconds.
- Default batch size: 32.
- Batch publishing is sequential and does not create unbounded tasks.

## Safety boundaries

- No database writes.
- No model training or recalibration.
- No test-label access.
- No dataset modification.
- No Kafka or Docker startup.
- No claim of flight/operational safety.

## Validation

Run focused tests:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase5_3_telemetry_producer.py -q
```

Run streaming regression:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase5_streaming_foundation.py backend\tests\test_phase5_topic_management.py backend\tests\test_phase5_3_telemetry_producer.py -q
```

Run full backend regression:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```