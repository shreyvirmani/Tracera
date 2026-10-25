"""Controlled local HTTP fixtures for collector and SSRF tests.

These servers bind to loopback only, so no test traffic ever leaves the
machine. They exist to exercise redirect handling and connection pinning
against real sockets instead of mocks.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _RedirectHandler(BaseHTTPRequestHandler):
    """Redirects every request to the path set on the server instance."""

    redirect_target = "/elsewhere"

    def do_GET(self):  # noqa: N802
        self.send_response(302)
        self.send_header("Location", self.redirect_target)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):  # silence test output
        pass


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"<html><body>ok</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _serve(handler_cls):
    last_error: OSError | None = None
    for port in (8080, 8443, 80, 443):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            return server, port
        except OSError as e:
            last_error = e
            continue
    raise RuntimeError(f"No allowed port free for test fixture: {last_error}")


def start_redirect_server(target: str):
    """Start a loopback server that 302-redirects to `target`."""
    server, port = _serve(_RedirectHandler)
    server.redirect_target = target  # type: ignore[attr-defined]
    return server, port


def start_ok_server():
    """Start a loopback server that returns a minimal 200 HTML page."""
    return _serve(_OkHandler)


def stop(server) -> None:
    server.shutdown()
    server.server_close()
