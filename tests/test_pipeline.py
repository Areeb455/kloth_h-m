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
    front_img = os.path.join(test_root, "samples", "front.jpg")
    back_img = os.path.join(test_root, "samples", "back.jpg")
    output_dir = os.path.join(test_root, "output")

    orchestrator = PipelineOrchestrator(
        size_chart_path=size_chart,
        product_details_path=details,
        avatar_glb_path=avatar_glb,
        front_image_path=front_img,
        back_image_path=back_img,
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
    report = pipeline_run_result["report"]
    assert len(report.checks) >= 20
    # Core collision, seam closure, and stability checks must strictly pass
    collision_check = next(c for c in report.checks if "Avatar Real Mesh Non-Penetration" in c["name"])
    assert collision_check["status"] == "PASS", f"Avatar penetration failed: {collision_check['details']}"
    seam_check = next(c for c in report.checks if "Seam Assembly Gap" in c["name"])
    assert seam_check["status"] == "PASS", f"Seam gap failed: {seam_check['details']}"
    stability_check = next(c for c in report.checks if "Simulation Stability" in c["name"])
    assert stability_check["status"] == "PASS"
    assert os.path.exists(pipeline_run_result["pkg_dir"])


def test_roundtrip_load_from_directory(pipeline_run_result):
    pkg = load_template(pipeline_run_result["pkg_dir"])
    assert pkg.manifest.base_size == "XS"
    assert len(pkg.patterns_2d) == 3  # front_panel, back_left_panel, back_right_panel
    assert len(pkg.meshes) == 3
    assert len(pkg.sewing_connections) == 5  # 2 shoulders, 2 sides, 1 center-back
    assert pkg.mannequin_ref.joint_count == 52
    assert set(pkg.grading_info.size_meshes.keys()) == {"XXS", "XS", "S"}


def test_roundtrip_load_from_zip(pipeline_run_result):
    zip_path = os.path.join(pipeline_run_result["output_dir"], "garment_template_package.zip")
    assert os.path.exists(zip_path)
    pkg = load_template(zip_path)
    assert pkg.manifest.brand == "H&M"
    assert pkg.manifest.category == "Women's Dresses"
    assert len(pkg.placements) == 3
