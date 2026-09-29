"""
Grading and Multi-Size Mesh Generation Engine.
Implements Category 8: Size labels, grading information and alternate meshes.
Generates fully graded 3D meshes for all supported sizes (XXS, XS, S, M)
with detailed geometric deltas relative to the primary base size (XS).
"""

import os
from typing import Dict, List, Tuple, Callable
import numpy as np

from .models import GradingInfo, SizeMeshRef, SizeDeltas, PanelMesh
from .sizing import SizingEngine
from .patterns import PatternGenerator
from .meshing import PanelMesher
from .placement import GarmentPlacer


class GradingEngine:
    def __init__(
        self,
        sizing_engine: SizingEngine,
        landmarks: Dict[str, float],
        torso_profile_fn: Callable[[float], Dict[str, float]] = None,
        vision_proportions: Dict[str, float] = None
    ):
        self.sizing = sizing_engine
        self.landmarks = landmarks
        self.torso_profile_fn = torso_profile_fn
        self.vision_proportions = vision_proportions or {}
        self.base_size = self.sizing.primary_base_size

    def generate_size_meshes(
        self,
        output_dir: str
    ) -> Tuple[GradingInfo, Dict[str, Dict[str, PanelMesh]]]:
        os.makedirs(output_dir, exist_ok=True)
        mesher = PanelMesher(target_edge_length_cm=3.0)
        placer = GarmentPlacer(self.landmarks, self.torso_profile_fn)

        all_size_meshes: Dict[str, Dict[str, PanelMesh]] = {}
        size_refs: Dict[str, SizeMeshRef] = {}

        for size_label in self.sizing.supported_sizes:
            dims = self.sizing.get_garment_dimensions(size_label)
            deltas = self.sizing.get_grading_deltas(size_label, self.base_size)

            # Generate 2D patterns for this size incorporating vision proportions
            p_gen = PatternGenerator(dims, self.vision_proportions)
            panels_2d = p_gen.generate_all_panels()

            # Triangulate
            flat_meshes = mesher.triangulate_all(panels_2d)

            # 3D placement wrapped around real torso cross-sections
            placed_meshes, _ = placer.place_all_panels(flat_meshes)
            all_size_meshes[size_label] = placed_meshes

            # Export unified OBJ file for this size
            obj_filename = f"garment_{size_label}.obj"
            obj_path = os.path.join(output_dir, obj_filename)
            v_cnt, f_cnt = self._export_unified_obj(placed_meshes, obj_path)

            size_refs[size_label] = SizeMeshRef(
                size_label=size_label,
                is_base_size=(size_label == self.base_size),
                dimensions_cm=dims,
                deltas_from_base=deltas,
                mesh_obj_filename=obj_filename,
                vertex_count=v_cnt,
                face_count=f_cnt
            )

        grading_info = GradingInfo(
            base_size=self.base_size,
            supported_sizes=self.sizing.supported_sizes,
            size_meshes=size_refs
        )

        return grading_info, all_size_meshes

    @staticmethod
    def _export_unified_obj(placed_meshes: Dict[str, PanelMesh], obj_path: str) -> Tuple[int, int]:
        total_vertices = 0
        total_faces = 0
        vertex_offset = 1

        with open(obj_path, "w") as f:
            f.write("# Kloth Garment Template Generator - Exported OBJ\n")

            for pid, mesh in placed_meshes.items():
                f.write(f"\ng {pid}\n")
                f.write(f"usemtl Material_{pid}\n")

                for v in mesh.vertices_3d:
                    f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
                    total_vertices += 1

                for uv in mesh.uvs:
                    f.write(f"vt {uv[0]:.5f} {uv[1]:.5f}\n")

                for face in mesh.faces:
                    i0 = face[0] + vertex_offset
                    i1 = face[1] + vertex_offset
                    i2 = face[2] + vertex_offset
                    f.write(f"f {i0}/{i0} {i1}/{i1} {i2}/{i2}\n")
                    total_faces += 1

                vertex_offset += mesh.vertex_count

        return total_vertices, total_faces
