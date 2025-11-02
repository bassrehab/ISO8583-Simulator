# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""Optimized parsing functions using Cython."""

from libc.stdint cimport uint8_t


cpdef tuple parse_mti_fast(str message, int position):
    """
    Parse Message Type Indicator from message.

    Args:
        message: Raw message string
        position: Current position in message

    Returns:
        Tuple of (mti, new_position) or raises ValueError
    """
    cdef int msg_len = len(message)

    if msg_len < position + 4:
        raise ValueError("Message too short for MTI")

    cdef str mti = message[position:position + 4]

    # Validate MTI is all digits
    cdef bytes mti_bytes = mti.encode('ascii')
    cdef const unsigned char* bp = mti_bytes
    cdef int i

    for i in range(4):
        if bp[i] < 48 or bp[i] > 57:  # '0' = 48, '9' = 57
            raise ValueError("Invalid MTI format - must be numeric")

    return (mti, position + 4)


cpdef tuple parse_bitmap_fast(str message, int position):
    """
    Parse primary and secondary bitmaps.

    Args:
        message: Raw message string
        position: Current position in message

    Returns:
        Tuple of (bitmap, new_position, has_secondary)
    """
    cdef int msg_len = len(message)
    cdef str primary
    cdef str secondary
    cdef str first_char
    cdef int new_pos
    cdef bint has_secondary

    if msg_len < position + 16:
        raise ValueError("Message too short for bitmap")

    primary = message[position:position + 16]
    new_pos = position + 16

    # Check for secondary bitmap (first hex char indicates bit 1)
    first_char = primary[0]
    has_secondary = first_char in ('8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                                   'a', 'b', 'c', 'd', 'e', 'f')

    if has_secondary:
        if msg_len < new_pos + 16:
            raise ValueError("Message too short for secondary bitmap")
        secondary = message[new_pos:new_pos + 16]
        new_pos += 16
        return (primary + secondary, new_pos, True)

    return (primary, new_pos, False)


cpdef tuple parse_length_indicator(str message, int position, int indicator_size):
    """
    Parse length indicator for variable-length fields.

    Args:
        message: Raw message string
        position: Current position in message
        indicator_size: Size of length indicator (2 for LLVAR, 3 for LLLVAR)

    Returns:
        Tuple of (length, new_position)
    """
    cdef int msg_len = len(message)

    if msg_len < position + indicator_size:
        raise ValueError("Message too short for length indicator")

    cdef str length_str = message[position:position + indicator_size]

    # Validate all digits
    cdef bytes length_bytes = length_str.encode('ascii')
    cdef const unsigned char* bp = length_bytes
    cdef int i
    cdef int length = 0

    for i in range(indicator_size):
        if bp[i] < 48 or bp[i] > 57:  # '0' = 48, '9' = 57
            raise ValueError(f"Invalid length indicator: {length_str}")
        length = length * 10 + (bp[i] - 48)

    return (length, position + indicator_size)


cpdef str extract_fixed_field(str message, int position, int length):
    """
    Extract a fixed-length field from message.

    Args:
        message: Raw message string
        position: Current position in message
        length: Field length to extract

    Returns:
        Field value string
    """
    cdef int msg_len = len(message)

    if msg_len < position + length:
        raise ValueError("Message too short for field")

    return message[position:position + length]


cpdef bint is_numeric_string(str s):
    """
    Check if string contains only numeric characters.

    Args:
        s: String to check

    Returns:
        True if all characters are digits
    """
    cdef bytes s_bytes = s.encode('ascii')
    cdef const unsigned char* bp = s_bytes
    cdef int i, length = len(s)

    for i in range(length):
        if bp[i] < 48 or bp[i] > 57:
            return False

    return True


cpdef str pad_numeric(str value, int target_length):
    """
    Left-pad a numeric string with zeros.

    Args:
        value: String to pad
        target_length: Target length

    Returns:
        Padded string
    """
    cdef int current_len = len(value)

    if current_len >= target_length:
        return value

    return '0' * (target_length - current_len) + value
