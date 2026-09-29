"""
Avatar and Mannequin extraction module.
Processes standard GLB avatar (such as Kloth's provided person_0.glb) to extract:
1. Mannequin 3D surface mesh (vertices, faces, bounds, height)
2. Skeletal joint hierarchy and transform matrices (Category 7)
"""

import os
import json
import struct
from typing import Tuple, List, Optional
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
        # 1. Load 3D mesh via trimesh
        scene = trimesh.load(self.glb_path)
        if isinstance(scene, trimesh.Scene):
            # Concatenate all geometries into one mesh
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
        self.bounds = self.mesh.bounds  # [[minX, minY, minZ], [maxX, maxY, maxZ]]
        self.extents = self.mesh.extents
        self.height_cm = float(self.extents[1] * 100.0)  # Y is height

        # 2. Extract Skeletal Joint Hierarchy from GLTF/GLB JSON chunk
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

        # Map parent-child relationships
        child_to_parent = {}
        for parent_idx, node in enumerate(nodes):
            for child_idx in node.get("children", []):
                child_to_parent[child_idx] = parent_idx

        # If a skin exists, extract joint indices
        joint_indices = []
        if skins and "joints" in skins[0]:
            joint_indices = skins[0]["joints"]
        else:
            # Fallback to all nodes
            joint_indices = list(range(len(nodes)))

        for idx in joint_indices:
            if idx < len(nodes):
                node = nodes[idx]
                name = node.get("name", f"joint_{idx}")
                parent = child_to_parent.get(idx, None)

                # 4x4 matrix if present, else identity
                matrix = node.get("matrix", [
                    1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0
                ])

                # If node has translation/rotation/scale instead of matrix
                if "translation" in node and "matrix" not in node:
                    t = node.get("translation", [0.0, 0.0, 0.0])
                    # Represent as 4x4 translation
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

    def get_anatomical_landmarks(self) -> dict:
        """
        Derives key anatomical heights (in meters) along Y axis for panel placement.
        """
        y_min = self.bounds[0][1]
        y_max = self.bounds[1][1]
        h = y_max - y_min

        # Standard female anthropometric proportional landmarks relative to total height
        landmarks = {
            "top_head_y": float(y_max),
            "shoulder_y": float(y_min + 0.81 * h),
            "chest_y": float(y_min + 0.73 * h),
            "waist_y": float(y_min + 0.62 * h),
            "hip_y": float(y_min + 0.52 * h),
            "knee_y": float(y_min + 0.28 * h),
            "floor_y": float(y_min)
        }
        return landmarks
