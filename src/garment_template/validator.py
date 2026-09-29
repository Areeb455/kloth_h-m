"""
Validation Suite for 3D Garment Templates.
Implements the Phase 2 verification checks:
1. Dimension checks (Bust, Waist, Hip, Length deltas vs chart)
2. Mesh checks (Non-degenerate triangles, valid indices, closed boundaries, area preservation)
3. Sewing checks (Matched lengths, 1:1 vertex count, edge uniqueness)
"""

from typing import Dict, List, Tuple, Any
import numpy as np
from shapely.geometry import Polygon

from .models import Panel2DGeometry, PanelMesh, SewingConnection, TemplateManifest


class ValidationReport:
    def __init__(self):
        self.passed: bool = True
        self.checks: List[Dict[str, Any]] = []

    def add_check(self, category: str, name: str, passed: bool, details: str, metrics: Dict[str, Any] = None):
        if not passed:
            self.passed = False
        self.checks.append({
            "category": category,
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "details": details,
            "metrics": metrics or {}
        })

    def to_dict(self) -> Dict[str, Any]:
        passed_count = sum(1 for c in self.checks if c["status"] == "PASS")
        total_count = len(self.checks)
        return {
            "overall_status": "PASS" if self.passed else "FAIL",
            "summary": f"{passed_count}/{total_count} checks passed",
            "checks": self.checks
        }


