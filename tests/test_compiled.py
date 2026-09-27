# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Check that compiled wheels really load their Cython extensions.

Skipped unless ISO8583SIM_REQUIRE_CYTHON=1, which the wheel build (cibuildwheel) sets.
Without this, a wheel whose extensions failed to build would still pass every other test,
because each compiled module has a pure-Python fallback.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ISO8583SIM_REQUIRE_CYTHON") != "1", reason="only checked when building compiled wheels"
)


def test_extensions_are_loaded():
    from iso8583sim.core import _bitmap, _parser_fast, _validator_fast, parser, validator

    assert parser._USE_CYTHON
    assert validator._USE_CYTHON
    # subhadipmitra@: The compiled modules have no __file__ ending in .py when built.
    for module in (_bitmap, _parser_fast, _validator_fast):
        assert not module.__file__.endswith(".py"), module.__file__
