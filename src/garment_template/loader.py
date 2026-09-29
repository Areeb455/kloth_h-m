"""
Package Loader and Reader Module.
Reads and strictly validates the exported 3D garment template package.
Implements the round-trip read-back verification required by the assignment.
"""

import os
import json
import zipfile
import tempfile
from typing import Dict, List, Optional

from .models import (
    TemplateManifest,
    Panel2DGeometry,
    PanelMesh,
    PlacedPanel3D,
    SewingConnection,
    FabricAssignment,
    FabricDirection,
    MannequinRef,
    GradingInfo,
    PanelMaterialSettings
)


class LoadedTemplatePackage:
    def __init__(
        self,
        package_path: str,
        manifest: TemplateManifest,
        patterns_2d: Dict[str, Panel2DGeometry],
        meshes: Dict[str, PanelMesh],
        placements: Dict[str, PlacedPanel3D],
        sewing_connections: List[SewingConnection],
        fabric_assignments: Dict[str, FabricAssignment],
        fabric_directions: Dict[str, FabricDirection],
        mannequin_ref: MannequinRef,
        grading_info: GradingInfo,
        visibility_settings: Dict[str, PanelMaterialSettings]
    ):
        self.package_path = package_path
        self.manifest = manifest
        self.patterns_2d = patterns_2d
        self.meshes = meshes
        self.placements = placements
        self.sewing_connections = sewing_connections
        self.fabric_assignments = fabric_assignments
        self.fabric_directions = fabric_directions
        self.mannequin_ref = mannequin_ref
        self.grading_info = grading_info
        self.visibility_settings = visibility_settings

    def summary(self) -> dict:
        return {
            "garment_name": self.manifest.garment_name,
            "base_size": self.manifest.base_size,
            "supported_sizes": self.manifest.supported_sizes,
            "panel_count": len(self.patterns_2d),
            "seam_count": len(self.sewing_connections),
            "mannequin_joints": self.mannequin_ref.joint_count,
            "mannequin_height_cm": self.mannequin_ref.height_cm,
            "mesh_sizes_available": list(self.grading_info.size_meshes.keys())
        }


def load_template(package_dir_or_zip: str) -> LoadedTemplatePackage:
    """
    Loads and validates a complete 3D garment template package from a directory or .zip archive.
    """
    if not os.path.exists(package_dir_or_zip):
        raise FileNotFoundError(f"Package not found: {package_dir_or_zip}")

    extract_dir = None
    if zipfile.is_zipfile(package_dir_or_zip):
        extract_dir = tempfile.mkdtemp(prefix="kloth_pkg_")
        with zipfile.ZipFile(package_dir_or_zip, "r") as zf:
            zf.extractall(extract_dir)
        target_dir = extract_dir
    elif os.path.isdir(package_dir_or_zip):
        target_dir = package_dir_or_zip
    else:
        raise ValueError(f"Path must be a directory or .zip file: {package_dir_or_zip}")

    try:
        manifest_path = os.path.join(target_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError("Missing manifest.json in template package")

        with open(manifest_path, "r") as f:
            manifest = TemplateManifest(**json.load(f))

        # Category 1: 2D patterns
        with open(os.path.join(target_dir, manifest.category_1_patterns_file), "r") as f:
            p2d_raw = json.load(f)
            patterns_2d = {k: Panel2DGeometry(**v) for k, v in p2d_raw.items()}

        # Category 2: Triangle meshes
        with open(os.path.join(target_dir, manifest.category_2_meshes_file), "r") as f:
            m_raw = json.load(f)
            meshes = {k: PanelMesh(**v) for k, v in m_raw.items()}

        # Category 3: Placed 3D positions
        with open(os.path.join(target_dir, manifest.category_3_placement_file), "r") as f:
            pl_raw = json.load(f)
            placements = {k: PlacedPanel3D(**v) for k, v in pl_raw.items()}

        # Category 4: Sewing connections
        with open(os.path.join(target_dir, manifest.category_4_sewing_file), "r") as f:
            sew_raw = json.load(f)
            sewing_conns = [SewingConnection(**c) for c in sew_raw]

        # Category 5: Fabric assignment
        with open(os.path.join(target_dir, manifest.category_5_fabric_file), "r") as f:
            fab_raw = json.load(f)
            fabric_assignments = {k: FabricAssignment(**v) for k, v in fab_raw.items()}

        # Category 6: Fabric direction
        with open(os.path.join(target_dir, manifest.category_6_direction_file), "r") as f:
            dir_raw = json.load(f)
            fabric_directions = {k: FabricDirection(**v) for k, v in dir_raw.items()}

        # Category 7: Mannequin & skeleton
        with open(os.path.join(target_dir, manifest.category_7_mannequin_file), "r") as f:
            mannequin_ref = MannequinRef(**json.load(f))

        # Category 8: Grading sizes
        with open(os.path.join(target_dir, manifest.category_8_grading_file), "r") as f:
            grading_info = GradingInfo(**json.load(f))

        # Category 9: Visibility & transparency
        with open(os.path.join(target_dir, manifest.category_9_visibility_file), "r") as f:
            vis_raw = json.load(f)
            visibility_settings = {k: PanelMaterialSettings(**v) for k, v in vis_raw.items()}

        return LoadedTemplatePackage(
            package_path=package_dir_or_zip,
            manifest=manifest,
            patterns_2d=patterns_2d,
            meshes=meshes,
            placements=placements,
            sewing_connections=sewing_conns,
            fabric_assignments=fabric_assignments,
            fabric_directions=fabric_directions,
            mannequin_ref=mannequin_ref,
            grading_info=grading_info,
            visibility_settings=visibility_settings
        )

    finally:
        # Note: We keep extract_dir if needed or cleanup
        pass
