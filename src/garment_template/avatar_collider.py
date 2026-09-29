"""
Avatar Mesh Collider Module.
Provides nearest-surface vertex-normal signed-distance collision detection and projection
approximation against the real avatar 3D mesh (assets/person_0.glb).
Accelerated via scipy.spatial.cKDTree with pure NumPy fallback.
Used identically by both ClothSimulator (during PBD iterations) and GarmentValidator (for physical verification).
"""

import os
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
import trimesh

try:
    from scipy.spatial import cKDTree
    HAS_CKDTREE = True
except ImportError:
    HAS_CKDTREE = False


class AvatarMeshCollider:
    def __init__(self, glb_path_or_mesh: Union[str, trimesh.Trimesh], margin: float = 0.006):
        """
        Initializes the avatar mesh collider.
        :param glb_path_or_mesh: File path to person_0.glb or loaded trimesh object.
        :param margin: Clearance margin in meters (default 0.006 m = 6.0 mm).
        """
        if isinstance(glb_path_or_mesh, str):
            mesh = trimesh.load(glb_path_or_mesh, force="mesh")
        else:
            mesh = glb_path_or_mesh

        self.vertices = np.asarray(mesh.vertices, dtype=np.float32)
        self.faces = np.asarray(mesh.faces, dtype=np.int64)
        self.margin = float(margin)

        # Compute outward vertex normals analytically from faces
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]
        face_normals = np.cross(v1 - v0, v2 - v0)
        fn_norm = np.linalg.norm(face_normals, axis=1, keepdims=True) + 1e-12
        face_normals = face_normals / fn_norm

        self.normals = np.zeros_like(self.vertices)
        np.add.at(self.normals, self.faces[:, 0], face_normals)
        np.add.at(self.normals, self.faces[:, 1], face_normals)
        np.add.at(self.normals, self.faces[:, 2], face_normals)
        vn_norm = np.linalg.norm(self.normals, axis=1, keepdims=True) + 1e-12
        self.normals = self.normals / vn_norm

        # Accelerate queries with scipy.spatial.cKDTree
        if HAS_CKDTREE:
            self.kdtree = cKDTree(self.vertices)
        else:
            self.kdtree = None

    def compute_signed_distances(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        For a set of 3D query points (N, 3), finds the nearest avatar vertex,
        its outward normal, and the signed distance:
            sd = (point - nearest_v) · nearest_n
        Positive => point is outside the avatar surface.
        Negative => point has penetrated behind the avatar surface.
        """
        pts = np.asarray(points, dtype=np.float32)
        if len(pts) == 0:
            return np.empty(0, dtype=np.float32), np.empty((0, 3), dtype=np.float32), np.empty((0, 3), dtype=np.float32)

        if self.kdtree is not None:
            dists, idx = self.kdtree.query(pts, k=1)
            near_v = self.vertices[idx]
            near_n = self.normals[idx]
            sd = np.sum((pts - near_v) * near_n, axis=1)
            return sd, near_v, near_n
        else:
            # Chunked vectorized fallback
            chunk_size = 500
            sds, nvs, nns = [], [], []
            for i in range(0, len(pts), chunk_size):
                p_chunk = pts[i:i + chunk_size]
                diffs = p_chunk[:, None, :] - self.vertices[None, :, :]
                dists_sq = np.sum(diffs ** 2, axis=2)
                idx = np.argmin(dists_sq, axis=1)
                nv = self.vertices[idx]
                nn = self.normals[idx]
                sd = np.sum((p_chunk - nv) * nn, axis=1)
                sds.append(sd)
                nvs.append(nv)
                nns.append(nn)
            return np.concatenate(sds), np.vstack(nvs), np.vstack(nns)

    def project_out(self, points: np.ndarray, margin: Optional[float] = None) -> np.ndarray:
        """
        Projects any point with signed_distance < margin outward along the surface normal
        so that its signed distance reaches at least `margin`:
            p_new = p + (margin - sd) * n
        Two iterative passes ensure full clearance even on curved mesh facets.
        """
        m = self.margin if margin is None else float(margin)
        pts = np.asarray(points, dtype=np.float32).copy()
        if len(pts) == 0:
            return pts

        for _ in range(2):
            sd, near_v, near_n = self.compute_signed_distances(pts)
            mask = sd < m
            if not np.any(mask):
                break
            pts[mask] += (m - sd[mask])[:, None] * near_n[mask]
        return pts

    def measure_penetrations(self, points: np.ndarray) -> Dict[str, Any]:
        """
        Computes physical penetration statistics for validation:
        - total_vertices: number of tested vertices
        - penetrated_vertices: count of vertices behind the body surface (sd < 0)
        - pct_vertices_inside: percentage behind body surface (Target: 0.0%)
        - max_penetration_mm: deepest inward penetration in mm (Target: 0.0 mm)
        - min_signed_dist_mm: signed distance to surface of worst vertex in mm (Target >= 0.0 mm)
        - zero_penetration_pass: True if exactly 0 vertices inside
        """
        pts = np.asarray(points, dtype=np.float32)
        if len(pts) == 0:
            return {
                "total_vertices": 0,
                "penetrated_vertices": 0,
                "pct_vertices_inside": 0.0,
                "max_penetration_mm": 0.0,
                "min_signed_dist_mm": 0.0,
                "zero_penetration_pass": True
            }

        sd, _, _ = self.compute_signed_distances(pts)
        sd_mm = sd * 1000.0  # convert to mm

        penetrated_mask = sd_mm < 0.0
        pen_count = int(np.sum(penetrated_mask))
        total_count = len(pts)
        pct_inside = round(float(pen_count / total_count * 100.0), 2)

        if pen_count > 0:
            max_pen_mm = round(float(-np.min(sd_mm[penetrated_mask])), 2)
        else:
            max_pen_mm = 0.0

        min_sd_mm = round(float(np.min(sd_mm)), 2)
        passed = bool(pen_count == 0)

        return {
            "total_vertices": total_count,
            "penetrated_vertices": pen_count,
            "pct_vertices_inside": pct_inside,
            "max_penetration_mm": max_pen_mm,
            "min_signed_dist_mm": min_sd_mm,
            "zero_penetration_pass": passed
        }
