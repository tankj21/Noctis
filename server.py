
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def run_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

    server = HTTPServer(('0.0.0.0', 8000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
