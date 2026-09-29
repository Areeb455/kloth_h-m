"""
End-to-End Pipeline Orchestrator.
Executes the full pipeline:
Inputs -> Sizing -> 2D Patterns -> Meshing -> 3D Placement -> Sewing ->
Fabric Assignment -> Grading -> Validation -> Export -> Round-Trip Read-Back.
"""

import os
import json
from typing import Dict, Any, Tuple

from .avatar import AvatarProcessor
from .sizing import SizingEngine
from .patterns import PatternGenerator
from .meshing import PanelMesher
from .placement import GarmentPlacer
from .sewing import SewingEngine
from .fabric import FabricManager
from .grading import GradingEngine
from .validator import GarmentValidator, ValidationReport
from .exporter import TemplateExporter
from .loader import load_template, LoadedTemplatePackage


class PipelineOrchestrator:
    def __init__(
        self,
        size_chart_path: str,
        product_details_path: str,
        avatar_glb_path: str,
        output_dir: str
    ):
        self.size_chart_path = size_chart_path
        self.product_details_path = product_details_path
        self.avatar_glb_path = avatar_glb_path
        self.output_dir = output_dir

        with open(product_details_path, "r") as f:
            self.product_details = json.load(f)

    def run(self) -> Tuple[str, ValidationReport, LoadedTemplatePackage]:
        print("[1/9] Ingesting avatar & extracting 52-joint skeleton...")
        ap = AvatarProcessor(self.avatar_glb_path)
        mannequin_ref = ap.to_mannequin_ref()
        landmarks = ap.get_anatomical_landmarks()

        print("[2/9] Parsing size chart and applying ease allowances...")
        sizing = SizingEngine(self.size_chart_path)
        base_size = sizing.primary_base_size
        base_dims = sizing.get_garment_dimensions(base_size)
        print(f"      Base size '{base_size}' garment dimensions: {base_dims}")

        print("[3/9] Generating parametric 2D patterns (Category 1)...")
        pat_gen = PatternGenerator(base_dims)
        panels_2d = pat_gen.generate_all_panels()

        print("[4/9] Tessellating 2D patterns into triangle meshes (Category 2)...")
        mesher = PanelMesher(target_edge_length_cm=3.0)
        flat_meshes = mesher.triangulate_all(panels_2d)

        print("[5/9] Conformally wrapping panels in 3D around mannequin (Category 3)...")
        placer = GarmentPlacer(landmarks)
        placed_meshes, placements = placer.place_all_panels(flat_meshes)

        print("[6/9] Pairing seams and equalizing vertex counts (Category 4)...")
        sewing_eng = SewingEngine(panels_2d, placed_meshes)
        sewing_conns = sewing_eng.generate_sewing_connections()

        print("[7/9] Assigning fabric parameters, grainlines and visibility (Categories 5, 6, 9)...")
        fab_mgr = FabricManager(self.product_details.get("fabric_properties"))
        panel_ids = list(panels_2d.keys())
        fab_assignments = fab_mgr.get_fabric_assignments(panel_ids)
        fab_directions = fab_mgr.get_fabric_directions(panel_ids)
        vis_settings = fab_mgr.get_visibility_settings(panel_ids)

        print("[8/9] Grading all sizes and exporting alternate 3D OBJ meshes (Category 8)...")
        grader = GradingEngine(sizing, landmarks)
        grading_info, _ = grader.generate_size_meshes(self.output_dir)

        print("[9/9] Running validation checks...")
        validator = GarmentValidator(base_dims, panels_2d, placed_meshes, sewing_conns)
        val_report = validator.run_all_checks()
        print(f"      Validation result: {val_report.passed} ({val_report.to_dict()['summary']})")

        print("Exporting self-contained template package...")
        exporter = TemplateExporter(self.output_dir)
        pkg_dir = exporter.export_package(
            garment_name=self.product_details.get("product_name", "Sleeveless Jersey Shift Dress"),
            brand=self.product_details.get("brand", "H&M"),
            category=self.product_details.get("category", "Women's Dresses"),
            base_size=base_size,
            supported_sizes=sizing.supported_sizes,
            panels_2d=panels_2d,
            meshes=placed_meshes,
            placements=placements,
            sewing_conns=sewing_conns,
            fabric_assignments=fab_assignments,
            fabric_directions=fab_directions,
            mannequin_ref=mannequin_ref,
            source_avatar_glb=self.avatar_glb_path,
            grading_info=grading_info,
            visibility_settings=vis_settings,
            create_zip=True
        )

        print("Executing round-trip read-back verification...")
        loaded_pkg = load_template(pkg_dir)
        print("      Read-back summary:", loaded_pkg.summary())

        return pkg_dir, val_report, loaded_pkg
