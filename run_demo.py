"""
Demo UI Server for the 3D Garment Template Generator.
Launches the interactive WebGL 3D/2D visualizer on http://localhost:8000
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8000))
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class GarmentDemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/viewer/index.html"
        return super().do_GET()


def main():
    os.chdir(ROOT_DIR)
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, GarmentDemoHandler)
    url = f"http://localhost:{PORT}/viewer/index.html"

    print("=" * 70)
    print("  KLOTH 3D GARMENT TEMPLATE GENERATOR - DEMO SERVER")
    print(f"  Live UI: {url}")
    print("  Press Ctrl+C to terminate.")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo server stopped.")


if __name__ == "__main__":
    main()
