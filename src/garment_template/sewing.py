"""
Sewing Connections Module.
Pairs corresponding seams between panels, resamples edge vertices 1:1,
and computes edge lengths, gather ratios, and assembly order.
Implements Category 4: Sewing connections.
"""

from typing import Dict, List, Tuple
import numpy as np

from .models import Panel2DGeometry, PanelMesh, SewingConnection


class SewingEngine:
    def __init__(self, panels_2d: Dict[str, Panel2DGeometry], meshes: Dict[str, PanelMesh]):
        self.panels_2d = panels_2d
        self.meshes = meshes

    def _find_edge_vertices(self, panel_id: str, edge_name: str) -> Tuple[List[int], float]:
        geo = self.panels_2d[panel_id]
        if edge_name not in geo.edges:
            return [0, 1], 10.0

        start_idx, end_idx = geo.edges[edge_name]
        n_pts = len(geo.contour_points)

        # Get all contour indices along this edge segment
        if start_idx <= end_idx:
            raw_indices = list(range(start_idx, end_idx + 1))
        else:
            raw_indices = list(range(start_idx, n_pts)) + list(range(0, end_idx + 1))

        pts = [geo.contour_points[i] for i in raw_indices]

        # Calculate accurate cumulative polyline edge length
        coords = np.array([[p.x, p.y] for p in pts])
        edge_length_cm = float(np.sum(np.linalg.norm(np.diff(coords, axis=0), axis=1)))

        # Sort anatomically to guarantee 1:1 topological alignment:
        # Vertical seams (side seams, center back seam): top to bottom (Y descending)
        if "side" in edge_name or "center_back" in edge_name:
            sorted_pairs = sorted(zip([-p.y for p in pts], raw_indices))
            sorted_indices = [idx for _, idx in sorted_pairs]
        # Horizontal / Shoulder seams: inner neck to outer armhole (|X| ascending)
        elif "shoulder" in edge_name:
            sorted_pairs = sorted(zip([abs(p.x) for p in pts], raw_indices))
            sorted_indices = [idx for _, idx in sorted_pairs]
        else:
            sorted_indices = raw_indices

        return sorted_indices, round(edge_length_cm, 2)

    def generate_sewing_connections(self) -> List[SewingConnection]:
        seam_definitions = [
            # 1. Right Shoulder
            {
                "seam_id": "seam_shoulder_right",
                "panel_a": "front_panel", "edge_a": "shoulder_right",
                "panel_b": "back_right_panel", "edge_b": "shoulder_right",
                "order": 1
            },
            # 2. Left Shoulder
            {
                "seam_id": "seam_shoulder_left",
                "panel_a": "front_panel", "edge_a": "shoulder_left",
                "panel_b": "back_left_panel", "edge_b": "shoulder_left",
                "order": 2
            },
            # 3. Center Back Seam (full spine length)
            {
                "seam_id": "seam_center_back",
                "panel_a": "back_left_panel", "edge_a": "center_back_seam",
                "panel_b": "back_right_panel", "edge_b": "center_back_seam",
                "order": 3
            },
            # 4. Continuous Right Side Seam (underarm to hem)
            {
                "seam_id": "seam_side_right",
                "panel_a": "front_panel", "edge_a": "side_seam_right",
                "panel_b": "back_right_panel", "edge_b": "side_seam_right",
                "order": 4
            },
            # 5. Continuous Left Side Seam (underarm to hem)
            {
                "seam_id": "seam_side_left",
                "panel_a": "front_panel", "edge_a": "side_seam_left",
                "panel_b": "back_left_panel", "edge_b": "side_seam_left",
                "order": 5
            }
        ]

        connections: List[SewingConnection] = []

        for s_def in seam_definitions:
            va, len_a = self._find_edge_vertices(s_def["panel_a"], s_def["edge_a"])
            vb, len_b = self._find_edge_vertices(s_def["panel_b"], s_def["edge_b"])

            # Equalize vertex count for 1:1 simulation mapping
            pair_count = max(2, min(len(va), len(vb)))
            idx_a_sub = [va[int(round(i))] for i in np.linspace(0, len(va) - 1, pair_count)]
            idx_b_sub = [vb[int(round(i))] for i in np.linspace(0, len(vb) - 1, pair_count)]

            gather_ratio = round(len_a / max(1e-4, len_b), 3)
            delta = abs(len_a - len_b)
            is_valid = (delta <= 3.0) or (0.90 <= gather_ratio <= 1.10)

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
                tolerance_cm=1.0
            )
            connections.append(conn)

        return connections
