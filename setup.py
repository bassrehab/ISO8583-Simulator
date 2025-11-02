"""Setup script for building Cython extensions."""

from setuptools import setup

try:
    from Cython.Build import cythonize

    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False


def get_extensions():
    """Get list of extensions to build."""
    if not USE_CYTHON:
        return []

    return cythonize(
        [
            "iso8583sim/core/_bitmap.pyx",
            "iso8583sim/core/_parser_fast.pyx",
            "iso8583sim/core/_validator_fast.pyx",
        ],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
        },
    )


if __name__ == "__main__":
    setup(
        ext_modules=get_extensions(),
    )
