"""Phase 5.2 topic administration and configuration tests."""

import asyncio
from dataclasses import replace

import pytest

from astroguard_api.streaming.topics import (
    Topic,
    TopicSpec,
    TOPIC_REGISTRY,
    resolve_topic,
    get_all_topic_specs,
)

from astroguard_api.streaming.topic_admin import (
    InMemoryTopicAdmin,
    TopicAlreadyExistsError,
    TopicNotFoundError,
    TopicAdminClosedError,
    validate_topic_name,
)


def test_topic_registry_has_four_unique_topics():
    specs = get_all_topic_specs()

    assert len(specs) == 4
    assert len({spec.name for spec in specs}) == 4


def test_all_topics_have_valid_configuration():
    for spec in TOPIC_REGISTRY.values():
        assert spec.partitions >= 1
        assert spec.replication_factor >= 1
        assert spec.retention_ms >= 60000
        assert spec.cleanup_policy in {"delete", "compact"}
        assert 1024 <= spec.max_message_bytes <= 10485760


def test_topic_spec_rejects_invalid_partition_count():
    with pytest.raises(ValueError):
        TopicSpec(
            name="invalid.topic",
            description="Invalid",
            retention_class="short",
            partitions=0,
        )


def test_topic_spec_rejects_invalid_replication_factor():
    with pytest.raises(ValueError):
        TopicSpec(
            name="invalid.topic",
            description="Invalid",
            retention_class="short",
            replication_factor=0,
        )


def test_topic_spec_rejects_invalid_retention():
    with pytest.raises(ValueError):
        TopicSpec(
            name="invalid.topic",
            description="Invalid",
            retention_class="short",
            retention_ms=100,
        )


def test_topic_spec_rejects_invalid_cleanup_policy():
    with pytest.raises(ValueError):
        TopicSpec(
            name="invalid.topic",
            description="Invalid",
            retention_class="short",
            cleanup_policy="unknown",
        )


def test_topic_spec_rejects_oversized_messages():
    with pytest.raises(ValueError):
        TopicSpec(
            name="invalid.topic",
            description="Invalid",
            retention_class="short",
            max_message_bytes=20000000,
        )


def test_topic_name_validation():
    assert validate_topic_name(Topic.TELEMETRY_RAW.value) == (
        "astroguard.telemetry.raw"
    )

    with pytest.raises(ValueError):
        validate_topic_name("unregistered.topic")


def test_topic_admin_provisions_registered_topics():
    async def scenario():
        admin = InMemoryTopicAdmin()

        created = await admin.ensure_topics()

        assert len(created) == 4

        topics = await admin.list_topics()
        assert len(topics) == 4

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_provisioning_is_idempotent():
    async def scenario():
        admin = InMemoryTopicAdmin()

        first = await admin.ensure_topics()
        second = await admin.ensure_topics()

        assert len(first) == 4
        assert second == ()

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_describes_existing_topic():
    async def scenario():
        admin = InMemoryTopicAdmin()
        await admin.ensure_topics()

        spec = await admin.describe_topic(
            Topic.TELEMETRY_RAW.value
        )

        assert spec == resolve_topic(Topic.TELEMETRY_RAW)

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_rejects_unknown_topic():
    async def scenario():
        admin = InMemoryTopicAdmin()

        with pytest.raises(TopicNotFoundError):
            await admin.describe_topic("unknown.topic")

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_detects_conflicting_configuration():
    async def scenario():
        admin = InMemoryTopicAdmin()
        original = resolve_topic(Topic.TELEMETRY_RAW)

        await admin.create_topic(original)

        conflicting = replace(original, partitions=3)

        with pytest.raises(TopicAlreadyExistsError):
            await admin.create_topic(conflicting)

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_validates_registered_topics():
    async def scenario():
        admin = InMemoryTopicAdmin()

        await admin.ensure_topics()

        results = await admin.validate_registered_topics()

        assert len(results) == 4
        assert all(results.values())

        await admin.close()

    asyncio.run(scenario())


def test_topic_admin_rejects_operations_after_close():
    async def scenario():
        admin = InMemoryTopicAdmin()
        await admin.close()

        with pytest.raises(TopicAdminClosedError):
            await admin.list_topics()

    asyncio.run(scenario())


def test_topic_admin_rejects_invalid_spec_type():
    async def scenario():
        admin = InMemoryTopicAdmin()

        with pytest.raises(TypeError):
            await admin.create_topic("not-a-topic-spec")

        await admin.close()

    asyncio.run(scenario())