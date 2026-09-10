"""가드레일 — AI 앞뒤에 세우는 안전장치.

입력 단계: 질문에 금지 키워드가 있으면 AI를 부르기 전에 거부합니다.
출력 단계: 답변 속 개인정보 패턴(주민번호·전화번호 등)을 가립니다.

실무에서 AWS Bedrock Guardrails, LLM 게이트웨이가 하는 일의 축소판입니다.
금지어와 패턴은 config.py에서 조절하세요.
"""
import re

import config


def check_input(question):
    """질문에 금지 키워드가 있으면 그 키워드를 반환합니다 (없으면 None).

    글자 포함 검사라서 '연봉이', '연봉은'처럼 조사가 붙어도 잡습니다.
    """
    for word in config.BLOCKED_KEYWORDS:
        if word and word in question:
            return word
    return None


def mask_output(text):
    """답변 속 개인정보 패턴을 가리고 (가린 결과, 가린 횟수)를 반환합니다."""
    count = 0
    for pattern in config.MASK_PATTERNS:
        text, n = re.subn(pattern, config.MASK_TEXT, text)
        count += n
    return text, count
