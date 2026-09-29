"""
Edge Case and Invalid Input Tests.
Verifies pipeline resilience against bad inputs, missing files, and corrupted data.
"""

import os
import tempfile
import pytest
from src.garment_template.sizing import SizingEngine
from src.garment_template.loader import load_template


def test_unknown_size_raises_error():
    test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chart_path = os.path.join(test_root, "samples", "size_chart.json")
    sizing = SizingEngine(chart_path)
    with pytest.raises(ValueError, match="Unknown size 'XXXL'"):
        sizing.get_garment_dimensions("XXXL")


def test_missing_manifest_raises_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError, match="Missing manifest.json"):
            load_template(tmpdir)


def test_nonexistent_package_path():
    with pytest.raises(FileNotFoundError):
        load_template("/non/existent/path/package")


def test_range_lower_bound_parsing():
    assert SizingEngine.resolve_range_lower("78-82") == 78.0
    assert SizingEngine.resolve_range_lower("32-34") == 32.0
    assert SizingEngine.resolve_range_lower(74) == 74.0
    assert SizingEngine.resolve_range_lower("85") == 85.0
