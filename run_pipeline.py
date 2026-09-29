"""
Main execution script for the 3D Garment Template Generator.
Usage:
    py -3.11 run_pipeline.py
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from src.garment_template.pipeline import PipelineOrchestrator


def main():
    print("=" * 70)
    print("  KLOTH 3D GARMENT TEMPLATE GENERATOR")
    print("  Vision-Guided Parametric Pipeline Execution")
    print("=" * 70)

    size_chart = os.path.join(ROOT_DIR, "samples", "size_chart.json")
    details = os.path.join(ROOT_DIR, "samples", "product_details.json")
    avatar_glb = os.path.join(ROOT_DIR, "assets", "person_0.glb")
    front_img = os.path.join(ROOT_DIR, "samples", "front.jpg")
    back_img = os.path.join(ROOT_DIR, "samples", "back.jpg")
    output_dir = os.path.join(ROOT_DIR, "output")

    orchestrator = PipelineOrchestrator(
        size_chart_path=size_chart,
        product_details_path=details,
        avatar_glb_path=avatar_glb,
        front_image_path=front_img,
        back_image_path=back_img,
        output_dir=output_dir
    )

    pkg_dir, val_report, loaded = orchestrator.run()

    status_label = "COMPLETE & VERIFIED" if val_report.passed else "COMPLETE (VALIDATION: FAIL - SIZE MISMATCH DOCUMENTED)"
    print("\n" + "=" * 70)
    print(f"  PIPELINE EXECUTION {status_label}")
    print(f"  Package Directory: {pkg_dir}")
    print(f"  Package Archive:   {os.path.join(output_dir, 'garment_template_package.zip')}")
    print(f"  Validation Checks: {val_report.to_dict()['summary']}")
    print(f"  Overall Status:    {val_report.to_dict()['overall_status']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
