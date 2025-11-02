# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""Optimized validation functions using Cython."""

from libc.stdint cimport uint8_t


cpdef bint validate_pan_luhn(str pan):
    """
    Validate Primary Account Number using Luhn algorithm.

    This is a Cython-optimized version that operates directly on
    ASCII character codes without creating intermediate lists.

    Args:
        pan: Card number string (digits only)

    Returns:
        True if valid according to Luhn algorithm, False otherwise
    """
    cdef:
        bytes pan_bytes
        const unsigned char* bp
        int length, i, checksum, d
        int odd_even

    # First check if all digits
    pan_bytes = pan.encode('ascii')
    bp = pan_bytes
    length = len(pan)

    if length == 0:
        return False

    # Validate all digits
    for i in range(length):
        if bp[i] < 48 or bp[i] > 57:  # '0' = 48, '9' = 57
            return False

    # Luhn algorithm
    checksum = 0
    odd_even = length % 2

    for i in range(length - 1, -1, -1):
        d = bp[i] - 48  # Convert ASCII to digit
        if i % 2 == odd_even:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d

    return (checksum % 10) == 0


cpdef bint is_valid_hex(str s):
    """
    Check if string contains only valid hexadecimal characters.

    Args:
        s: String to validate

    Returns:
        True if valid hex string, False otherwise
    """
    cdef:
        bytes s_bytes = s.encode('ascii')
        const unsigned char* bp = s_bytes
        int i, length = len(s)
        unsigned char c

    for i in range(length):
        c = bp[i]
        # Check if 0-9, A-F, or a-f
        if not ((c >= 48 and c <= 57) or   # 0-9
                (c >= 65 and c <= 70) or   # A-F
                (c >= 97 and c <= 102)):   # a-f
            return False

    return True


cpdef bint is_numeric(str s):
    """
    Check if string contains only numeric characters.

    Args:
        s: String to check

    Returns:
        True if all characters are digits
    """
    cdef:
        bytes s_bytes = s.encode('ascii')
        const unsigned char* bp = s_bytes
        int i, length = len(s)

    for i in range(length):
        if bp[i] < 48 or bp[i] > 57:
            return False

    return True


cpdef bint is_alpha(str s):
    """
    Check if string contains only alphabetic characters (and spaces).

    Args:
        s: String to check

    Returns:
        True if all characters are letters or spaces
    """
    cdef:
        bytes s_bytes = s.encode('ascii')
        const unsigned char* bp = s_bytes
        int i, length = len(s)
        unsigned char c

    for i in range(length):
        c = bp[i]
        # Check if A-Z, a-z, or space
        if not ((c >= 65 and c <= 90) or   # A-Z
                (c >= 97 and c <= 122) or  # a-z
                c == 32):                   # space
            return False

    return True


cpdef bint is_alphanumeric(str s):
    """
    Check if string contains only alphanumeric characters (and spaces).

    Args:
        s: String to check

    Returns:
        True if all characters are letters, digits, or spaces
    """
    cdef:
        bytes s_bytes = s.encode('ascii')
        const unsigned char* bp = s_bytes
        int i, length = len(s)
        unsigned char c

    for i in range(length):
        c = bp[i]
        # Check if 0-9, A-Z, a-z, or space
        if not ((c >= 48 and c <= 57) or   # 0-9
                (c >= 65 and c <= 90) or   # A-Z
                (c >= 97 and c <= 122) or  # a-z
                c == 32):                   # space
            return False

    return True


cpdef bint validate_mti_format(str mti):
    """
    Validate MTI format (4 digits, valid version and message class).

    Args:
        mti: 4-digit MTI string

    Returns:
        True if valid MTI format
    """
    cdef:
        bytes mti_bytes
        const unsigned char* bp
        unsigned char version, msg_class

    if len(mti) != 4:
        return False

    mti_bytes = mti.encode('ascii')
    bp = mti_bytes

    # Check all digits
    for i in range(4):
        if bp[i] < 48 or bp[i] > 57:
            return False

    # Check version (position 0): must be 0 or 1
    version = bp[0] - 48
    if version > 1:
        return False

    # Check message class (position 1): must be 1-6, 8, or 9
    msg_class = bp[1] - 48
    if msg_class == 0 or msg_class == 7:
        return False

    return True
