"""
Edge Case and Invalid Input Tests.
Verifies pipeline resilience against bad inputs, missing files, and corrupted data:
1. Negative or NaN dimensions.
2. Malformed JSON syntax in size charts.
3. Corrupt or truncated image files.
4. Broken / corrupt zip package archives.
5. Unknown sizes or missing manifest files.
"""

import os
import json
import tempfile
import zipfile
import pytest
from PIL import Image

from src.garment_template.sizing import SizingEngine
from src.garment_template.patterns import PatternGenerator
from src.garment_template.vision import GarmentVisionAnalyzer
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


def test_malformed_size_chart_json():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write("{ bad_json: unquoted, ")
        bad_path = f.name
    try:
        with pytest.raises(json.JSONDecodeError):
            SizingEngine(bad_path)
    finally:
        os.remove(bad_path)


def test_corrupt_or_truncated_image():
    with tempfile.NamedTemporaryFile("wb", suffix=".jpg", delete=False) as f:
        f.write(b"NOT_AN_IMAGE_FILE_RANDOM_BYTES_12345")
        corrupt_path = f.name
    try:
        with pytest.raises(Exception):  # PIL raises UnidentifiedImageError
            analyzer = GarmentVisionAnalyzer(corrupt_path)
            analyzer.extract_silhouette_measurements()
    finally:
        os.remove(corrupt_path)


def test_corrupt_zip_package():
    with tempfile.NamedTemporaryFile("wb", suffix=".zip", delete=False) as f:
        f.write(b"PK\x03\x04CORRUPTED_ZIP_BYTES")
        bad_zip = f.name
    try:
        with pytest.raises(Exception):
            load_template(bad_zip)
    finally:
        os.remove(bad_zip)


def test_negative_dimensions_rejected():
    bad_dims = {
        "bust_circ": -82.0,
        "waist_circ": 70.0,
        "hip_circ": 90.0,
        "hem_circ": 110.0,
        "front_length": 88.0,
        "back_length": 90.0
    }
    with pytest.raises(ValueError, match="Invalid dimension"):
        PatternGenerator(bad_dims)

    nan_dims = {
        "bust_circ": float("nan"),
        "waist_circ": 70.0,
        "hip_circ": 90.0,
        "hem_circ": 110.0,
        "front_length": 88.0,
        "back_length": 90.0
    }
    with pytest.raises(ValueError, match="Invalid dimension"):
        PatternGenerator(nan_dims)


def test_range_lower_bound_parsing():
    assert SizingEngine.resolve_range_lower("78-82") == 78.0
    assert SizingEngine.resolve_range_lower("32-34") == 32.0
    assert SizingEngine.resolve_range_lower(74) == 74.0
    assert SizingEngine.resolve_range_lower("85") == 85.0
