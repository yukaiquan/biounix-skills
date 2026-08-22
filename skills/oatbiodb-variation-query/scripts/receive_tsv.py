#!/usr/bin/env python3
"""
[DEPRECATED] Receive genotype TSV data from the browser via HTTP POST.

This script belongs to the OLD browser-based workflow (local HTTP receiver + browser JS
fetch). It is kept for reference only. Do NOT start this server for new queries.

Usage:
    python3 receive_tsv.py <output_file> [port]

Example:
    python3 receive_tsv.py /path/to/chr1A_4696935.tsv 8765

The server listens on 127.0.0.1:<port> (default 8765). After a successful POST it
writes the raw body to <output_file> and prints the byte count.
"""
import http.server
import socketserver
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 receive_tsv.py <output_file> [port]", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            with open(output_file, 'wb') as f:
                f.write(body)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'OK')
            print(f"WROTE {len(body)} bytes to {output_file}", flush=True)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"LISTENING on {port}", flush=True)
        httpd.serve_forever()


if __name__ == '__main__':
    main()
