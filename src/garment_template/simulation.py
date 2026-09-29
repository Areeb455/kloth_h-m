"""
Position-Based Dynamics (PBD) Cloth Simulation Module.
Assembles and sews 2D/3D garment panels in 3D space:
1. Structural distance constraints derived from 2D rest lengths.
2. Bending constraints across adjacent triangle pairs.
3. Seam constraints on 1:1 paired vertices to pull seams closed.
4. Vertex mass computed from fabric weight (180 GSM cotton jersey).
5. Gravity, velocity damping, and vectorized avatar torso collision avoidance.
6. Produces settled, draped 3D garment mesh with < 5 mm seam gaps.
"""

import copy
from typing import Dict, List, Tuple, Any, Callable, Optional
import numpy as np

from .models import PanelMesh, SewingConnection, Panel2DGeometry


class ClothSimulationResult:
    def __init__(
        self,
        starting_meshes: Dict[str, PanelMesh],
        simulated_meshes: Dict[str, PanelMesh],
        metrics: Dict[str, Any]
    ):
        self.starting_meshes = starting_meshes
        self.simulated_meshes = simulated_meshes
        self.metrics = metrics


class ClothSimulator:
    def __init__(
        self,
        panels_2d: Dict[str, Panel2DGeometry],
        meshes: Dict[str, PanelMesh],
        sewing_conns: List[SewingConnection],
        fabric_properties: Dict[str, Any],
        torso_profile_fn: Optional[Callable[[float], Dict[str, float]]] = None
    ):
        self.panels_2d = panels_2d
        self.initial_meshes = meshes
        self.sewing_conns = sewing_conns
        self.fabric_props = fabric_properties
        self.torso_profile_fn = torso_profile_fn

        panel_props = self.fabric_props.get("panel_properties", {})
        sample_prop = next(iter(panel_props.values()), {}) if panel_props else {}
        self.gsm = sample_prop.get("weight_gsm", 180.0)
        self.mass_per_sq_m = self.gsm * 0.001

        # Precompute vectorized torso profile grid for ultra-fast collision queries
        if self.torso_profile_fn is not None:
            self.y_grid = np.linspace(0.60, 1.50, 91)
            self.grid_zf = np.array([self.torso_profile_fn(y)["z_front"] for y in self.y_grid])
            self.grid_zb = np.array([self.torso_profile_fn(y)["z_back"] for y in self.y_grid])
            self.grid_rx = np.array([self.torso_profile_fn(y).get("r_x", 0.17) for y in self.y_grid])
        else:
            self.y_grid = None

        self._build_global_mesh()

    def _build_global_mesh(self):
        """Assembles all panel meshes into a unified global vertex and constraint system."""
        self.panel_ids = list(self.initial_meshes.keys())
        self.panel_vertex_ranges = {}
        all_verts_3d = []
        all_verts_2d = []

        curr_offset = 0
        for pid in self.panel_ids:
            m = self.initial_meshes[pid]
            v3 = np.array(m.vertices_3d, dtype=np.float64)
            v2 = np.array(m.vertices_2d, dtype=np.float64)
            cnt = len(v3)
            self.panel_vertex_ranges[pid] = (curr_offset, curr_offset + cnt)
            all_verts_3d.append(v3)
            all_verts_2d.append(v2)
            curr_offset += cnt

        self.num_vertices = curr_offset
        self.positions_initial = np.vstack(all_verts_3d)
        self.positions = self.positions_initial.copy()
        self.positions_prev = self.positions.copy()
        self.velocities = np.zeros_like(self.positions)
        self.vertices_2d = np.vstack(all_verts_2d)

        # 1. Structural Distance Constraints
        edges_set = set()
        faces_by_edge = {}

        for pid in self.panel_ids:
            m = self.initial_meshes[pid]
            offset = self.panel_vertex_ranges[pid][0]
            for f in m.faces:
                f_glob = [f[0] + offset, f[1] + offset, f[2] + offset]
                tri_edges = [
                    (min(f_glob[0], f_glob[1]), max(f_glob[0], f_glob[1])),
                    (min(f_glob[1], f_glob[2]), max(f_glob[1], f_glob[2])),
                    (min(f_glob[2], f_glob[0]), max(f_glob[2], f_glob[0]))
                ]
                for e in tri_edges:
                    edges_set.add(e)
                    faces_by_edge.setdefault(e, []).append(f_glob)

        self.edge_indices = np.array(list(edges_set), dtype=np.int32)
        p2d_a = self.vertices_2d[self.edge_indices[:, 0]]
        p2d_b = self.vertices_2d[self.edge_indices[:, 1]]
        self.edge_rest_lengths = np.linalg.norm(p2d_a - p2d_b, axis=1) * 0.01

        # 2. Bending Constraints
        bending_pairs = []
        for e, tri_list in faces_by_edge.items():
            if len(tri_list) == 2:
                t0, t1 = tri_list[0], tri_list[1]
                opp0 = [v for v in t0 if v not in e][0]
                opp1 = [v for v in t1 if v not in e][0]
                bending_pairs.append((min(opp0, opp1), max(opp0, opp1)))

        if bending_pairs:
            self.bend_indices = np.array(list(set(bending_pairs)), dtype=np.int32)
            bp2d_a = self.vertices_2d[self.bend_indices[:, 0]]
            bp2d_b = self.vertices_2d[self.bend_indices[:, 1]]
            self.bend_rest_lengths = np.linalg.norm(bp2d_a - bp2d_b, axis=1) * 0.01
        else:
            self.bend_indices = np.empty((0, 2), dtype=np.int32)
            self.bend_rest_lengths = np.empty(0, dtype=np.float64)

        # 3. Seam Pairing Constraints
        seam_a_list = []
        seam_b_list = []
        for conn in self.sewing_conns:
            offset_a = self.panel_vertex_ranges[conn.panel_a_id][0]
            offset_b = self.panel_vertex_ranges[conn.panel_b_id][0]
            for idx_a, idx_b in zip(conn.edge_a_vertex_indices, conn.edge_b_vertex_indices):
                seam_a_list.append(offset_a + idx_a)
                seam_b_list.append(offset_b + idx_b)

        self.seam_pairs_a = np.array(seam_a_list, dtype=np.int32)
        self.seam_pairs_b = np.array(seam_b_list, dtype=np.int32)

        # 4. Masses & Valences
        self.masses = np.zeros(self.num_vertices, dtype=np.float64)
        for pid in self.panel_ids:
            m = self.initial_meshes[pid]
            offset = self.panel_vertex_ranges[pid][0]
            for f in m.faces:
                p0 = self.vertices_2d[f[0] + offset]
                p1 = self.vertices_2d[f[1] + offset]
                p2 = self.vertices_2d[f[2] + offset]
                area_m2 = 0.5 * abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])) * 0.0001
                face_mass = area_m2 * self.mass_per_sq_m
                self.masses[f[0] + offset] += face_mass / 3.0
                self.masses[f[1] + offset] += face_mass / 3.0
                self.masses[f[2] + offset] += face_mass / 3.0

        self.masses = np.maximum(self.masses, 1e-4)

        # Precompute Jacobi valences to normalize constraint accumulation
        self.valences = np.ones(self.num_vertices, dtype=np.float64)
        np.add.at(self.valences, self.edge_indices[:, 0], 1.0)
        np.add.at(self.valences, self.edge_indices[:, 1], 1.0)
        if len(self.bend_indices) > 0:
            np.add.at(self.valences, self.bend_indices[:, 0], 0.5)
            np.add.at(self.valences, self.bend_indices[:, 1], 0.5)
        if len(self.seam_pairs_a) > 0:
            np.add.at(self.valences, self.seam_pairs_a, 2.0)
            np.add.at(self.valences, self.seam_pairs_b, 2.0)

    def simulate(self, num_steps: int = 50, sub_iters: int = 12, dt: float = 0.01) -> ClothSimulationResult:
        """
        Runs Jacobi-normalized PBD simulation steps to assemble and drape cloth around avatar.
        """
        gravity_step = 0.00015  # gentle vertical settling
        energy_history = []
        max_displacement = 0.0

        for step in range(num_steps):
            self.positions_prev[:] = self.positions[:]
            self.positions[:, 1] -= gravity_step

            for sub in range(sub_iters):
                d_accum = np.zeros_like(self.positions)

                # 1. Structural Edges
                if len(self.edge_indices) > 0:
                    idx_a = self.edge_indices[:, 0]
                    idx_b = self.edge_indices[:, 1]
                    diff = self.positions[idx_a] - self.positions[idx_b]
                    dist = np.linalg.norm(diff, axis=1)
                    valid = dist > 1e-6
                    C = dist - self.edge_rest_lengths
                    dir_norm = np.zeros_like(diff)
                    dir_norm[valid] = diff[valid] / dist[valid, None]

                    np.add.at(d_accum, idx_a, - 0.5 * (C * 0.8)[:, None] * dir_norm)
                    np.add.at(d_accum, idx_b, + 0.5 * (C * 0.8)[:, None] * dir_norm)

                # 2. Bending Constraints
                if len(self.bend_indices) > 0:
                    b_a = self.bend_indices[:, 0]
                    b_b = self.bend_indices[:, 1]
                    b_diff = self.positions[b_a] - self.positions[b_b]
                    b_dist = np.linalg.norm(b_diff, axis=1)
                    b_valid = b_dist > 1e-6
                    b_C = b_dist - self.bend_rest_lengths
                    b_dir = np.zeros_like(b_diff)
                    b_dir[b_valid] = b_diff[b_valid] / b_dist[b_valid, None]

                    np.add.at(d_accum, b_a, - 0.5 * (b_C * 0.2)[:, None] * b_dir)
                    np.add.at(d_accum, b_b, + 0.5 * (b_C * 0.2)[:, None] * b_dir)

                # 3. Seam Pulling & Welding Constraints (Rigid stitch to midpoint)
                if len(self.seam_pairs_a) > 0:
                    mid = 0.5 * (self.positions[self.seam_pairs_a] + self.positions[self.seam_pairs_b])
                    self.positions[self.seam_pairs_a] = mid
                    self.positions[self.seam_pairs_b] = mid

                # Update with Jacobi normalization and step clamping
                step_delta = d_accum / self.valences[:, None]
                step_norm = np.linalg.norm(step_delta, axis=1, keepdims=True)
                scale = np.minimum(1.0, 0.008 / (step_norm + 1e-9))
                self.positions += step_delta * scale

                # Ensure exact seam closure after step update
                if len(self.seam_pairs_a) > 0:
                    mid = 0.5 * (self.positions[self.seam_pairs_a] + self.positions[self.seam_pairs_b])
                    self.positions[self.seam_pairs_a] = mid
                    self.positions[self.seam_pairs_b] = mid

                # 4. Avatar Torso Collision Projection (Vectorized)
                if self.y_grid is not None:
                    self._resolve_avatar_collisions_vectorized()

            self.velocities = (self.positions - self.positions_prev) / dt
            ke = 0.5 * float(np.sum(self.masses[:, None] * (self.velocities ** 2)))
            energy_history.append(ke)
            max_displacement = float(np.max(np.linalg.norm(self.positions - self.positions_prev, axis=1)))

        simulated_meshes = {}
        starting_meshes = {}
        for pid in self.panel_ids:
            start_i, end_i = self.panel_vertex_ranges[pid]
            m_orig = self.initial_meshes[pid]

            m_start = copy.deepcopy(m_orig)
            m_start.vertices_3d = self.positions_initial[start_i:end_i].round(5).tolist()
            starting_meshes[pid] = m_start

            m_sim = copy.deepcopy(m_orig)
            m_sim.vertices_3d = self.positions[start_i:end_i].round(5).tolist()
            simulated_meshes[pid] = m_sim

        metrics = self._calculate_simulation_metrics(energy_history, max_displacement)
        return ClothSimulationResult(starting_meshes, simulated_meshes, metrics)

    def _resolve_avatar_collisions_vectorized(self):
        """Ultra-fast vectorized radial ellipse projection against avatar torso profile."""
        y_vals = self.positions[:, 1]
        torso_mask = (y_vals >= 0.70) & (y_vals <= 1.45)
        if not np.any(torso_mask):
            return

        y_sub = y_vals[torso_mask]
        zf = np.interp(y_sub, self.y_grid, self.grid_zf)
        zb = np.interp(y_sub, self.y_grid, self.grid_zb)
        rx = np.interp(y_sub, self.y_grid, self.grid_rx) + 0.008
        zc = (zf + zb) * 0.5
        rz = np.maximum(0.06, (zf - zb) * 0.5) + 0.008

        dx = self.positions[torso_mask, 0]
        dz = self.positions[torso_mask, 2] - zc
        dist_sq = (dx / rx)**2 + (dz / rz)**2
        penetrated = (dist_sq < 1.0) & (dist_sq > 1e-6)

        if np.any(penetrated):
            scale = 1.0 / np.sqrt(dist_sq[penetrated])
            sub_indices = np.where(torso_mask)[0][penetrated]
            self.positions[sub_indices, 0] = dx[penetrated] * scale
            self.positions[sub_indices, 2] = zc[penetrated] + dz[penetrated] * scale

    def _calculate_simulation_metrics(self, energy_history: List[float], max_disp: float) -> Dict[str, Any]:
        """Calculates validation metrics: seam closure, non-penetration, strain, and stability."""
        if len(self.seam_pairs_a) > 0:
            diffs = self.positions[self.seam_pairs_a] - self.positions[self.seam_pairs_b]
            gaps = np.linalg.norm(diffs, axis=1) * 1000.0  # in mm
            max_seam_gap_mm = float(np.max(gaps))
            avg_seam_gap_mm = float(np.mean(gaps))
        else:
            max_seam_gap_mm = 0.0
            avg_seam_gap_mm = 0.0

        penetration_count = 0
        if self.y_grid is not None:
            y_vals = self.positions[:, 1]
            torso_mask = (y_vals >= 0.80) & (y_vals <= 1.35)
            if np.any(torso_mask):
                y_sub = y_vals[torso_mask]
                zf = np.interp(y_sub, self.y_grid, self.grid_zf)
                zb = np.interp(y_sub, self.y_grid, self.grid_zb)
                rx = np.interp(y_sub, self.y_grid, self.grid_rx)
                zc = (zf + zb) * 0.5
                rz = (zf - zb) * 0.5
                dx = self.positions[torso_mask, 0]
                dz = self.positions[torso_mask, 2] - zc
                dist_sq = (dx / rx)**2 + (dz / rz)**2
                penetration_count = int(np.sum(dist_sq < 0.98))

        total_3d_area = 0.0
        total_2d_area = 0.0
        for pid in self.panel_ids:
            total_2d_area += self.panels_2d[pid].area_sq_cm
            m = self.initial_meshes[pid]
            offset = self.panel_vertex_ranges[pid][0]
            v3 = self.positions
            for f in m.faces:
                p0 = v3[f[0] + offset]
                p1 = v3[f[1] + offset]
                p2 = v3[f[2] + offset]
                cross = np.cross(p1 - p0, p2 - p0)
                total_3d_area += 0.5 * float(np.linalg.norm(cross)) * 10000.0

        strain_ratio = total_3d_area / max(1e-4, total_2d_area)
        strain_pct = abs(strain_ratio - 1.0) * 100.0

        has_nan = bool(np.any(np.isnan(self.positions)) or np.any(np.isinf(self.positions)))
        settled = bool(energy_history[-1] < 1.0 and max_disp < 0.005)

        return {
            "has_nan": has_nan,
            "is_stable": not has_nan,
            "settled": settled,
            "final_kinetic_energy": round(energy_history[-1], 6),
            "max_step_displacement_mm": round(max_disp * 1000.0, 3),
            "max_seam_gap_mm": round(max_seam_gap_mm, 2),
            "avg_seam_gap_mm": round(avg_seam_gap_mm, 2),
            "seam_closure_pass": bool(max_seam_gap_mm < 5.0),
            "avatar_penetrations": penetration_count,
            "non_penetration_pass": bool(penetration_count == 0),
            "area_3d_sq_cm": round(total_3d_area, 1),
            "area_2d_sq_cm": round(total_2d_area, 1),
            "strain_ratio": round(strain_ratio, 3),
            "strain_pct": round(strain_pct, 2),
            "strain_pass": bool(strain_pct <= 10.0)
        }
