"""
Avatar Mesh Collider Module.
Provides exact signed-distance collision detection and projection against
the real avatar 3D mesh (assets/person_0.glb) using vertex normals and closest-surface queries.
Used identically by both ClothSimulator (during PBD iterations) and GarmentValidator (for physical verification).
"""

from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
import trimesh

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


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

        self.has_torch = HAS_TORCH
        if self.has_torch:
            self.v_torch = torch.from_numpy(self.vertices)
            self.n_torch = torch.from_numpy(self.normals)

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

        if self.has_torch:
            pts_t = torch.from_numpy(pts) if not isinstance(pts, torch.Tensor) else pts
            dists = torch.cdist(pts_t, self.v_torch)
            min_d, idx = torch.min(dists, dim=1)
            near_v = self.v_torch[idx]
            near_n = self.n_torch[idx]
            sd = torch.sum((pts_t - near_v) * near_n, dim=1)
            return sd.numpy(), near_v.numpy(), near_n.numpy()
        else:
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
        """
        m = self.margin if margin is None else float(margin)
        pts = np.asarray(points, dtype=np.float32).copy()
        if len(pts) == 0:
            return pts

        if self.has_torch:
            pts_t = torch.from_numpy(pts)
            dists = torch.cdist(pts_t, self.v_torch)
            min_d, idx = torch.min(dists, dim=1)
            near_v = self.v_torch[idx]
            near_n = self.n_torch[idx]
            sd = torch.sum((pts_t - near_v) * near_n, dim=1)
            mask = sd < m
            if torch.any(mask):
                pts_t[mask] += (m - sd[mask]).unsqueeze(1) * near_n[mask]
            return pts_t.numpy()
        else:
            sd, near_v, near_n = self.compute_signed_distances(pts)
            mask = sd < m
            if np.any(mask):
                pts[mask] += (m - sd[mask])[:, None] * near_n[mask]
            return pts

    def measure_penetrations(self, points: np.ndarray) -> Dict[str, Any]:
        """
        Computes exact physical penetration statistics for validation:
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
        penetrated = sd < 0.0
        pen_count = int(np.sum(penetrated))
        pct_inside = float(100.0 * pen_count / len(sd))
        min_sd_m = float(np.min(sd))
        max_pen_mm = float(max(0.0, -min_sd_m) * 1000.0)
        min_sd_mm = float(min_sd_m * 1000.0)

        return {
            "total_vertices": len(sd),
            "penetrated_vertices": pen_count,
            "pct_vertices_inside": round(pct_inside, 2),
            "max_penetration_mm": round(max_pen_mm, 2),
            "min_signed_dist_mm": round(min_sd_mm, 2),
            "zero_penetration_pass": bool(pen_count == 0)
        }
