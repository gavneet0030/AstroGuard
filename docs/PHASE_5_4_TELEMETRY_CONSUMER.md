# AstroGuard Phase 5.4 — Telemetry Consumer

## Objective

Introduce an application-level consumer abstraction over the existing streaming broker interface.

This phase adds sequential message consumption, handler execution, bounded batch processing, timeout handling, and acknowledgement after successful handler completion.

## Components

- `streaming/consumer.py`
  - `TelemetryConsumer`
  - `ConsumeResult`
  - `ConsumeBatchResult`
  - `ConsumerError`
  - `ConsumerConfigurationError`
  - `ConsumerMessageError`

- `streaming/broker.py`
  - Existing broker protocol and in-memory development implementation.

## Consumption behaviour

The consumer:

1. Validates the requested registered topic.
2. Retrieves messages through the configured broker interface.
3. Executes the configured message handler.
4. Acknowledges a message only after successful handler completion.
5. Leaves a handler-failed message unacknowledged.
6. Processes batch messages sequentially, subject to configured limits.

The consumer does not create an unbounded set of asynchronous handler tasks.

## Acknowledgement semantics

Acknowledgement is an application-level operation delegated to the configured broker.

For the current in-memory implementation, consumption and acknowledgement use local queue operations. This is not equivalent to a durable broker acknowledgement protocol.

A successful handler followed by a successful local acknowledgement indicates successful processing within the local implementation. It does not establish durable delivery, exactly-once processing, or cross-process recovery.

A handler failure does not result in acknowledgement.

## Timeout and failure limitations

A handler timeout or failure may leave a message unacknowledged after it has already been retrieved from the in-memory queue.

The current implementation does not establish automatic redelivery, durable retry scheduling, or a persistent dead-letter lifecycle.

These limitations must not be described as production retry guarantees.

Retry and dead-letter management are addressed separately in the subsequent streaming roadmap.

## Resource and execution policy

- Sequential handler execution.
- Bounded batch size.
- Configurable consumption timeout.
- No unbounded task creation.
- No external broker dependency required for local tests.

## Infrastructure limitations

The current consumer implementation does not provide:

- Kafka or Redpanda connectivity.
- Persistent offsets.
- Durable acknowledgement.
- Consumer-group coordination.
- Cross-process message recovery.
- Exactly-once processing.
- Guaranteed retry or redelivery.
- Distributed ordering guarantees.

The in-memory broker remains development and test infrastructure.

## Safety boundaries

This phase does not:

- Modify the database schema.
- Execute database migrations.
- Modify NASA source datasets.
- Change training or test-label boundaries.
- Promote an ML model to production.
- Start Docker, Kafka, or Redpanda services.
- Establish spacecraft operational or flight-safety readiness.

## Validation

Run focused consumer tests:

```powershell
$env:PYTHONPATH = "backend"

.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase5_4_telemetry_consumer.py -q
```

Run streaming regression:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase5_streaming_foundation.py backend\tests\test_phase5_topic_management.py backend\tests\test_phase5_3_telemetry_producer.py backend\tests\test_phase5_4_telemetry_consumer.py -q
```

Run the complete backend suite:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

## Acceptance evidence

Record the actual results for:

- Python compilation.
- Focused consumer tests.
- Combined streaming regression.
- Full backend regression.
- Dependency consistency.
- Database baseline integrity.

A test result must be supported by its actual terminal output. No external broker capability is inferred from in-memory test results.