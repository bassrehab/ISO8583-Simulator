# iso8583sim/core/pool.py
"""Object pooling for high-throughput ISO8583 message processing."""

from collections import deque
from threading import Lock

from .types import CardNetwork, ISO8583Message, ISO8583Version


class MessagePool:
    """
    Thread-safe object pool for ISO8583Message instances.

    Using a pool reduces object allocation overhead in high-throughput
    scenarios by reusing message objects instead of creating new ones.

    Usage:
        pool = MessagePool(size=100)

        # Get a message from the pool
        msg = pool.acquire("0100", {2: "4111111111111111"})

        # Process the message...

        # Return it to the pool when done
        pool.release(msg)

    Note: Messages returned to the pool have their fields cleared,
    so don't hold references to field data after releasing.
    """

    __slots__ = ("_pool", "_lock", "_max_size")

    def __init__(self, size: int = 100):
        """
        Initialize the message pool.

        Args:
            size: Maximum number of messages to keep in the pool
        """
        self._pool: deque[ISO8583Message] = deque(maxlen=size)
        self._lock = Lock()
        self._max_size = size

    def acquire(
        self,
        mti: str,
        fields: dict[int, str],
        version: ISO8583Version = ISO8583Version.V1987,
        network: CardNetwork | None = None,
        raw_message: str | None = None,
        bitmap: str | None = None,
    ) -> ISO8583Message:
        """
        Get a message from the pool or create a new one.

        Args:
            mti: Message Type Indicator
            fields: Message fields dictionary
            version: ISO8583 version
            network: Card network
            raw_message: Original raw message string
            bitmap: Message bitmap

        Returns:
            An ISO8583Message instance (either recycled or new)
        """
        msg = None

        with self._lock:
            if self._pool:
                msg = self._pool.pop()

        if msg is not None:
            # Reset the pooled message with new values
            msg.mti = mti
            msg.fields = fields.copy() if fields else {}
            msg.version = version
            msg.network = network
            msg.raw_message = raw_message
            msg.bitmap = bitmap
            # Re-run post_init logic
            if mti:
                msg.fields[0] = mti
            return msg

        # No pooled message available, create new one
        return ISO8583Message(
            mti=mti,
            fields=fields.copy() if fields else {},
            version=version,
            network=network,
            raw_message=raw_message,
            bitmap=bitmap,
        )

    def release(self, msg: ISO8583Message) -> None:
        """
        Return a message to the pool for reuse.

        Args:
            msg: The message to return to the pool

        Note: The message's fields are cleared to avoid holding
        references to old data.
        """
        # Clear the message to free memory
        msg.fields.clear()
        msg.raw_message = None
        msg.bitmap = None

        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(msg)

    def clear(self) -> None:
        """Clear all messages from the pool."""
        with self._lock:
            self._pool.clear()

    @property
    def size(self) -> int:
        """Get current number of messages in the pool."""
        with self._lock:
            return len(self._pool)

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size


# Global default pool for convenience
_default_pool: MessagePool | None = None


def get_default_pool(size: int = 100) -> MessagePool:
    """
    Get or create the default global message pool.

    Args:
        size: Pool size (only used on first call)

    Returns:
        The default MessagePool instance
    """
    global _default_pool
    if _default_pool is None:
        _default_pool = MessagePool(size=size)
    return _default_pool


def reset_default_pool() -> None:
    """Reset the default global pool."""
    global _default_pool
    if _default_pool is not None:
        _default_pool.clear()
    _default_pool = None
