"""Serve the isolated preview and an explicit allowlist of existing brand assets."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "/hero-face.png": (ROOT / "design-previews/hero-face.png", "image/png"),
    "/": (ROOT / "design-previews/home-motion.html", "text/html; charset=utf-8"),
    "/home-motion.html": (ROOT / "design-previews/home-motion.html", "text/html; charset=utf-8"),
    "/frontend/public/assets/aphrodize-logo.svg": (ROOT / "frontend/public/assets/aphrodize-logo.svg", "image/svg+xml"),
    "/frontend/public/assets/aphrodize-home-background-118c8b84.mp4": (ROOT / "frontend/public/assets/aphrodize-home-background-118c8b84.mp4", "video/mp4"),
    "/frontend/src/app/fonts/Montserrat-Variable.ttf": (ROOT / "frontend/src/app/fonts/Montserrat-Variable.ttf", "font/ttf"),
    "/frontend/src/app/fonts/LibreBaskerville-Variable.ttf": (ROOT / "frontend/src/app/fonts/LibreBaskerville-Variable.ttf", "font/ttf"),
}


class PreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        item = FILES.get(self.path.split("?", 1)[0])
        if not item or not item[0].is_file():
            self.send_error(404)
            return
        data = item[0].read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", item[1])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print("Isolated preview: http://localhost:3011/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 3011), PreviewHandler).serve_forever()
