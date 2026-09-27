# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Message type indicators: the MTI that answers a request or an advice."""

from __future__ import annotations


def response_mti(mti: str, keep_repeat: bool = False) -> str:
    """The MTI that answers a request or an advice: its function digit plus one.

    0100 is answered with 0110, 0120 with 0130, 0400 with 0410, 0800 with 0810.

    Args:
        mti: The request's or advice's MTI
        keep_repeat: Keep a repeat's flag in the answer (0121 with 0131)

    Returns:
        The response MTI. A repeat (0101, 0121, 0401, 0421) is answered as the message it
        repeats, without the repeat flag: 0121 with 0130, 0421 with 0430.

    Raises:
        ValueError: If the MTI isn't four digits, or is already a response
    """
    if len(mti) != 4 or not mti.isdigit():
        raise ValueError(f"{mti!r} is not an MTI")
    function, origin = int(mti[2]), int(mti[3])
    if function % 2:
        raise ValueError(f"MTI {mti} is already a response")
    # subhadipmitra@: The common convention, which jPOS follows too: the origin digit's repeat
    # flag (its low bit, for origins 0 to 5) is dropped, so 0 and 1 answer as 0, 2 and 3 as 2,
    # 4 and 5 as 4. Some systems expect the flag kept, hence keep_repeat.
    if not keep_repeat and origin <= 5:
        origin -= origin % 2
    return f"{mti[:2]}{function + 1}{origin}"
