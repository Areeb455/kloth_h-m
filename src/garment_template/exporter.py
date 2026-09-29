"""
Standardized Template Exporter Module.
Bundles all 9 categories into the official template package structure:
1. patterns_2d.json
2. meshes_panels.json
3. placement_3d.json (starting arrangement) & simulated_3d.json (draped simulation)
4. sewing_connections.json
5. fabric_properties.json
6. fabric_direction.json
7. mannequin.glb & mannequin_skeleton.json
8. grading_sizes.json & garment_{size}.obj
9. visibility_settings.json
Plus manifest.json and validation_report.json, compressed into garment_template_package.zip.
"""

import os
import json
import shutil
import zipfile
from datetime import datetime
from typing import Dict, List, Any, Optional

from .models import (
    Panel2DGeometry, PanelMesh, PlacedPanel3D, SewingConnection,
    FabricAssignment, FabricDirection, MannequinRef, GradingInfo,
    PanelMaterialSettings, TemplateManifest
)


class TemplateExporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def export_package(
        self,
        garment_name: str,
        brand: str,
        category: str,
        base_size: str,
        supported_sizes: List[str],
        panels_2d: Dict[str, Panel2DGeometry],
        meshes: Dict[str, PanelMesh],
        placements: Dict[str, PlacedPanel3D],
        sewing_conns: List[SewingConnection],
        fabric_assignments: Dict[str, FabricAssignment],
        fabric_directions: Dict[str, FabricDirection],
        mannequin_ref: MannequinRef,
        source_avatar_glb: str,
        grading_info: GradingInfo,
        visibility_settings: Dict[str, PanelMaterialSettings],
        simulated_meshes: Optional[Dict[str, PanelMesh]] = None,
        simulation_metrics: Optional[Dict[str, Any]] = None,
        validation_report: Optional[Dict[str, Any]] = None,
        create_zip: bool = True
    ) -> str:
        pkg_dir = os.path.join(self.output_dir, "template_package")
        os.makedirs(pkg_dir, exist_ok=True)

        # 1. Manifest
        manifest = TemplateManifest(
            garment_name=garment_name,
            brand=brand,
            category=category,
            base_size=base_size,
            supported_sizes=supported_sizes,
            created_at=datetime.utcnow().isoformat() + "Z",
            mannequin_mesh_file="mannequin.glb",
            base_garment_obj_file=f"garment_{base_size}.obj"
        )
        with open(os.path.join(pkg_dir, "manifest.json"), "w") as f:
            f.write(manifest.model_dump_json(indent=2))

        # Category 1: 2D patterns
        with open(os.path.join(pkg_dir, manifest.category_1_patterns_file), "w") as f:
            data = {k: v.model_dump() for k, v in panels_2d.items()}
            json.dump(data, f, indent=2)

        # Category 2: Triangle meshes
        with open(os.path.join(pkg_dir, manifest.category_2_meshes_file), "w") as f:
            data = {k: v.model_dump() for k, v in meshes.items()}
            json.dump(data, f, indent=2)

        # Category 3: Placed 3D positions (starting arrangement)
        with open(os.path.join(pkg_dir, manifest.category_3_placement_file), "w") as f:
            data = {k: v.model_dump() for k, v in placements.items()}
            json.dump(data, f, indent=2)

        # Category 3 (Simulated): Draped positions & metrics
        if simulated_meshes:
            with open(os.path.join(pkg_dir, "simulated_3d.json"), "w") as f:
                sim_data = {
                    "metrics": simulation_metrics or {},
                    "panels": {k: v.model_dump() for k, v in simulated_meshes.items()}
                }
                json.dump(sim_data, f, indent=2)

        # Category 4: Sewing connections
        with open(os.path.join(pkg_dir, manifest.category_4_sewing_file), "w") as f:
            data = [c.model_dump() for c in sewing_conns]
            json.dump(data, f, indent=2)

        # Category 5: Fabric assignment
        with open(os.path.join(pkg_dir, manifest.category_5_fabric_file), "w") as f:
            data = {k: v.model_dump() for k, v in fabric_assignments.items()}
            json.dump(data, f, indent=2)

        # Category 6: Fabric direction
        with open(os.path.join(pkg_dir, manifest.category_6_direction_file), "w") as f:
            data = {k: v.model_dump() for k, v in fabric_directions.items()}
            json.dump(data, f, indent=2)

        # Category 7: Mannequin & skeleton metadata
        with open(os.path.join(pkg_dir, manifest.category_7_mannequin_file), "w") as f:
            json.dump(mannequin_ref.model_dump(), f, indent=2)

        # Copy mannequin 3D asset (GLB)
        dst_glb = os.path.join(pkg_dir, "mannequin.glb")
        if os.path.exists(source_avatar_glb) and source_avatar_glb != dst_glb:
            shutil.copy2(source_avatar_glb, dst_glb)

        # Category 8: Grading sizes metadata
        with open(os.path.join(pkg_dir, manifest.category_8_grading_file), "w") as f:
            json.dump(grading_info.model_dump(), f, indent=2)

        # Category 9: Visibility & transparency
        with open(os.path.join(pkg_dir, manifest.category_9_visibility_file), "w") as f:
            data = {k: v.model_dump() for k, v in visibility_settings.items()}
            json.dump(data, f, indent=2)

        # Validation Report
        if validation_report:
            with open(os.path.join(pkg_dir, "validation_report.json"), "w") as f:
                json.dump(validation_report, f, indent=2)
            # Also save directly in output_dir for easy viewer access
            with open(os.path.join(self.output_dir, "validation_report.json"), "w") as f:
                json.dump(validation_report, f, indent=2)

        # Copy generated OBJ size meshes into package
        for size_label in supported_sizes:
            src_obj = os.path.join(self.output_dir, f"garment_{size_label}.obj")
            dst_obj = os.path.join(pkg_dir, f"garment_{size_label}.obj")
            if os.path.exists(src_obj) and src_obj != dst_obj:
                shutil.copy2(src_obj, dst_obj)

            src_init_obj = os.path.join(self.output_dir, f"garment_{size_label}_initial.obj")
            dst_init_obj = os.path.join(pkg_dir, f"garment_{size_label}_initial.obj")
            if os.path.exists(src_init_obj) and src_init_obj != dst_init_obj:
                shutil.copy2(src_init_obj, dst_init_obj)

        # Create zip if requested
        zip_path = os.path.join(self.output_dir, "garment_template_package.zip")
        if create_zip:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(pkg_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, pkg_dir)
                        zipf.write(file_path, rel_path)

        return pkg_dir
