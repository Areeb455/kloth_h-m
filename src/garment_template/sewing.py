"""
Sewing Connections Module.
Pairs corresponding seams between panels, resamples edge vertices 1:1,
and computes edge lengths, gather ratios, and assembly order.
Implements Category 4: Sewing connections.
"""

from typing import Dict, List, Tuple
import math
import numpy as np

from .models import Panel2DGeometry, PanelMesh, SewingConnection


class SewingEngine:
    def __init__(self, panels_2d: Dict[str, Panel2DGeometry], meshes: Dict[str, PanelMesh]):
        self.panels_2d = panels_2d
        self.meshes = meshes

    def _find_edge_vertices(self, panel_id: str, edge_name: str) -> Tuple[List[int], float]:
        """
        Finds the mesh vertex indices along a named edge segment and calculates total edge length in cm.
        """
        geo = self.panels_2d[panel_id]
        mesh = self.meshes[panel_id]

        if edge_name not in geo.edges:
            # Fallback: estimate from bounding edge
            return [0, 1], 10.0

        pt_indices = geo.edges[edge_name]
        start_pt = geo.contour_points[pt_indices[0]]
        end_pt = geo.contour_points[pt_indices[1]]

        # Find mesh vertices that lie close to the line segment between start_pt and end_pt
        p_start = np.array([start_pt.x, start_pt.y])
        p_end = np.array([end_pt.x, end_pt.y])
        seg_vec = p_end - p_start
        seg_len = float(np.linalg.norm(seg_vec))

        if seg_len < 1e-4:
            return [0], 0.0

        seg_unit = seg_vec / seg_len

        matched_v_indices = []
        projections = []

        for v_idx, v2d in enumerate(mesh.vertices_2d):
            p = np.array([v2d[0], v2d[1]])
            v_rel = p - p_start
            proj = float(np.dot(v_rel, seg_unit))
            perp_dist = float(np.linalg.norm(v_rel - proj * seg_unit))

            # Within 0.8 cm perpendicular distance and along segment length
            if perp_dist <= 0.8 and (-0.5 <= proj <= seg_len + 0.5):
                matched_v_indices.append(v_idx)
                projections.append(proj)

        # Sort vertices along the seam direction
        sorted_pairs = sorted(zip(projections, matched_v_indices))
        sorted_indices = [idx for _, idx in sorted_pairs]

        if not sorted_indices:
            # Fallback to closest 2 vertices
            sorted_indices = [0, 1]

        return sorted_indices, round(seg_len, 2)

    def generate_sewing_connections(self) -> List[SewingConnection]:
        """
        Constructs all standard assembly sewing connections.
        """
        seam_definitions = [
            # Shoulder seams
            {
                "seam_id": "seam_shoulder_right",
                "panel_a": "front_bodice", "edge_a": "shoulder_right",
                "panel_b": "back_bodice",  "edge_b": "shoulder_right",
                "order": 1
            },
            {
                "seam_id": "seam_shoulder_left",
                "panel_a": "front_bodice", "edge_a": "shoulder_left",
                "panel_b": "back_bodice",  "edge_b": "shoulder_left",
                "order": 2
            },
            # Bodice side seams
            {
                "seam_id": "seam_bodice_side_right",
                "panel_a": "front_bodice", "edge_a": "side_seam_right",
                "panel_b": "back_bodice",  "edge_b": "side_seam_right",
                "order": 3
            },
            {
                "seam_id": "seam_bodice_side_left",
                "panel_a": "front_bodice", "edge_a": "side_seam_left",
                "panel_b": "back_bodice",  "edge_b": "side_seam_left",
                "order": 4
            },
            # Waist joining seams
            {
                "seam_id": "seam_waist_front",
                "panel_a": "front_bodice", "edge_a": "waist_right",
                "panel_b": "front_skirt",  "edge_b": "waist_top_right",
                "order": 5
            },
            {
                "seam_id": "seam_waist_back",
                "panel_a": "back_bodice", "edge_a": "waist_right",
                "panel_b": "back_skirt",  "edge_b": "waist_top_right",
                "order": 6
            },
            # Skirt side seams
            {
                "seam_id": "seam_skirt_side_right",
                "panel_a": "front_skirt", "edge_a": "skirt_side_right",
                "panel_b": "back_skirt",  "edge_b": "skirt_side_right",
                "order": 7
            },
            {
                "seam_id": "seam_skirt_side_left",
                "panel_a": "front_skirt", "edge_a": "skirt_side_left",
                "panel_b": "back_skirt",  "edge_b": "skirt_side_left",
                "order": 8
            },
        ]

        connections: List[SewingConnection] = []

        for s_def in seam_definitions:
            va, len_a = self._find_edge_vertices(s_def["panel_a"], s_def["edge_a"])
            vb, len_b = self._find_edge_vertices(s_def["panel_b"], s_def["edge_b"])

            # Harmonize vertex count for 1:1 simulation mapping
            min_count = min(len(va), len(vb))
            if min_count > 1:
                # Subsample evenly to identical vertex count
                idx_a_sub = [va[int(i)] for i in np.linspace(0, len(va) - 1, min_count)]
                idx_b_sub = [vb[int(i)] for i in np.linspace(0, len(vb) - 1, min_count)]
            else:
                idx_a_sub = va
                idx_b_sub = vb

            gather_ratio = round(len_a / max(1e-4, len_b), 3)
            delta = abs(len_a - len_b)
            is_valid = (delta <= 1.0) or (0.90 <= gather_ratio <= 1.10)

            conn = SewingConnection(
                seam_id=s_def["seam_id"],
                panel_a_id=s_def["panel_a"],
                edge_a_name=s_def["edge_a"],
                edge_a_vertex_indices=idx_a_sub,
                edge_a_length_cm=len_a,
                panel_b_id=s_def["panel_b"],
                edge_b_name=s_def["edge_b"],
                edge_b_vertex_indices=idx_b_sub,
                edge_b_length_cm=len_b,
                seam_order=s_def["order"],
                gather_ratio=gather_ratio,
                is_valid=is_valid,
                tolerance_cm=0.5
            )
            connections.append(conn)

        return connections
