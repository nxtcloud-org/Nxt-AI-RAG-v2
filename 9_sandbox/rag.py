"""RAG의 심장 — 세 가지 개념이 전부 여기 있습니다.

1) 파일 저장폴더  data/            : 검색 대상 문서(.md/.txt)를 넣는 곳
2) 청크 분할      split_text()     : 문서를 검색 단위로 잘게 쪼개기
3) 벡터디비       vector_db.json   : 청크 + 벡터를 저장한 파일 하나

벡터디비는 거창한 게 아닙니다. 열어 보면 {"text": 청크, "vector": [숫자들]}
목록이 들어 있는 JSON 파일일 뿐입니다. 초기화 = 이 파일 삭제.
"""
import json
import math
import os

import config
import llm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")        # 📁 파일 저장폴더
DB_PATH = os.path.join(BASE_DIR, "vector_db.json")  # 🗄️ 벡터디비
SAMPLE_DIR = os.path.join(BASE_DIR, "samples")   # 🧪 예시 문서 보관함


def list_files():
    """data 폴더의 문서 목록"""
    os.makedirs(DATA_DIR, exist_ok=True)
    return sorted(f for f in os.listdir(DATA_DIR) if f.endswith((".md", ".txt")))


def load_samples():
    """samples 폴더의 예시 문서를 data 폴더로 복사 — 바로 테스트해볼 수 있게"""
    names = sorted(f for f in os.listdir(SAMPLE_DIR) if f.endswith((".md", ".txt")))
    if not names:
        raise RuntimeError("samples 폴더에 예시 문서가 없습니다.")
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in names:
        with open(os.path.join(SAMPLE_DIR, name), "rb") as src:
            with open(os.path.join(DATA_DIR, name), "wb") as dst:
                dst.write(src.read())
    return names


def split_text(text):
    """문단을 우선 지키면서 CHUNK_SIZE 글자 안팎으로 쪼갭니다."""
    size, overlap = config.CHUNK_SIZE, config.CHUNK_OVERLAP
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        while len(para) > size:  # 한 문단이 너무 길면 강제로 자름
            chunks.append(para[:size])
            para = para[size - overlap:]
        if current and len(current) + len(para) > size:
            chunks.append(current)
            current = current[-overlap:] if overlap else ""  # 끝부분을 겹쳐 문맥 유지
        current = (current + "\n" + para).strip()
    if current:
        chunks.append(current)
    return chunks


def cosine(a, b):
    """두 벡터가 얼마나 같은 방향인지 (1에 가까울수록 의미가 비슷)"""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def build_db():
    """data 폴더의 문서 전부 → 청크 → 벡터 → vector_db.json 저장"""
    files = list_files()
    if not files:
        raise RuntimeError("data 폴더에 .md 또는 .txt 파일이 없습니다. 먼저 문서를 올려 주세요.")
    entries = []
    for name in files:
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
            text = f.read()
        for chunk in split_text(text):
            entries.append({"source": name, "text": chunk, "vector": llm.embed(chunk)})
    db = {"backend": llm.BACKEND, "chunk_size": config.CHUNK_SIZE, "chunks": entries}
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    return {"files": len(files), "chunks": len(entries)}


def reset_db():
    """벡터디비 초기화 = 파일 하나 삭제"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def db_info():
    """화면 상단 상태 표시용 정보"""
    info = {"backend": llm.BACKEND, "ai_ready": llm.ready(), "files": list_files(),
            "db_exists": os.path.exists(DB_PATH), "chunks": 0, "db_backend": None}
    if info["db_exists"]:
        with open(DB_PATH, encoding="utf-8") as f:
            db = json.load(f)
        info["chunks"] = len(db["chunks"])
        info["db_backend"] = db.get("backend")
    return info


def search(question):
    """질문을 벡터로 바꿔, 저장된 모든 청크와 비교해 가장 비슷한 TOP_K개를 찾습니다."""
    if not os.path.exists(DB_PATH):
        raise RuntimeError("벡터디비가 아직 없습니다. [DB 만들기] 버튼을 먼저 눌러 주세요.")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    if db.get("backend") != llm.BACKEND:
        raise RuntimeError(
            f"이 벡터디비는 {db.get('backend')} 임베딩으로 만들어져 지금 환경({llm.BACKEND})과 호환되지 않습니다. "
            "[DB 초기화] 후 [DB 만들기]를 다시 눌러 주세요.")
    qv = llm.embed(question)
    scored = [{"source": c["source"], "text": c["text"], "score": round(cosine(qv, c["vector"]), 3)}
              for c in db["chunks"]]
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[: config.TOP_K]
