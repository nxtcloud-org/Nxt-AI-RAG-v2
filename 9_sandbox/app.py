"""서버코드 — 브라우저와 RAG를 연결하는 부분.

브라우저(index.html)가 보내는 요청을 받아서:
  GET  /            → 화면(index.html)을 보여줌
  GET  /api/status  → 지금 상태(문서 개수, 청크 개수, 사용 중인 AI)
  POST /api/ask     → 질문 → 벡터 검색 → AI 답변
  POST /api/upload  → 문서 파일을 data 폴더에 저장
  POST /api/rebuild → 벡터디비 새로 만들기
  POST /api/reset   → 벡터디비 초기화(삭제)

실행: python app.py  →  브라우저에서 http://localhost:8501
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import llm
import rag

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def render_index():
    """index.html을 읽어 제목만 config 값으로 끼워 넣습니다."""
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()
    return (html.replace("{{TITLE}}", config.APP_TITLE)
                .replace("{{SUBTITLE}}", config.APP_SUBTITLE))


class Handler(BaseHTTPRequestHandler):
    # ── 응답 보내기 도우미 ──
    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), code=code)

    # ── 화면과 상태 ──
    def do_GET(self):
        if self.path == "/":
            self._send(render_index(), ctype="text/html; charset=utf-8")
        elif self.path == "/guide":
            with open(os.path.join(BASE_DIR, "guide.html"), encoding="utf-8") as f:
                self._send(f.read(), ctype="text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._json(rag.db_info())
        else:
            self._json({"error": "없는 주소입니다"}, code=404)

    # ── 동작(질문·업로드·DB 관리) ──
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            if self.path == "/api/ask":
                question = json.loads(body)["question"].strip()
                if not question:
                    raise RuntimeError("질문을 입력해 주세요.")
                chunks = rag.search(question)                      # 1) 벡터 검색
                context = "\n\n---\n\n".join(c["text"] for c in chunks)
                prompt = config.PROMPT.format(context=context, question=question)
                answer = llm.ask(prompt)                           # 2) AI 답변 생성
                self._json({"answer": answer, "chunks": chunks})
            elif self.path == "/api/upload":
                self._json({"saved": self._save_upload(body)})
            elif self.path == "/api/sample":
                self._json({"saved": rag.load_samples()})
            elif self.path == "/api/rebuild":
                rag.reset_db()
                self._json(rag.build_db())
            elif self.path == "/api/reset":
                rag.reset_db()
                self._json({"ok": True})
            else:
                self._json({"error": "없는 주소입니다"}, code=404)
        except Exception as e:  # 오류는 화면에 그대로 보여줍니다
            self._json({"error": str(e)}, code=400)

    def _save_upload(self, body):
        """업로드된 파일(.md/.txt)을 data 폴더에 저장 (multipart 직접 해석)"""
        ctype = self.headers.get("Content-Type", "")
        if "boundary=" not in ctype:
            raise RuntimeError("파일이 올바르게 전송되지 않았습니다.")
        boundary = ctype.split("boundary=")[-1].encode()
        saved = []
        for part in body.split(b"--" + boundary):
            if b"filename=" not in part:
                continue
            header, _, content = part.partition(b"\r\n\r\n")
            name = os.path.basename(
                re.search(rb'filename="([^"]*)"', header).group(1).decode("utf-8", "ignore"))
            if not name:
                continue
            if not name.endswith((".md", ".txt")):
                raise RuntimeError(".md 또는 .txt 파일만 올릴 수 있습니다. (PDF는 md로 변환해서 넣어 주세요)")
            if content.endswith(b"\r\n"):
                content = content[:-2]
            os.makedirs(rag.DATA_DIR, exist_ok=True)
            with open(os.path.join(rag.DATA_DIR, name), "wb") as f:
                f.write(content)
            saved.append(name)
        if not saved:
            raise RuntimeError("저장된 파일이 없습니다. 파일을 선택했는지 확인해 주세요.")
        return saved

    def log_message(self, fmt, *args):  # 터미널을 조용하게
        pass


if __name__ == "__main__":
    print("═" * 50)
    print(f"🚀 {config.APP_TITLE}")
    print(f"   브라우저에서 열기 → http://localhost:{config.PORT}")
    print(f"   📁 문서 폴더: data/   🗄️ 벡터디비: vector_db.json")
    if llm.ready():
        print(f"   🤖 사용 중인 AI: {llm.BACKEND}")
    else:
        print("   ⚠️ AI 미연결 — .env 파일에 GEMINI_API_KEY를 넣어 주세요 (.env.example 참고)")
    print("   종료: Ctrl+C")
    print("═" * 50)
    ThreadingHTTPServer(("0.0.0.0", config.PORT), Handler).serve_forever()
