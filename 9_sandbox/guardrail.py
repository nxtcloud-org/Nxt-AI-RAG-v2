"""가드레일 — AI 앞뒤에 세우는 안전장치.

입력 단계: 질문에 금지 키워드가 있으면 AI를 부르기 전에 거부합니다.
출력 단계: 답변 속 개인정보 패턴(주민번호·전화번호 등)을 가립니다.

설정 우선순위: 화면의 🛡️ 가드레일 탭에서 저장한 guardrail.json이 있으면 그것을,
없으면 config.py의 기본값을 씁니다. [기본값으로 되돌리기] = guardrail.json 삭제.

실무에서 AWS Bedrock Guardrails, LLM 게이트웨이가 하는 일의 축소판입니다.
"""
import json
import os
import re

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "guardrail.json")


def get_settings():
    """현재 가드레일 설정 (guardrail.json 우선, 없으면 config.py 기본값)"""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"blocked_keywords": list(config.BLOCKED_KEYWORDS),
            "block_message": config.BLOCK_MESSAGE,
            "mask_patterns": list(config.MASK_PATTERNS),
            "mask_text": config.MASK_TEXT}


def save_settings(s):
    """가드레일 탭에서 저장 — 검증 후 guardrail.json에 기록"""
    keywords = []
    for w in s.get("blocked_keywords", []):
        w = str(w).strip()
        if w and w not in keywords:
            keywords.append(w)
    patterns = []
    for p in s.get("mask_patterns", []):
        p = str(p).strip()
        if not p:
            continue
        try:
            re.compile(p)
        except re.error:
            raise RuntimeError(f"정규식이 잘못되었어요: {p} — 에이전트에게 패턴 작성을 부탁해 보세요.") from None
        if p not in patterns:
            patterns.append(p)
    data = {"blocked_keywords": keywords,
            "block_message": str(s.get("block_message") or config.BLOCK_MESSAGE).strip(),
            "mask_patterns": patterns,
            "mask_text": str(s.get("mask_text") or config.MASK_TEXT).strip()}
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def reset_settings():
    """기본값으로 되돌리기 = guardrail.json 삭제"""
    if os.path.exists(SETTINGS_PATH):
        os.remove(SETTINGS_PATH)


def check_input(question):
    """질문에 금지 키워드가 있으면 그 키워드를 반환합니다 (없으면 None).

    글자 포함 검사라서 '연봉이', '연봉은'처럼 조사가 붙어도 잡습니다.
    """
    for word in get_settings()["blocked_keywords"]:
        if word and word in question:
            return word
    return None


def mask_output(text):
    """답변 속 개인정보 패턴을 가리고 (가린 결과, 가린 횟수)를 반환합니다."""
    s = get_settings()
    count = 0
    for pattern in s["mask_patterns"]:
        text, n = re.subn(pattern, s["mask_text"], text)
        count += n
    return text, count


def block_message():
    """차단 시 보여줄 메시지"""
    return get_settings()["block_message"]
