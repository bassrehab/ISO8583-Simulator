"""Build the optional Cython extensions.

Package metadata lives in pyproject.toml. This file only declares the compiled modules.
"""

from setuptools import Extension, setup

try:
    from Cython.Build import cythonize

    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False

MODULES = ["_bitmap", "_parser_fast", "_validator_fast"]

# subhadipmitra@: optional=True means a failed compile (no C compiler, unusual platform) is a
# warning, not an install error. The package has pure-Python fallbacks for every compiled
# module, so it still works, just without the speedup.
EXTENSIONS = [Extension(f"iso8583sim.core.{name}", [f"iso8583sim/core/{name}.pyx"], optional=True) for name in MODULES]


def get_extensions():
    """Cythonize the extensions, or build none when Cython isn't installed."""
    if not USE_CYTHON:
        return []
    extensions = cythonize(
        EXTENSIONS,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
        },
    )
    # subhadipmitra@: cythonize() returns new Extension objects and drops the optional flag,
    # which made a failed compile fatal. Set it again on what it returns.
    for extension in extensions:
        extension.optional = True
    return extensions


setup(ext_modules=get_extensions())
