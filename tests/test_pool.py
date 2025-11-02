# tests/test_pool.py
"""Tests for the object pool."""

from iso8583sim.core.pool import MessagePool, get_default_pool, reset_default_pool
from iso8583sim.core.types import ISO8583Version


class TestMessagePool:
    """Tests for MessagePool class."""

    def test_pool_creation(self):
        """Test pool can be created with specified size."""
        pool = MessagePool(size=50)
        assert pool.max_size == 50
        assert pool.size == 0

    def test_acquire_creates_new_message(self):
        """Test acquire creates a new message when pool is empty."""
        pool = MessagePool(size=10)
        msg = pool.acquire(mti="0100", fields={2: "4111111111111111"})

        assert msg.mti == "0100"
        assert msg.fields[2] == "4111111111111111"
        assert msg.fields[0] == "0100"  # MTI is added as field 0

    def test_release_and_acquire_reuses_message(self):
        """Test that released messages are reused."""
        pool = MessagePool(size=10)

        # Create and release a message
        msg1 = pool.acquire(mti="0100", fields={2: "4111111111111111"})
        pool.release(msg1)

        assert pool.size == 1

        # Acquire should reuse the released message
        msg2 = pool.acquire(mti="0200", fields={3: "000000"})

        assert pool.size == 0
        assert msg2.mti == "0200"
        assert msg2.fields[3] == "000000"

    def test_pool_respects_max_size(self):
        """Test that pool doesn't exceed max size."""
        pool = MessagePool(size=2)

        msgs = [pool.acquire(mti="0100", fields={}) for _ in range(5)]
        for msg in msgs:
            pool.release(msg)

        # Pool should only keep max_size messages
        assert pool.size == 2

    def test_acquire_with_all_parameters(self):
        """Test acquire with all parameters."""
        pool = MessagePool(size=10)
        msg = pool.acquire(
            mti="0100",
            fields={2: "4111111111111111", 3: "000000"},
            version=ISO8583Version.V1993,
            network=None,
            raw_message="raw_data",
            bitmap="8000000000000000",
        )

        assert msg.mti == "0100"
        assert msg.version == ISO8583Version.V1993
        assert msg.raw_message == "raw_data"
        assert msg.bitmap == "8000000000000000"

    def test_clear_empties_pool(self):
        """Test that clear empties the pool."""
        pool = MessagePool(size=10)

        msgs = [pool.acquire(mti="0100", fields={}) for _ in range(5)]
        for msg in msgs:
            pool.release(msg)

        assert pool.size == 5
        pool.clear()
        assert pool.size == 0


class TestDefaultPool:
    """Tests for default pool functions."""

    def teardown_method(self):
        """Reset default pool after each test."""
        reset_default_pool()

    def test_get_default_pool_creates_pool(self):
        """Test that get_default_pool creates a pool."""
        pool = get_default_pool()
        assert pool is not None
        assert pool.max_size == 100  # Default size

    def test_get_default_pool_returns_same_instance(self):
        """Test that get_default_pool returns the same instance."""
        pool1 = get_default_pool()
        pool2 = get_default_pool()
        assert pool1 is pool2

    def test_reset_default_pool(self):
        """Test that reset_default_pool clears and resets."""
        pool1 = get_default_pool()
        msg = pool1.acquire(mti="0100", fields={})
        pool1.release(msg)
        assert pool1.size == 1

        reset_default_pool()
        pool2 = get_default_pool()

        assert pool2 is not pool1
        assert pool2.size == 0
