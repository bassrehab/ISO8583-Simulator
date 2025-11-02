# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""Optimized bitmap parsing functions using Cython."""

from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.stdint cimport uint64_t, uint8_t

# Hex character to value lookup table
cdef uint8_t[256] HEX_VALUES
cdef bint _initialized = False


cdef void _init_hex_values():
    """Initialize the hex lookup table."""
    global _initialized
    cdef int i

    # Initialize all to 255 (invalid)
    for i in range(256):
        HEX_VALUES[i] = 255

    # Set valid hex values
    for i in range(10):
        HEX_VALUES[ord('0') + i] = i
    for i in range(6):
        HEX_VALUES[ord('A') + i] = 10 + i
        HEX_VALUES[ord('a') + i] = 10 + i

    _initialized = True


cpdef list get_present_fields_fast(str bitmap):
    """
    Get list of present fields from bitmap using optimized bit manipulation.

    Args:
        bitmap: Hexadecimal bitmap string (16 or 32 chars)

    Returns:
        List of field numbers that are present (excluding 1 and 65)
    """
    global _initialized
    if not _initialized:
        _init_hex_values()

    cdef:
        int bitmap_len = len(bitmap)
        int num_bits = bitmap_len * 4
        list present_fields = []
        int i, bit_pos, field_number
        uint64_t primary = 0, secondary = 0
        uint64_t bitmap_int
        bytes bitmap_bytes = bitmap.encode('ascii')
        const unsigned char* bp = bitmap_bytes
        uint8_t hex_val

    # Parse primary bitmap (first 16 hex chars = 64 bits)
    for i in range(min(16, bitmap_len)):
        hex_val = HEX_VALUES[bp[i]]
        if hex_val > 15:
            raise ValueError(f"Invalid hex character at position {i}")
        primary = (primary << 4) | hex_val

    # Parse secondary bitmap if present (next 16 hex chars)
    if bitmap_len == 32:
        for i in range(16, 32):
            hex_val = HEX_VALUES[bp[i]]
            if hex_val > 15:
                raise ValueError(f"Invalid hex character at position {i}")
            secondary = (secondary << 4) | hex_val

    # Extract set bits from primary bitmap (bits 2-64, skip bit 1)
    for bit_pos in range(1, 64):  # bit_pos 0 is bit 1, skip it
        if primary & (1ULL << (63 - bit_pos)):
            field_number = bit_pos + 1
            present_fields.append(field_number)

    # Extract set bits from secondary bitmap if present (bits 66-128, skip bit 65)
    if bitmap_len == 32:
        for bit_pos in range(1, 64):  # bit_pos 0 is bit 65, skip it
            if secondary & (1ULL << (63 - bit_pos)):
                field_number = 64 + bit_pos + 1
                present_fields.append(field_number)

    return present_fields


cpdef str build_bitmap_fast(dict fields):
    """
    Build bitmap from present fields using optimized operations.

    Args:
        fields: Dictionary of field_number -> value

    Returns:
        Hexadecimal bitmap string (16 or 32 chars)
    """
    cdef:
        uint64_t primary = 0, secondary = 0
        bint need_secondary = False
        int field_number
        str result

    for field_number in fields:
        if field_number == 0:  # Skip MTI
            continue

        if 1 <= field_number <= 64:
            primary |= (1ULL << (64 - field_number))
        elif 65 <= field_number <= 128:
            secondary |= (1ULL << (128 - field_number))
            need_secondary = True

    if need_secondary:
        # Set bit 1 to indicate secondary bitmap present
        primary |= (1ULL << 63)
        result = format(primary, '016X') + format(secondary, '016X')
    else:
        result = format(primary, '016X')

    return result


cpdef bint validate_hex_string(str s):
    """
    Validate that a string contains only hexadecimal characters.

    Args:
        s: String to validate

    Returns:
        True if valid hex, False otherwise
    """
    global _initialized
    if not _initialized:
        _init_hex_values()

    cdef:
        bytes s_bytes = s.encode('ascii')
        const unsigned char* bp = s_bytes
        int i, length = len(s)

    for i in range(length):
        if HEX_VALUES[bp[i]] > 15:
            return False

    return True
