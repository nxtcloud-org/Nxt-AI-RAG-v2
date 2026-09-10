"""서버코드 — 브라우저와 RAG를 연결하는 부분.

브라우저(index.html)가 보내는 요청을 받아서:
  GET  /            → 화면(index.html)을 보여줌
  GET  /guide       → 쉬운 설명서(guide.html)
  GET  /api/status  → 지금 상태(문서 개수, 청크 개수, 사용 중인 AI)
  GET  /api/chunks  → 벡터디비에 저장된 청크 목록 (어떻게 쪼개졌는지 구경)
  GET  /api/file    → data 폴더 문서의 원문 (?name=파일명)
  POST /api/ask     → 질문(+이전 대화) → 벡터 검색 → AI 답변
  POST /api/upload  → 문서 파일을 data 폴더에 저장
  POST /api/sample  → 샘플 문서를 data 폴더로 복사
  POST /api/rebuild → 벡터디비 새로 만들기 (청크 크기·겹침 조절 가능)
  POST /api/reset   → 벡터디비 초기화(삭제)

실행: python app.py  →  브라우저에서 http://localhost:8501
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import config
import guardrail
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
        url = urlparse(self.path)
        try:
            if url.path == "/":
                self._send(render_index(), ctype="text/html; charset=utf-8")
            elif url.path == "/guide":
                with open(os.path.join(BASE_DIR, "guide.html"), encoding="utf-8") as f:
                    self._send(f.read(), ctype="text/html; charset=utf-8")
            elif url.path == "/api/status":
                self._json(rag.db_info())
            elif url.path == "/api/chunks":
                self._json(rag.get_chunks())
            elif url.path == "/api/file":
                name = parse_qs(url.query).get("name", [""])[0]
                self._json(rag.read_file(name))
            else:
                self._json({"error": "없는 주소입니다"}, code=404)
        except Exception as e:
            self._json({"error": str(e)}, code=400)

    # ── 동작(질문·업로드·DB 관리) ──
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            if self.path == "/api/ask":
                data = json.loads(body)
                question = data["question"].strip()
                if not question:
                    raise RuntimeError("질문을 입력해 주세요.")
                # 🛡️ 가드레일 1단계: 금지 키워드면 AI를 부르지 않고 거부
                hit = guardrail.check_input(question)
                if hit:
                    self._json({"answer": config.BLOCK_MESSAGE, "chunks": [],
                                "blocked": hit, "masked": 0})
                    return
                # 이전 대화(최근 4턴)를 프롬프트에 넣어 맥락을 기억하게 합니다
                turns = [f"사용자: {t['q']}\nAI: {t['a'][:400]}"
                         for t in (data.get("history") or [])[-4:]]
                history = "\n\n".join(turns) if turns else "(없음)"
                chunks = rag.search(question)                      # 1) 벡터 검색
                context = "\n\n---\n\n".join(c["text"] for c in chunks)
                try:
                    prompt = config.PROMPT.format(history=history, context=context, question=question)
                except KeyError:  # 프롬프트에서 {history}를 지웠어도 동작하게
                    prompt = config.PROMPT.format(context=context, question=question)
                answer = llm.ask(prompt)                           # 2) AI 답변 생성
                # 🛡️ 가드레일 2단계: 답변 속 개인정보 패턴 가리기
                answer, masked = guardrail.mask_output(answer)
                self._json({"answer": answer, "chunks": chunks,
                            "blocked": None, "masked": masked})
            elif self.path == "/api/upload":
                self._json({"saved": self._save_upload(body)})
            elif self.path == "/api/sample":
                self._json({"saved": rag.load_samples()})
            elif self.path == "/api/rebuild":
                opts = json.loads(body) if body else {}
                rag.reset_db()
                self._json(rag.build_db(opts.get("chunk_size"), opts.get("chunk_overlap")))
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
