"""문서 변환기 — 업로드된 파일에서 텍스트를 뽑아냅니다.

비밀 하나: hwpx·pptx·docx는 사실 ZIP 압축 속에 XML(글자 기록)이 든 파일입니다.
그래서 표준 라이브러리(zipfile + 정규식)만으로 텍스트를 꺼낼 수 있어요.
실무의 AWS Textract, Unstructured, LangChain Document Loader가 하는 일의 축소판입니다.

표·도형 속 글자는 순서가 조금 섞일 수 있습니다 — 그게 바로 '전처리'가 필요한 이유예요.
"""
import csv
import html
import io
import re
import zipfile

# 업로드를 받는 형식 (이 목록에 없으면 안내 메시지와 함께 거절)
SUPPORTED = (".md", ".txt", ".csv", ".hwpx", ".pptx", ".docx")

# 읽을 수 없는 형식 → 어떻게 하면 되는지 알려주는 안내
GUIDE = {
    ".hwp": "구버전 hwp는 읽을 수 없어요. 한글에서 [다른 이름으로 저장 → hwpx]로 저장해 올려 주세요.",
    ".ppt": "구버전 ppt는 읽을 수 없어요. 파워포인트에서 pptx로 다시 저장해 올려 주세요.",
    ".doc": "구버전 doc는 읽을 수 없어요. 워드에서 docx로 다시 저장해 올려 주세요.",
    ".pdf": "PDF는 읽을 수 없어요. 내용을 복사해 메모장(.txt)에 붙여넣거나, 에이전트에게 변환을 부탁해 보세요.",
}


def _decode(data):
    """텍스트 파일 인코딩 처리 — 엑셀에서 저장한 CSV는 cp949인 경우가 많습니다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _from_csv(data):
    """표의 각 행을 '컬럼명: 값' 문장으로 펴서 검색이 잘 되게 합니다."""
    rows = list(csv.reader(io.StringIO(_decode(data))))
    rows = [r for r in rows if any(v.strip() for v in r)]
    if not rows:
        return ""
    header = [h.strip() for h in rows[0]]
    lines = [" | ".join(header)]
    for row in rows[1:]:
        pairs = [f"{h}: {v.strip()}" for h, v in zip(header, row) if v.strip()]
        if pairs:
            lines.append(", ".join(pairs))
    return "\n\n".join(lines)


def _xml_paragraphs(xml, para_tag, text_pattern):
    """XML을 문단 단위로 끊어 글자만 모읍니다 (hwpx·pptx·docx 공통 요령)."""
    paras = []
    for part in re.split(rf"<{para_tag}[ >/]", xml):
        runs = re.findall(text_pattern, part)
        line = html.unescape("".join(runs)).strip()
        if line:
            paras.append(line)
    return paras


def _from_hwpx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        sections = sorted(n for n in z.namelist()
                          if n.startswith("Contents/section") and n.endswith(".xml"))
        if not sections:
            raise RuntimeError("hwpx 안에서 본문을 찾지 못했어요. (암호화·배포용 문서일 수 있습니다)")
        paras = []
        for n in sections:
            xml = z.read(n).decode("utf-8", "ignore")
            paras += _xml_paragraphs(xml, "hp:p", r"<hp:t[^>]*>([^<]*)</hp:t>")
    return "\n\n".join(paras)


def _from_pptx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        slides = sorted((n for n in z.namelist()
                         if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                        key=lambda n: int(re.search(r"\d+", n).group()))
        parts = []
        for i, n in enumerate(slides, 1):
            xml = z.read(n).decode("utf-8", "ignore")
            paras = _xml_paragraphs(xml, "a:p", r"<a:t[^>]*>([^<]*)</a:t>")
            if paras:
                parts.append(f"[슬라이드 {i}]\n" + "\n".join(paras))
    return "\n\n".join(parts)


def _from_docx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    return "\n\n".join(_xml_paragraphs(xml, "w:p", r"<w:t[^>]*>([^<]*)</w:t>"))


def extract(name, data):
    """파일 이름과 내용(bytes)을 받아 텍스트를 돌려줍니다. 못 읽으면 안내와 함께 거절."""
    lower = name.lower()
    ext = lower[lower.rfind("."):] if "." in lower else ""
    if ext in GUIDE:
        raise RuntimeError(f"'{name}' — {GUIDE[ext]}")
    if ext not in SUPPORTED:
        raise RuntimeError(
            f"'{name}'은 지원하지 않는 형식이에요. 가능한 형식: {', '.join(SUPPORTED)}")
    try:
        if ext in (".md", ".txt"):
            text = _decode(data)
        elif ext == ".csv":
            text = _from_csv(data)
        elif ext == ".hwpx":
            text = _from_hwpx(data)
        elif ext == ".pptx":
            text = _from_pptx(data)
        else:
            text = _from_docx(data)
    except zipfile.BadZipFile:
        raise RuntimeError(f"'{name}' 파일이 손상되었거나 다른 형식인 것 같아요.") from None
    if not text.strip():
        raise RuntimeError(f"'{name}'에서 텍스트를 찾지 못했어요. (이미지만 있는 문서일 수 있습니다)")
    return text
