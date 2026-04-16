#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.error
import os

PORT = int(os.environ.get('PORT', 8080))
ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/proxy':
            self._proxy()
        else:
            self.send_error(404, 'Not found')

    def _proxy(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        api_key = self.headers.get('x-api-key', '')

        print(f'[proxy] → Anthropic  key={api_key[:12]}...  body={body[:120]}')

        req = urllib.request.Request(
            ANTHROPIC_URL,
            data=body,
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req) as resp:
                resp_body = resp.read()
                print(f'[proxy] ← {resp.status}  {resp_body[:120]}')
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json')
                self._cors()
                self.end_headers()
                self.wfile.write(resp_body)

        except urllib.error.HTTPError as e:
            resp_body = e.read()
            print(f'[proxy] ← HTTPError {e.code}  {resp_body[:200]}')
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(resp_body)

        except Exception as e:
            print(f'[proxy] ← Exception: {e}')
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(f'{{"error":{{"message":"{e}"}}}}'.encode())

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, x-api-key')

    def log_message(self, fmt, *args):
        print(self.address_string(), '-', fmt % args)


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'French quiz running at http://localhost:{PORT}')
    print(f'Anthropic proxy at   http://localhost:{PORT}/api/proxy')
    httpd.serve_forever()
