# -*- coding: utf-8 -*-
"""
ERD 시각화용 테이블 스키마 API (CORS 허용)
- GET /erd_tables.json → data/erd_tables.json 내용 반환
- React ERD 뷰어(localhost:5173)에서 fetch 가능하도록 CORS 헤더 설정
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 프로젝트 루트 기준
DATA_DIR = Path(__file__).resolve().parent / "data"
ERD_JSON = DATA_DIR / "erd_tables.json"
PORT = 8765


class CORSRequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/erd_tables.json" or self.path == "/erd_tables.json/":
            self._serve_erd_json()
        else:
            self.send_response(404)
            self._send_cors()
            self.end_headers()

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_erd_json(self):
        try:
            if ERD_JSON.exists():
                body = ERD_JSON.read_text(encoding="utf-8")
            else:
                body = json.dumps({"tables": []}, ensure_ascii=False, indent=2)
        except Exception:
            body = json.dumps({"tables": []}, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors()
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # 조용히 실행 (선택)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("127.0.0.1", PORT), CORSRequestHandler)
    print(f"ERD API: http://127.0.0.1:{PORT}/erd_tables.json (CORS enabled)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
