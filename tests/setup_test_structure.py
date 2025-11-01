# tests/setup_test_structure.py
from pathlib import Path


def create_test_structure():
    """Create test directory structure"""
    # Get the base directory
    base_dir = Path(__file__).parent

    # Create test data directory
    test_data_dir = base_dir / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (test_data_dir / "messages").mkdir(exist_ok=True)
    (test_data_dir / "configs").mkdir(exist_ok=True)
    (test_data_dir / "results").mkdir(exist_ok=True)

    # Create __init__.py files
    (base_dir / "__init__.py").touch()
    (test_data_dir / "__init__.py").touch()


if __name__ == "__main__":
    create_test_structure()
