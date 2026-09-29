"""
End-to-End Pipeline and Round-Trip Read-Back Tests.
"""

import os
import pytest

from src.garment_template.pipeline import PipelineOrchestrator
from src.garment_template.loader import load_template


@pytest.fixture(scope="module")
def pipeline_run_result():
    test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    size_chart = os.path.join(test_root, "samples", "size_chart.json")
    details = os.path.join(test_root, "samples", "product_details.json")
    avatar_glb = os.path.join(test_root, "assets", "person_0.glb")
    output_dir = os.path.join(test_root, "output")

    orchestrator = PipelineOrchestrator(
        size_chart_path=size_chart,
        product_details_path=details,
        avatar_glb_path=avatar_glb,
        output_dir=output_dir
    )
    pkg_dir, val_report, loaded = orchestrator.run()
    return {
        "pkg_dir": pkg_dir,
        "report": val_report,
        "loaded": loaded,
        "output_dir": output_dir
    }


def test_pipeline_runs_successfully(pipeline_run_result):
    assert pipeline_run_result["report"].passed is True
    assert len(pipeline_run_result["report"].checks) >= 30


def test_roundtrip_load_from_directory(pipeline_run_result):
    pkg = load_template(pipeline_run_result["pkg_dir"])
    assert pkg.manifest.base_size == "XS"
    assert len(pkg.patterns_2d) == 4
    assert len(pkg.meshes) == 4
    assert len(pkg.sewing_connections) == 8
    assert pkg.mannequin_ref.joint_count == 52
    assert set(pkg.grading_info.size_meshes.keys()) == {"XXS", "XS", "S", "M"}


def test_roundtrip_load_from_zip(pipeline_run_result):
    zip_path = os.path.join(pipeline_run_result["output_dir"], "garment_template_package.zip")
    assert os.path.exists(zip_path)
    pkg = load_template(zip_path)
    assert pkg.manifest.brand == "H&M"
    assert pkg.manifest.category == "Women's Dresses"
    assert len(pkg.placements) == 4
