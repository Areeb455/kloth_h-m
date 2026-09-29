"""
Avatar and Mannequin extraction module.
Processes standard GLB avatar (such as Kloth's provided person_0.glb) to extract:
1. Mannequin 3D surface mesh (vertices, faces, bounds, height)
2. Skeletal joint hierarchy and transform matrices (Category 7)
3. Anthropometric torso cross-section profiles (X half-width, Z front/back bounds)
"""

import os
import json
import struct
from typing import Tuple, List, Optional, Dict
import numpy as np
import trimesh

from .models import MannequinRef, SkeletonJoint


class AvatarProcessor:
    def __init__(self, glb_path: str):
        if not os.path.exists(glb_path):
            raise FileNotFoundError(f"Avatar file not found at: {glb_path}")
        self.glb_path = glb_path
        self._load_mesh_and_skeleton()

    def _load_mesh_and_skeleton(self):
        scene = trimesh.load(self.glb_path)
        if isinstance(scene, trimesh.Scene):
            meshes = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if meshes:
                self.mesh = trimesh.util.concatenate(meshes)
            else:
                raise ValueError("No Trimesh geometry found in GLB scene.")
        elif isinstance(scene, trimesh.Trimesh):
            self.mesh = scene
        else:
            raise ValueError(f"Unexpected scene type: {type(scene)}")

        self.vertex_count = len(self.mesh.vertices)
        self.face_count = len(self.mesh.faces)
        self.bounds = self.mesh.bounds
        self.extents = self.mesh.extents
        self.height_cm = float(self.extents[1] * 100.0)

        # 2. Extract Skeletal Joint Hierarchy
        self.joints: List[SkeletonJoint] = []
        self._parse_gltf_skeleton()

    def _parse_gltf_skeleton(self):
        with open(self.glb_path, "rb") as f:
            magic, ver, length = struct.unpack("<4sII", f.read(12))
            chunk_len, chunk_type = struct.unpack("<II", f.read(8))
            json_bytes = f.read(chunk_len)
            header = json.loads(json_bytes)

        nodes = header.get("nodes", [])
        skins = header.get("skins", [])

        child_to_parent = {}
        for parent_idx, node in enumerate(nodes):
            for child_idx in node.get("children", []):
                child_to_parent[child_idx] = parent_idx

        joint_indices = []
        if skins and "joints" in skins[0]:
            joint_indices = skins[0]["joints"]
        else:
            joint_indices = list(range(len(nodes)))

        for idx in joint_indices:
            if idx < len(nodes):
                node = nodes[idx]
                name = node.get("name", f"joint_{idx}")
                parent = child_to_parent.get(idx, None)

                matrix = node.get("matrix", [
                    1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0
                ])

                if "translation" in node and "matrix" not in node:
                    t = node.get("translation", [0.0, 0.0, 0.0])
                    matrix = [
                        1.0, 0.0, 0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        float(t[0]), float(t[1]), float(t[2]), 1.0
                    ]

                self.joints.append(
                    SkeletonJoint(
                        joint_index=idx,
                        name=name,
                        parent_index=parent,
                        local_matrix=[float(v) for v in matrix]
                    )
                )

    def to_mannequin_ref(self, target_filename: str = "mannequin.glb") -> MannequinRef:
        return MannequinRef(
            mesh_filename=target_filename,
            format="glb",
            vertex_count=self.vertex_count,
            face_count=self.face_count,
            height_cm=round(self.height_cm, 2),
            joint_count=len(self.joints),
            joints=self.joints,
            reference_source="Kloth provided SMPL-X female avatar (person_0.glb)"
        )

    def get_anatomical_landmarks(self) -> Dict[str, float]:
        y_min = float(self.bounds[0][1])
        y_max = float(self.bounds[1][1])
        h = y_max - y_min

        landmarks = {
            "top_head_y": float(y_max),
            "shoulder_y": float(y_min + 0.81 * h),   # ~1.30 m
            "chest_y": float(y_min + 0.73 * h),      # ~1.17 m
            "waist_y": float(y_min + 0.62 * h),      # ~1.00 m
            "hip_y": float(y_min + 0.52 * h),        # ~0.84 m
            "knee_y": float(y_min + 0.28 * h),       # ~0.45 m
            "floor_y": float(y_min)
        }
        return landmarks

    def get_torso_profile_at_y(self, y: float, tolerance: float = 0.03) -> Dict[str, float]:
        """
        Slices avatar mesh vertices at height y, filtering out arms to get true torso dimensions.
        Returns: z_front, z_back, z_center, half_width
        """
        verts = self.mesh.vertices
        mask_y = np.abs(verts[:, 1] - y) < tolerance
        v_slice = verts[mask_y]

        # Filter out peripheral arm vertices (|x| < 0.22 for central trunk)
        v_torso = v_slice[np.abs(v_slice[:, 0]) < 0.22]

        if len(v_torso) < 5:
            # Fallback based on height
            if y > 1.2:
                return {"z_front": -0.01, "z_back": -0.18, "z_center": -0.09, "half_width": 0.21}
            elif y > 1.05:
                return {"z_front": 0.04, "z_back": -0.18, "z_center": -0.07, "half_width": 0.20}
            elif y > 0.90:
                return {"z_front": 0.08, "z_back": -0.16, "z_center": -0.04, "half_width": 0.16}
            else:
                return {"z_front": 0.08, "z_back": -0.18, "z_center": -0.05, "half_width": 0.18}

        z_front = float(v_torso[:, 2].max())
        z_back = float(v_torso[:, 2].min())
        z_center = (z_front + z_back) / 2.0
        half_width = float(np.abs(v_torso[:, 0]).max())

        return {
            "z_front": round(z_front, 4),
            "z_back": round(z_back, 4),
            "z_center": round(z_center, 4),
            "half_width": round(half_width, 4)
        }
