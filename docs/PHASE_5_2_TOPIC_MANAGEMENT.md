# AstroGuard Phase 5.2 — Broker Abstraction and Topic Management

## Objective

Provide a broker-independent topic administration interface and a
validated registry of application streaming topics.

## Components

- `streaming/topics.py`
  - Topic enum
  - TopicSpec
  - TOPIC_REGISTRY
  - Topic resolution
  - Partition, retention and message-size configuration

- `streaming/topic_admin.py`
  - TopicAdminProtocol
  - InMemoryTopicAdmin
  - Idempotent topic provisioning
  - Topic inspection
  - Registered-topic validation

## Registered topics

| Topic | Partitions | Replication | Retention |
|---|---:|---:|---:|
| astroguard.telemetry.raw | 2 | 1 | 1 day |
| astroguard.telemetry.validated | 2 | 1 | 7 days |
| astroguard.anomalies.detected | 1 | 1 | 7 days |
| astroguard.events.dead-letter | 1 | 1 | 30 days |

These values are application-level desired configuration.
The in-memory implementation does not enforce broker retention.

## Idempotency

Repeated provisioning of an identical topic configuration does not
create a duplicate topic.

A conflicting configuration for an existing topic raises
TopicAlreadyExistsError.

## Resource policy

Local development uses in-memory administration only.

No Kafka, Redpanda, Docker or Redis service is started in this phase.

## Limitations

The local implementation is not durable or distributed.
It does not create physical broker topics.
It does not enforce partitioning or replication.
It does not provide broker ACLs or retention enforcement.

## Safety

No database schema, migration, Phase 3 ML code, raw data or
processed NASA datasets are modified.

## Acceptance

- Topic configuration validation passes.
- Topic provisioning tests pass.
- Idempotency tests pass.
- Full backend regression passes.
- Dependency consistency passes.