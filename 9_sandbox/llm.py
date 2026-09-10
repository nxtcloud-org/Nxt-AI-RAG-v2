"""AI 호출 담당.

.env 파일에 GEMINI_API_KEY가 있으면 → Gemini (로컬 실행용, 무료 키)
없으면                              → AWS Bedrock (EC2 실행용)

외부 패키지 없이 표준 라이브러리(urllib)로 Gemini REST API를 호출합니다.
Bedrock은 EC2에 기본 설치된 boto3를 씁니다.
"""
import json
import os
import urllib.request

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_env():
    """같은 폴더의 .env 파일을 읽어 환경변수로 등록합니다 (패키지 불필요)."""
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

# 어떤 AI를 쓸지 자동 결정
BACKEND = "gemini" if os.environ.get("GEMINI_API_KEY") else "bedrock"


# ── Gemini (REST API 직접 호출) ────────────────────────────────
def _gemini_post(model, action, body):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{action}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"Gemini 호출 실패 (HTTP {e.code}): {detail}") from e


def _gemini_ask(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = _gemini_post(config.GEMINI_MODEL, "generateContent", body)
    return resp["candidates"][0]["content"]["parts"][0]["text"]


def _gemini_embed(text):
    body = {
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 768,  # 벡터 길이를 줄여 vector_db.json을 가볍게
    }
    resp = _gemini_post(config.GEMINI_EMBED_MODEL, "embedContent", body)
    return resp["embedding"]["values"]


# ── AWS Bedrock (boto3) ────────────────────────────────────────
_bedrock_client = None


def _bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        try:
            import boto3  # EC2에서만 필요하므로 여기서 불러옵니다
        except ImportError:
            raise RuntimeError(
                "AI에 연결되어 있지 않습니다. 내 컴퓨터에서 실행 중이라면 "
                ".env 파일에 GEMINI_API_KEY를 넣어 주세요. "
                "(.env.example 파일 참고 — 무료 키 발급: https://aistudio.google.com/apikey)") from None
        _bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _bedrock_client


def ready():
    """AI를 호출할 수 있는 상태인지 (화면 배지 표시용)"""
    if BACKEND == "gemini":
        return True
    try:
        import boto3  # noqa: F401
        return True
    except ImportError:
        return False


def _bedrock_ask(prompt):
    resp = _bedrock().converse(
        modelId=config.BEDROCK_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1024},
    )
    return resp["output"]["message"]["content"][0]["text"]


def _bedrock_embed(text):
    resp = _bedrock().invoke_model(
        modelId=config.BEDROCK_EMBED_MODEL,
        body=json.dumps({"inputText": text[:8000]}),
    )
    return json.loads(resp["body"].read())["embedding"]


# ── 공용 함수 (앱에서는 이 둘만 사용) ──────────────────────────
def ask(prompt):
    """질문(프롬프트)을 AI에게 보내 답변 텍스트를 받습니다."""
    return _gemini_ask(prompt) if BACKEND == "gemini" else _bedrock_ask(prompt)


def embed(text):
    """텍스트를 숫자 벡터(의미 좌표)로 바꿉니다."""
    return _gemini_embed(text) if BACKEND == "gemini" else _bedrock_embed(text)
