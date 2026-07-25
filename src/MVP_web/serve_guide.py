"""
星星家庭 - 家长使用说明页面服务器
替换旧 Streamlit 界面，在 8501 端口单独提供家长使用说明 HTML 页面。
启动: python serve_guide.py
"""

import http.server
import os
import sys

PORT = 8501
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "家长使用说明.html")


class GuideHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_html()
        elif self.path == "/health":
            self._serve_text("ok")
        else:
            # 对于未知路径也返回说明页（SPA fallback）
            self._serve_html()

    def _serve_html(self):
        try:
            with open(HTML_FILE, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._serve_error(404, "家长使用说明页面不存在")

    def _serve_text(self, text: str):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_error(self, code: int, message: str):
        data = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # 简洁日志
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))


def main():
    abs_path = os.path.abspath(HTML_FILE)
    if not os.path.exists(abs_path):
        print(f"错误: 找不到 HTML 文件: {abs_path}")
        sys.exit(1)

    print(f"星星家庭 · 家长使用说明")
    print(f"服务地址: http://localhost:{PORT}")
    print(f"HTML 文件: {abs_path}")
    print(f"按 Ctrl+C 停止\n")

    server = http.server.HTTPServer(("0.0.0.0", PORT), GuideHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
