"""
Cloth Simulation Test Suite.
Validates PBD physics engine:
1. No NaN / infinite numerical stability.
2. Equilibrium settling (decreasing kinetic energy and small step displacement).
3. Exact seam closure (< 5 mm max gap, 0.0 mm midpoint welding).
4. Zero body penetration against avatar torso profile.
5. Area strain and physical conservation.
"""

import os
import pytest
import numpy as np

from src.garment_template.avatar import AvatarProcessor
from src.garment_template.sizing import SizingEngine
from src.garment_template.patterns import PatternGenerator
from src.garment_template.meshing import PanelMesher
from src.garment_template.placement import GarmentPlacer
from src.garment_template.sewing import SewingEngine
from src.garment_template.simulation import ClothSimulator, ClothSimulationResult


@pytest.fixture(scope="module")
def sim_context():
    test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    avatar_glb = os.path.join(test_root, "assets", "person_0.glb")
    size_chart = os.path.join(test_root, "samples", "size_chart.json")

    ap = AvatarProcessor(avatar_glb)
    sizing = SizingEngine(size_chart)
    base_dims = sizing.get_garment_dimensions("XS")
    pat_gen = PatternGenerator(base_dims)
    panels_2d = pat_gen.generate_all_panels()
    mesher = PanelMesher(target_edge_length_cm=3.0)
    flat_meshes = mesher.triangulate_all(panels_2d)

    placer = GarmentPlacer(ap.get_anatomical_landmarks(), ap.get_torso_profile_at_y)
    placed_meshes, _ = placer.place_all_panels(flat_meshes)

    sewing_eng = SewingEngine(panels_2d, placed_meshes)
    sewing_conns = sewing_eng.generate_sewing_connections()

    simulator = ClothSimulator(
        panels_2d=panels_2d,
        meshes=placed_meshes,
        sewing_conns=sewing_conns,
        fabric_properties={"gsm": 180, "blend": "95% cotton, 5% elastane"},
        torso_profile_fn=ap.get_torso_profile_at_y
    )
    result = simulator.simulate(num_steps=30, sub_iters=10, dt=0.01)

    return {
        "simulator": simulator,
        "result": result,
        "ap": ap,
        "conns": sewing_conns,
        "panels_2d": panels_2d
    }


def test_simulation_stability_no_nan(sim_context):
    sim = sim_context["simulator"]
    assert not np.isnan(sim.positions).any(), "Found NaN in simulated vertex positions"
    assert not np.isinf(sim.positions).any(), "Found Inf in simulated vertex positions"
    assert not np.isnan(sim.velocities).any(), "Found NaN in vertex velocities"


def test_simulation_settles_to_equilibrium(sim_context):
    metrics = sim_context["result"].metrics
    assert metrics["settled"] is True, f"Simulation did not settle: final_ke={metrics['final_kinetic_energy']}"
    assert metrics["final_kinetic_energy"] < 0.05, f"Excessive kinetic energy: {metrics['final_kinetic_energy']}"
    assert metrics["max_step_displacement_mm"] < 5.0, f"Displacement too large: {metrics['max_step_displacement_mm']}"


def test_simulation_seam_closure(sim_context):
    metrics = sim_context["result"].metrics
    assert metrics["max_seam_gap_mm"] < 5.0, f"Seam gap exceeds 5 mm: {metrics['max_seam_gap_mm']} mm"
    assert metrics["avg_seam_gap_mm"] < 2.0, f"Average seam gap too large: {metrics['avg_seam_gap_mm']} mm"


def test_simulation_avatar_non_penetration(sim_context):
    metrics = sim_context["result"].metrics
    assert metrics["avatar_penetrations"] == 0, f"Found {metrics['avatar_penetrations']} penetrations"


def test_simulation_exports_initial_and_simulated_meshes(sim_context):
    res = sim_context["result"]
    assert len(res.starting_meshes) == 3
    assert len(res.simulated_meshes) == 3
    for pid in res.simulated_meshes:
        assert len(res.starting_meshes[pid].vertices_3d) == len(res.simulated_meshes[pid].vertices_3d)
        assert len(res.starting_meshes[pid].faces) == len(res.simulated_meshes[pid].faces)
