"""
End-to-End Pipeline Orchestrator.
Executes the full pipeline:
Vision Analysis (front/back photos) -> Sizing & Ease ->
2D Patterns -> Meshing -> 3D Torso-Aware Placement -> Sewing ->
Fabric Assignment -> Grading -> Non-Circular Validation -> Export -> Round-Trip Read-Back.
"""

import os
import json
from typing import Dict, Any, Tuple

from .avatar import AvatarProcessor
from .vision import GarmentVisionAnalyzer
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
        front_image_path: str,
        back_image_path: str,
        output_dir: str
    ):
        self.size_chart_path = size_chart_path
        self.product_details_path = product_details_path
        self.avatar_glb_path = avatar_glb_path
        self.front_image_path = front_image_path
        self.back_image_path = back_image_path
        self.output_dir = output_dir

        with open(product_details_path, "r") as f:
            self.product_details = json.load(f)

    def run(self) -> Tuple[str, ValidationReport, LoadedTemplatePackage]:
        print("[1/10] Ingesting avatar & extracting 52-joint skeleton & torso profiles...")
        ap = AvatarProcessor(self.avatar_glb_path)
        mannequin_ref = ap.to_mannequin_ref()
        landmarks = ap.get_anatomical_landmarks()
        torso_fn = ap.get_torso_profile_at_y

        print("[2/10] Analyzing garment imagery via Computer Vision (front.jpg & back.jpg)...")
        vision = GarmentVisionAnalyzer(self.front_image_path, self.back_image_path)
        vision_meas = vision.extract_silhouette_measurements(target_garment_length_cm=88.0)
        vp = vision_meas["proportions_cm"]
        print(f"       Vision: Neck depth={vp['neck_depth']}cm, Armhole={vp['armhole_depth']}cm, Shift ratio={vision_meas['silhouette_ratios']['waist_to_chest']}")

        print("[3/10] Parsing size chart and applying ease allowances...")
        sizing = SizingEngine(self.size_chart_path)
        base_size = sizing.primary_base_size
        base_dims = sizing.get_garment_dimensions(base_size)
        body_meas = sizing.sizes_data[base_size]["body_measurements_cm"]
        print(f"       Base size '{base_size}' garment dimensions: {base_dims}")

        print("[4/10] Generating continuous 2D shift patterns guided by vision proportions (Category 1)...")
        pat_gen = PatternGenerator(base_dims, vision_proportions=vp)
        panels_2d = pat_gen.generate_all_panels()

        print("[5/10] Tessellating 2D patterns into triangle meshes (Category 2)...")
        mesher = PanelMesher(target_edge_length_cm=3.0)
        flat_meshes = mesher.triangulate_all(panels_2d)

        print("[6/10] Conformally wrapping panels in 3D around real torso profile (Category 3)...")
        placer = GarmentPlacer(landmarks, torso_profile_fn=torso_fn)
        placed_meshes, placements = placer.place_all_panels(flat_meshes)

        print("[7/10] Pairing seams and equalizing vertex counts (Category 4)...")
        sewing_eng = SewingEngine(panels_2d, placed_meshes)
        sewing_conns = sewing_eng.generate_sewing_connections()

        print("[8/10] Assigning fabric parameters, grainlines and visibility (Categories 5, 6, 9)...")
        fab_mgr = FabricManager(self.product_details.get("fabric_properties"))
        panel_ids = list(panels_2d.keys())
        fab_assignments = fab_mgr.get_fabric_assignments(panel_ids)
        fab_directions = fab_mgr.get_fabric_directions(panel_ids)
        vis_settings = fab_mgr.get_visibility_settings(panel_ids)

        print("[9/10] Grading all sizes and exporting alternate 3D OBJ meshes (Category 8)...")
        grader = GradingEngine(sizing, landmarks, torso_profile_fn=torso_fn, vision_proportions=vp)
        grading_info, _ = grader.generate_size_meshes(self.output_dir)

        print("[10/10] Running non-circular validation checks...")
        validator = GarmentValidator(
            body_measurements=body_meas,
            garment_dimensions=base_dims,
            vision_measurements=vision_meas,
            panels_2d=panels_2d,
            meshes=placed_meshes,
            sewing_conns=sewing_conns,
            torso_profile_fn=torso_fn
        )
        val_report = validator.run_all_checks()
        print(f"        Validation result: {val_report.passed} ({val_report.to_dict()['summary']})")

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
        print("        Read-back summary:", loaded_pkg.summary())

        return pkg_dir, val_report, loaded_pkg
