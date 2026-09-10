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
import unicodedata

import config
import extract
import guardrail
import llm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")        # 📁 파일 저장폴더
DB_PATH = os.path.join(BASE_DIR, "vector_db.json")  # 🗄️ 벡터디비
SAMPLE_DIR = os.path.join(BASE_DIR, "samples")   # 🧪 예시 문서 보관함


def nfc(name):
    """한글 파일명 정규화 — 맥에서 압축을 풀면 자모가 분리된 형태(NFD)가 되어
    눈에는 같아 보여도 다른 글자가 됩니다. 항상 완성형(NFC)으로 통일합니다."""
    return unicodedata.normalize("NFC", name)


def _resolve(directory, name):
    """정규화(NFC/NFD)가 달라도 실제 디스크의 파일을 찾아 (표준이름, 경로)를 돌려줍니다."""
    name = nfc(os.path.basename(name))
    path = os.path.join(directory, name)
    if not os.path.exists(path) and os.path.isdir(directory):
        for f in os.listdir(directory):
            if nfc(f) == name:
                return name, os.path.join(directory, f)
    return name, path


def list_files():
    """data 폴더의 문서 목록"""
    os.makedirs(DATA_DIR, exist_ok=True)
    return sorted(nfc(f) for f in os.listdir(DATA_DIR) if f.endswith((".md", ".txt")))


def list_samples():
    """samples 폴더의 예시 문서 목록 (여러 형식 — 부서 유형별 샘플)"""
    if not os.path.isdir(SAMPLE_DIR):
        return []
    return sorted(nfc(f) for f in os.listdir(SAMPLE_DIR)
                  if not f.startswith(".") and "." in f)


def load_samples(name=None):
    """예시 문서를 data 폴더에 추가합니다.

    name을 주면 그 파일 하나만, 없으면 전부.
    xlsx·hwpx 등은 업로드와 똑같이 extract를 거쳐 텍스트(.md)로 변환해 저장합니다.
    """
    names = [nfc(os.path.basename(name))] if name else list_samples()
    if not names:
        raise RuntimeError("samples 폴더에 예시 문서가 없습니다.")
    os.makedirs(DATA_DIR, exist_ok=True)
    saved = []
    for n in names:
        n, path = _resolve(SAMPLE_DIR, n)
        if not os.path.exists(path):
            raise RuntimeError(f"'{n}' 예시 문서를 찾을 수 없습니다.")
        with open(path, "rb") as f:
            data = f.read()
        text = extract.extract(n, data)
        out = n if n.lower().endswith((".md", ".txt")) else n[: n.rfind(".")] + ".md"
        with open(os.path.join(DATA_DIR, out), "w", encoding="utf-8") as f:
            f.write(text)
        saved.append(out)
    return saved


def split_text(text, size=None, overlap=None):
    """문단을 우선 지키면서 size 글자 안팎으로 쪼갭니다. (기본값은 config)"""
    size = size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
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


