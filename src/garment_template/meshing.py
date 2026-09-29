"""
Mesh Generation and Triangulation Module.
Converts 2D parametric pattern panels into clean 2D/3D triangle meshes.
Implements Category 2: Triangle mesh with vertex correspondence and UV coordinates.
Uses GEOS / Shapely internal triangulation for robust, dependency-light execution.
"""

from typing import Dict, List, Tuple
import numpy as np
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import triangulate

from .models import Panel2DGeometry, PanelMesh


class PanelMesher:
    def __init__(self, target_edge_length_cm: float = 3.0):
        """
        target_edge_length_cm: Grid resolution for garment surface tessellation.
        """
        self.grid_step = target_edge_length_cm

    def triangulate_panel(self, panel_geo: Panel2DGeometry) -> PanelMesh:
        """
        Triangulates a 2D panel polygon using boundary points + interior grid sampling.
        Filters triangles outside concave boundaries (e.g., necklines, armholes).
        """
        boundary_coords = [(p.x, p.y) for p in panel_geo.contour_points]
        poly = Polygon(boundary_coords)
        minx, miny, maxx, maxy = poly.bounds

        # 1. Collect points: unique boundary points + internal grid
        all_pts = list(boundary_coords)
        seen_pts = {(round(p[0], 3), round(p[1], 3)) for p in all_pts}

        # Generate internal grid
        xs = np.arange(minx + self.grid_step, maxx, self.grid_step)
        ys = np.arange(miny + self.grid_step, maxy, self.grid_step)
        for x in xs:
            for y in ys:
                pt = Point(x, y)
                # Ensure point is well inside polygon with a buffer
                if poly.contains(pt) and poly.boundary.distance(pt) > (self.grid_step * 0.4):
                    k = (round(float(x), 3), round(float(y), 3))
                    if k not in seen_pts:
                        seen_pts.add(k)
                        all_pts.append(k)

        # Map each point coordinate to its index
        pt_to_idx = {p: i for i, p in enumerate(all_pts)}

        # 2. Delaunay Triangulation using Shapely GEOS
        mp = MultiPoint(all_pts)
        raw_triangles = triangulate(mp)

        valid_faces: List[Tuple[int, int, int]] = []
        for tri in raw_triangles:
            # Check if triangle centroid is inside the original panel polygon
            centroid = tri.centroid
            if poly.contains(centroid) and tri.area > 1e-4:
                coords = list(tri.exterior.coords)[:3]
                # Match each coordinate to its index in all_pts
                indices = []
                for c in coords:
                    ck = (round(c[0], 3), round(c[1], 3))
                    if ck in pt_to_idx:
                        indices.append(pt_to_idx[ck])
                    else:
                        # Find closest point
                        dists = [((p[0] - c[0])**2 + (p[1] - c[1])**2) for p in all_pts]
                        indices.append(int(np.argmin(dists)))

                if len(set(indices)) == 3:
                    p0 = all_pts[indices[0]]
                    p1 = all_pts[indices[1]]
                    p2 = all_pts[indices[2]]
                    # Ensure positive counter-clockwise winding
                    cross_val = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
                    if cross_val < 0:
                        valid_faces.append((indices[0], indices[2], indices[1]))
                    else:
                        valid_faces.append((indices[0], indices[1], indices[2]))

        # 3. Compute normalized UV coordinates [0, 1]
        span_x = max(1e-5, maxx - minx)
        span_y = max(1e-5, maxy - miny)
        uvs: List[Tuple[float, float]] = []
        for p in all_pts:
            u = round(float((p[0] - minx) / span_x), 4)
            v = round(float((p[1] - miny) / span_y), 4)
            uvs.append((u, v))

        # 4. Generate initial flat 3D coords (in meters: cm * 0.01)
        vertices_3d: List[Tuple[float, float, float]] = []
        for p in all_pts:
            vertices_3d.append((round(p[0] * 0.01, 4), round(p[1] * 0.01, 4), 0.0))

        return PanelMesh(
            panel_id=panel_geo.panel_id,
            vertex_count=len(all_pts),
            face_count=len(valid_faces),
            vertices_2d=[(round(p[0], 3), round(p[1], 3)) for p in all_pts],
            vertices_3d=vertices_3d,
            faces=valid_faces,
            uvs=uvs
        )

    def triangulate_all(self, panels: Dict[str, Panel2DGeometry]) -> Dict[str, PanelMesh]:
        """Triangulates all 2D panels into corresponding meshes."""
        return {pid: self.triangulate_panel(geo) for pid, geo in panels.items()}