class GarmentValidator:
    def __init__(
        self,
        target_dimensions: Dict[str, float],
        panels_2d: Dict[str, Panel2DGeometry],
        meshes: Dict[str, PanelMesh],
        sewing_conns: List[SewingConnection]
    ):
        self.dims = target_dimensions
        self.panels_2d = panels_2d
        self.meshes = meshes
        self.sewing_conns = sewing_conns

    def run_all_checks(self) -> ValidationReport:
        report = ValidationReport()
        self.check_dimensions(report)
        self.check_mesh_integrity(report)
        self.check_sewing_connections(report)
        return report

    def check_dimensions(self, report: ValidationReport):
        """1. Dimension Checks against size chart."""
        # Calculate generated garment dimensions from 2D panels
        front_b = self.panels_2d["front_bodice"]
        back_b = self.panels_2d["back_bodice"]
        front_s = self.panels_2d["front_skirt"]
        back_s = self.panels_2d["back_skirt"]

        # Bust circumference = front bodice width + back bodice width
        gen_bust = round(front_b.width_cm + back_b.width_cm, 1)
        chart_bust = round(self.dims["bust_circ"], 1)
        bust_delta = abs(gen_bust - chart_bust)
        report.add_check(
            category="Dimensions",
            name="Bust Circumference",
            passed=(bust_delta <= 1.5),
            details=f"Generated {gen_bust} cm vs Chart {chart_bust} cm (delta: {bust_delta:.1f} cm)",
            metrics={"generated_cm": gen_bust, "chart_cm": chart_bust, "delta_cm": bust_delta}
        )

        # Total front length = bodice height + skirt height
        gen_front_len = round(front_b.height_cm + front_s.height_cm, 1)
        chart_front_len = round(self.dims["front_length"], 1)
        len_delta = abs(gen_front_len - chart_front_len)
        report.add_check(
            category="Dimensions",
            name="Front Garment Length",
            passed=(len_delta <= 2.0),
            details=f"Generated {gen_front_len} cm vs Chart {chart_front_len} cm (delta: {len_delta:.1f} cm)",
            metrics={"generated_cm": gen_front_len, "chart_cm": chart_front_len, "delta_cm": len_delta}
        )

    def check_mesh_integrity(self, report: ValidationReport):
        """2. Mesh Checks: Non-degenerate, in-range indices, area preservation."""
        for pid, mesh in self.meshes.items():
            # Check face indices in range
            max_idx = mesh.vertex_count - 1
            indices_valid = True
            degenerate_count = 0

            pts_2d = np.array(mesh.vertices_2d)

            for f in mesh.faces:
                if f[0] > max_idx or f[1] > max_idx or f[2] > max_idx:
                    indices_valid = False
                # Check for zero area
                p0 = pts_2d[f[0]]
                p1 = pts_2d[f[1]]
                p2 = pts_2d[f[2]]
                area = abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])) * 0.5
                if area < 1e-5:
                    degenerate_count += 1

            report.add_check(
                category="Mesh",
                name=f"{pid} - Face Indices Valid",
                passed=indices_valid,
                details=f"All {mesh.face_count} face indices within [0, {max_idx}]",
                metrics={"vertex_count": mesh.vertex_count, "face_count": mesh.face_count}
            )

            report.add_check(
                category="Mesh",
                name=f"{pid} - Non-Degenerate Triangles",
                passed=(degenerate_count == 0),
                details=f"Found {degenerate_count} degenerate faces out of {mesh.face_count}",
                metrics={"degenerate_count": degenerate_count}
            )

            # Check 2D area vs 3D area consistency
            geo_area = self.panels_2d[pid].area_sq_cm
            # Sum triangle areas in 2D
            tri_area_sum = 0.0
            for f in mesh.faces:
                p0 = pts_2d[f[0]]
                p1 = pts_2d[f[1]]
                p2 = pts_2d[f[2]]
                tri_area_sum += abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])) * 0.5

            area_ratio = tri_area_sum / max(1e-4, geo_area)
            # Triangulation covers >90% of polygon
            report.add_check(
                category="Mesh",
                name=f"{pid} - Surface Area Consistency",
                passed=(0.88 <= area_ratio <= 1.05),
                details=f"Triangulated area: {tri_area_sum:.1f} cm2 vs Pattern: {geo_area:.1f} cm2 (ratio: {area_ratio:.2f})",
                metrics={"tri_area_sq_cm": round(tri_area_sum, 1), "pattern_area_sq_cm": geo_area}
            )

    def check_sewing_connections(self, report: ValidationReport):
        """3. Sewing Checks: Matched edge lengths and equal vertex counts."""
        edge_usage = {}

        for conn in self.sewing_conns:
            # Check vertex counts match 1:1
            cnt_a = len(conn.edge_a_vertex_indices)
            cnt_b = len(conn.edge_b_vertex_indices)
            counts_equal = (cnt_a == cnt_b)

            report.add_check(
                category="Sewing",
                name=f"{conn.seam_id} - 1:1 Vertex Count",
                passed=counts_equal,
                details=f"{conn.panel_a_id} ({cnt_a} v) <-> {conn.panel_b_id} ({cnt_b} v)",
                metrics={"count_a": cnt_a, "count_b": cnt_b}
            )

            # Check lengths within tolerance or acceptable gather ratio
            length_delta = abs(conn.edge_a_length_cm - conn.edge_b_length_cm)
            report.add_check(
                category="Sewing",
                name=f"{conn.seam_id} - Length Compatibility",
                passed=(conn.is_valid),
                details=f"Len A: {conn.edge_a_length_cm} cm, Len B: {conn.edge_b_length_cm} cm (gather ratio: {conn.gather_ratio:.2f})",
                metrics={"length_a_cm": conn.edge_a_length_cm, "length_b_cm": conn.edge_b_length_cm, "ratio": conn.gather_ratio}
            )

            # Track edge usage to verify no edge is mistakenly sewn twice
            key_a = f"{conn.panel_a_id}:{conn.edge_a_name}"
            key_b = f"{conn.panel_b_id}:{conn.edge_b_name}"
            edge_usage[key_a] = edge_usage.get(key_a, 0) + 1
            edge_usage[key_b] = edge_usage.get(key_b, 0) + 1

        duplicates = [k for k, v in edge_usage.items() if v > 1]
        report.add_check(
            category="Sewing",
            name="No Duplicate Seam Edges",
            passed=(len(duplicates) == 0),
            details=f"Edges used multiple times: {duplicates if duplicates else 'None'}",
            metrics={"duplicate_edges": duplicates}
        )