def build_db(chunk_size=None, chunk_overlap=None):
    """data 폴더의 문서 전부 → 청크 → 벡터 → vector_db.json 저장"""
    files = list_files()
    if not files:
        raise RuntimeError("data 폴더에 .md 또는 .txt 파일이 없습니다. 먼저 문서를 올려 주세요.")
    size = chunk_size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap
    entries = []
    for name in files:
        name, path = _resolve(DATA_DIR, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for chunk in split_text(text, size, overlap):
            entries.append({"source": name, "text": chunk, "vector": llm.embed(chunk)})
    db = {"backend": llm.BACKEND, "chunk_size": size, "chunk_overlap": overlap, "chunks": entries}
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    return {"files": len(files), "chunks": len(entries)}


def get_chunks():
    """벡터디비 속 청크를 (벡터는 빼고) 보여주기용으로 반환"""
    if not os.path.exists(DB_PATH):
        return {"exists": False, "chunks": []}
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    return {"exists": True, "chunk_size": db.get("chunk_size"),
            "chunk_overlap": db.get("chunk_overlap"), "backend": db.get("backend"),
            "chunks": [{"source": c["source"], "text": c["text"]} for c in db["chunks"]]}


def delete_file(name):
    """data 폴더에서 문서를 삭제합니다 (벡터디비 반영은 [DB 만들기]를 다시)"""
    name, path = _resolve(DATA_DIR, name)
    if not name.endswith((".md", ".txt")) or not os.path.exists(path):
        raise RuntimeError(f"'{name}' 문서를 찾을 수 없습니다.")
    os.remove(path)
    return name


def read_file(name):
    """data 폴더 문서의 원문 반환 (경로 탈출 방지를 위해 파일명만 허용)"""
    name, path = _resolve(DATA_DIR, name)
    if not os.path.exists(path) or not name.endswith((".md", ".txt")):
        raise RuntimeError(f"'{name}' 문서를 찾을 수 없습니다.")
    with open(path, encoding="utf-8") as f:
        return {"name": name, "text": f.read()}


def reset_db():
    """벡터디비 초기화 = 파일 하나 삭제 (문서는 그대로 — 청크 설정 실험용)"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def reset_all():
    """전체 비우기 — 문서(data/)와 벡터디비를 모두 삭제해 처음 상태로"""
    reset_db()
    for f in list_files():
        os.remove(os.path.join(DATA_DIR, f))


def db_info():
    """화면 상단 상태 표시용 정보"""
    info = {"backend": llm.BACKEND, "ai_ready": llm.ready(), "files": list_files(),
            "db_exists": os.path.exists(DB_PATH), "chunks": 0, "db_backend": None,
            "cfg_chunk_size": config.CHUNK_SIZE, "cfg_chunk_overlap": config.CHUNK_OVERLAP,
            "db_chunk_size": None, "db_chunk_overlap": None,
            "guard_keywords": len([w for w in guardrail.get_settings()["blocked_keywords"] if w]),
            "guard_patterns": len(guardrail.get_settings()["mask_patterns"])}
    if info["db_exists"]:
        with open(DB_PATH, encoding="utf-8") as f:
            db = json.load(f)
        info["chunks"] = len(db["chunks"])
        info["db_backend"] = db.get("backend")
        info["db_chunk_size"] = db.get("chunk_size")
        info["db_chunk_overlap"] = db.get("chunk_overlap")
        info["db_sources"] = sorted({c["source"] for c in db["chunks"]})
    else:
        info["db_sources"] = []
    return info


def search(question, source=None):
    """질문을 벡터로 바꿔, 저장된 청크와 비교해 가장 비슷한 TOP_K개를 찾습니다.

    source를 주면 그 문서의 청크만 검색합니다 (실무 KB의 메타데이터 필터와 같은 원리).
    """
    if not os.path.exists(DB_PATH):
        raise RuntimeError("벡터디비가 아직 없습니다. [DB 만들기] 버튼을 먼저 눌러 주세요.")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    if db.get("backend") != llm.BACKEND:
        raise RuntimeError(
            f"이 벡터디비는 {db.get('backend')} 임베딩으로 만들어져 지금 환경({llm.BACKEND})과 호환되지 않습니다. "
            "[DB 초기화] 후 [DB 만들기]를 다시 눌러 주세요.")
    chunks = db["chunks"]
    if source:
        source = nfc(source)
        chunks = [c for c in chunks if nfc(c["source"]) == source]
        if not chunks:
            raise RuntimeError(
                f"'{source}'는 아직 벡터디비에 없습니다. ⚡ 실습 탭에서 [DB 만들기]를 다시 눌러 주세요.")
    qv = llm.embed(question)
    scored = [{"source": c["source"], "text": c["text"], "score": round(cosine(qv, c["vector"]), 3)}
              for c in chunks]
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[: config.TOP_K]
