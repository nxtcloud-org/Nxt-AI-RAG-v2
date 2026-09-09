import streamlit as st
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter

st.set_page_config(page_title="RAG 문서 분석기", page_icon="📄", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.header("스플리터 설정")
    chunk_size = st.slider("청크 사이즈", 100, 1000, 500, 50)
    chunk_overlap = st.slider("오버랩 크기", 0, 200, 100, 10)
    separator = st.text_input("구분자", value="\n")

# 메인 로직
try:
    # 스플리터 초기화
    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator=separator,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        disallowed_special=(),
    )

    # PDF 로딩 및 분할
    # 5-2_RAG와 같은 문서로 미리 쪼개보기 — 여기서 본 청크가 곧 검색의 단위가 된다
    pdf_loader = PyPDFLoader("./data/univ-admin-manual.pdf")
    pdf = pdf_loader.load()
    data = pdf_loader.load_and_split(text_splitter=splitter)

    # 메트릭 섹션
    st.subheader("스플리터 설정", divider="rainbow")
    metrics = st.columns(3)
    metrics[0].metric("청크 사이즈", chunk_size, "토큰", border=True)
    metrics[1].metric("오버랩 범위", chunk_overlap, "토큰", border=True)
    metrics[2].metric("나눠진 데이터 수", len(data), "청크", border=True)

    # 데이터 프리뷰 섹션
    st.subheader("데이터 프리뷰", divider="rainbow")
    preview_cols = st.columns(2)

    for i, col in enumerate(preview_cols):
        if i < len(data):
            with col:
                st.subheader(f"청크 #{i+1}", divider="rainbow")
                st.text_area(
                    "내용", value=data[i].page_content, height=300, disabled=True
                )
                st.json(data[i].metadata)

    # 데이터 분석 섹션
    st.subheader("데이터 분석", divider="rainbow")
    analysis_cols = st.columns(2)

    # 청크 길이 분포
    with analysis_cols[0]:
        chunk_lengths = [len(chunk.page_content) for chunk in data]
        st.write("청크 길이 통계")
        st.write(
            {
                "최소 길이": min(chunk_lengths),
                "최대 길이": max(chunk_lengths),
                "평균 길이": sum(chunk_lengths) / len(chunk_lengths),
            }
        )

    # 페이지별 청크 수
    with analysis_cols[1]:
        page_chunks = {}
        for chunk in data:
            page = chunk.metadata.get("page", 0)
            page_chunks[page] = page_chunks.get(page, 0) + 1
        st.write("페이지별 청크 수")
        st.write(page_chunks)

    # 전체 데이터 테이블 (접을 수 있는 섹션)
    with st.expander("전체 데이터 보기"):
        df = pd.DataFrame(
            [
                {
                    "청크 번호": i + 1,
                    "페이지": chunk.metadata.get("page", 0),
                    "내용": chunk.page_content,
                    "길이": len(chunk.page_content),
                }
                for i, chunk in enumerate(data)
            ]
        )
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.stop()

# 푸터
st.markdown("---")
st.caption("RAG 문서 분석기 v1.0")
