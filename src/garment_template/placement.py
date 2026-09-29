"""
3D Garment Placement Module.
Conformally places and wraps 2D pattern panel meshes in 3D space around the mannequin.
Implements Category 3: Saved 3D garment positions.
"""

from typing import Dict, List, Tuple
import math
import numpy as np

from .models import PanelMesh, PlacedPanel3D


class GarmentPlacer:
    def __init__(self, landmarks: Dict[str, float], body_depth_m: float = 0.22):
        """
        landmarks: Anatomical heights from avatar (shoulder_y, chest_y, waist_y, hip_y, knee_y)
        body_depth_m: Anthropometric torso depth (~0.22 m for female SMPL-X)
        """
        self.landmarks = landmarks
        self.waist_y = landmarks.get("waist_y", 1.00)
        self.shoulder_y = landmarks.get("shoulder_y", 1.30)
        self.half_depth = body_depth_m / 2.0
        self.clearance = 0.025  # 2.5 cm air clearance from body surface

    def wrap_panel_cylindrical(
        self,
        mesh: PanelMesh,
        side: str,
        category: str,
        radius_m: float = 0.18
    ) -> Tuple[List[Tuple[float, float, float]], PlacedPanel3D]:
        """
        Conformally wraps a flat 2D panel mesh around the Y-axis torso cylinder.
        """
        placed_v3d: List[Tuple[float, float, float]] = []

        is_front = (side == "front")
        z_base = (self.half_depth + self.clearance) if is_front else -(self.half_depth + self.clearance)
        z_sign = 1.0 if is_front else -1.0

        # Y anchor
        if category == "bodice":
            y_base = self.waist_y
            arrangement = "front_torso_wrap" if is_front else "back_torso_wrap"
        else:  # skirt
            y_base = self.waist_y
            arrangement = "front_skirt_drape" if is_front else "back_skirt_drape"

        xs = []
        ys = []
        zs = []

        for p2d in mesh.vertices_2d:
            # p2d is in cm: convert to meters
            x_m = p2d[0] * 0.01
            y_m = p2d[1] * 0.01

            # Cylindrical wrapping angle theta around Y axis
            theta = x_m / radius_m
            wrapped_x = radius_m * math.sin(theta)

            # Curved depth offset: sagitta = R * (1 - cos(theta))
            sagitta = radius_m * (1.0 - math.cos(theta))
            wrapped_z = z_base - (z_sign * sagitta)

            wrapped_y = y_base + y_m

            placed_v3d.append((round(wrapped_x, 4), round(wrapped_y, 4), round(wrapped_z, 4)))
            xs.append(wrapped_x)
            ys.append(wrapped_y)
            zs.append(wrapped_z)

        center_3d = (
            round(float(np.mean(xs)), 4),
            round(float(np.mean(ys)), 4),
            round(float(np.mean(zs)), 4)
        )
        bb_min = (round(float(min(xs)), 4), round(float(min(ys)), 4), round(float(min(zs)), 4))
        bb_max = (round(float(max(xs)), 4), round(float(max(ys)), 4), round(float(max(zs)), 4))

        placement_info = PlacedPanel3D(
            panel_id=mesh.panel_id,
            center_3d=center_3d,
            bounding_box_min=bb_min,
            bounding_box_max=bb_max,
            initial_arrangement=arrangement
        )

        return placed_v3d, placement_info

    def place_all_panels(
        self,
        meshes: Dict[str, PanelMesh]
    ) -> Tuple[Dict[str, PanelMesh], Dict[str, PlacedPanel3D]]:
        """
        Wraps and positions all garment panels in 3D space.
        Returns updated meshes (with 3D positions) and placement metadata.
        """
        updated_meshes: Dict[str, PanelMesh] = {}
        placements: Dict[str, PlacedPanel3D] = {}

        for pid, mesh in meshes.items():
            side = "front" if "front" in pid else "back"
            category = "bodice" if "bodice" in pid else "skirt"

            # Skirt flares out, so radius is slightly larger
            rad = 0.20 if category == "skirt" else 0.16

            v3d, p_info = self.wrap_panel_cylindrical(mesh, side=side, category=category, radius_m=rad)

            # Create updated PanelMesh with placed 3D vertices
            updated_meshes[pid] = PanelMesh(
                panel_id=mesh.panel_id,
                vertex_count=mesh.vertex_count,
                face_count=mesh.face_count,
                vertices_2d=mesh.vertices_2d,
                vertices_3d=v3d,
                faces=mesh.faces,
                uvs=mesh.uvs
            )
            placements[pid] = p_info

        return updated_meshes, placements
