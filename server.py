import logging
import http.server
import socketserver

PORT = 9999


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        logging.error(self.headers)
        http.server.SimpleHTTPRequestHandler.do_GET(self)


httpd = socketserver.TCPServer(('localhost', PORT), Handler)

httpd.serve_forever()
