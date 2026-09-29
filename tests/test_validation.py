"""
Validation Suite Tests: Tests individual checks on geometry, mesh, non-penetration, and seams.
"""

import os
import pytest
from src.garment_template.sizing import SizingEngine
from src.garment_template.patterns import PatternGenerator
from src.garment_template.meshing import PanelMesher
from src.garment_template.placement import GarmentPlacer
from src.garment_template.sewing import SewingEngine
from src.garment_template.validator import GarmentValidator


@pytest.fixture(scope="module")
def base_garment_data():
    test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chart_path = os.path.join(test_root, "samples", "size_chart.json")
    sizing = SizingEngine(chart_path)
    dims = sizing.get_garment_dimensions("XS")
    body_meas = sizing.sizes_data["XS"]["body_measurements_cm"]
    panels = PatternGenerator(dims).generate_all_panels()
    flat_meshes = PanelMesher(target_edge_length_cm=3.0).triangulate_all(panels)
    landmarks = {"waist_y": 1.0, "shoulder_y": 1.3}
    placed_meshes, placements = GarmentPlacer(landmarks).place_all_panels(flat_meshes)
    sewing_conns = SewingEngine(panels, placed_meshes).generate_sewing_connections()
    return {
        "dims": dims,
        "body_meas": body_meas,
        "panels": panels,
        "placed_meshes": placed_meshes,
        "sewing_conns": sewing_conns
    }


def test_2d_panel_polygons_valid(base_garment_data):
    for pid, geo in base_garment_data["panels"].items():
        assert geo.area_sq_cm > 500.0
        assert geo.width_cm > 0.0
        assert geo.height_cm > 0.0
        assert len(geo.contour_points) >= 6


def test_mesh_has_no_degenerate_triangles(base_garment_data):
    validator = GarmentValidator(
        body_measurements=base_garment_data["body_meas"],
        garment_dimensions=base_garment_data["dims"],
        vision_measurements={},
        panels_2d=base_garment_data["panels"],
        meshes=base_garment_data["placed_meshes"],
        sewing_conns=base_garment_data["sewing_conns"]
    )
    report = validator.run_all_checks()
    degen_checks = [c for c in report.checks if "Non-Degenerate" in c["name"]]
    assert len(degen_checks) == 3
    for c in degen_checks:
        assert c["status"] == "PASS"


def test_sewing_connections_all_have_equal_vertices(base_garment_data):
    for conn in base_garment_data["sewing_conns"]:
        assert len(conn.edge_a_vertex_indices) == len(conn.edge_b_vertex_indices)
        assert len(conn.edge_a_vertex_indices) > 0


def test_no_duplicate_seams(base_garment_data):
    seam_ids = [c.seam_id for c in base_garment_data["sewing_conns"]]
    assert len(seam_ids) == len(set(seam_ids))
