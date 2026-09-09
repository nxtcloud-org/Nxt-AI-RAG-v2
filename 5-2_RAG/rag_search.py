import boto3
import streamlit as st
from langchain_aws import ChatBedrock
from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import chromadb

# 사이드바 자동 숨김 설정
st.set_page_config(initial_sidebar_state="collapsed")
st.title("🔍 대학행정 정보 검색 시스템")
st.caption("RAG(Retrieval-Augmented Generation) 기반 문서 검색")


# AWS Bedrock 클라이언트 초기화
@st.cache_resource
def init_bedrock():
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
    bedrock = ChatBedrock(
        client=bedrock_client,
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        model_kwargs={"anthropic_version": "bedrock-2023-05-31"},
    )
    embeddings = BedrockEmbeddings(region_name="us-east-1")
    return bedrock, embeddings


bedrock, embeddings = init_bedrock()


# PDF 로드 및 청크 분할
@st.cache_resource
def load_and_process_pdf():
    chroma_client = chromadb.PersistentClient(path="./vector_db")
    # 파일로드
    pdf_loader = PyMuPDFLoader("./data/univ-admin-manual.pdf")
    # 청크 분할
    # ──────────────────────────────────────────────────────────────
    # 🔬 실습 포인트: 챗봇이 이상하다? 범인은 여기 있다
    #
    # 지금 이 앱은 일부 질문에 "문서에 없습니다"라고 답합니다.
    # 문서에는 분명히 답이 있는데도요. (실측 사례 — Claude Haiku 4.5 기준)
    #
    #   현재 설정 chunk_size=1000 — 여러 주제가 한 청크에 뒤섞임:
    #     Q. 출퇴근 기록 소급 등록은 언제까지 가능한가요?
    #     A. "문서에 해당 내용이 없습니다"  ← ❌ 편람에 분명히 있음
    #     Q. 연가는 며칠까지 쓸 수 있나요?
    #     A. "문서에 연가 내용이 없습니다"  ← ❌
    #
    # 4_chunk_splite에서 같은 문서를 쪼개봤던 것을 떠올려 보세요.
    # 청크가 곧 검색의 단위입니다 — 한 청크에 여러 주제가 섞이면
    # 임베딩이 흐릿해져 질문과 매칭되지 않습니다.
    #
    # 🔧 해결: ① 앱 종료(Ctrl+C) → ② vector_db 폴더 삭제 → ③ 아래 값을 500/50으로 → ④ 재실행
    #    (순서 주의: 앱을 켜둔 채 폴더를 지우면 readonly 에러,
    #     폴더를 안 지우면 옛 청크가 남아 중복 누적 — 고쳐도 안 고쳐진 것처럼 보임)
    #     Q. 출퇴근 기록 소급 등록은 언제까지 가능한가요?
    #     A. "익일 정오까지 사유 기재 후 소급 등록…"  ← ✅
    #
    # 청크 크기와 별개로, 질문의 구체성도 검색을 좌우합니다:
    #     Q. 연가는 며칠까지 쓸 수 있나요?     → "문서에 없습니다"  ← ❌ 뭉툭한 질문
    #     Q. 재직 3년이면 연가가 며칠인가요?   → "17일입니다"      ← ✅ 구체적 질문
    # (임베딩이 질문과 청크를 의미로 매칭하기 때문 — 문서 표준화와 질문 구체화가 함께 필요)
    # ──────────────────────────────────────────────────────────────
    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator="\n",
        chunk_size=1000,  # 🔧 500으로 바꿔보세요
        chunk_overlap=100,  # 🔧 50으로 바꿔보세요
    )
    data = pdf_loader.load_and_split(text_splitter=splitter)
    # 벡터 스토어 구성
    vectorstore = Chroma.from_documents(
        documents=data,
        embedding=embeddings,
        persist_directory="./vector_db/",
        collection_name="university_docs",
    )
    return vectorstore


# 메인 검색 인터페이스
try:
    vectorstore = load_and_process_pdf()
    st.success("문서가 성공적으로 로드되었습니다.")
    st.header("📚 대학행정 정보 검색")

    search_query = st.text_input(
        "궁금한 내용을 자연어로 입력하세요:",
        placeholder="예: 경조사 휴가는 며칠인가요?",
        key="search_query",
    )

    if search_query:  # 검색어가 입력된 경우에만 검색 실행
        results = vectorstore.similarity_search(search_query, k=3)

        # 중복 제거
        seen_contents = set()
        unique_results = []
        for doc in results:
            content = doc.page_content.strip()
            if content not in seen_contents:
                seen_contents.add(content)
                unique_results.append(doc)

        st.write(f"🎯 검색 결과: {len(unique_results)}개 관련 문서 발견")
        for i, doc in enumerate(unique_results, 1):
            with st.expander(f"검색 결과 #{i}"):
                st.markdown(f"**내용:**\n{doc.page_content}")
                st.caption(f"출처: {doc.metadata.get('page', 'N/A')}페이지")

        # AI 답변 생성
        st.write("---")
        st.subheader("🤖 AI 응답")

        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            # 검색 결과를 하나의 컨텍스트로 결합
            context = "\n".join([doc.page_content for doc in unique_results])

            # 프롬프트 구성
            prompt = f"""다음은 대학행정 업무에 대한 질문과 관련 문서 내용입니다:

    질문: {search_query}

    관련 문서 내용:
    {context}

    위 내용을 바탕으로 질문에 대해 명확하고 친절하게 답변해주세요.
    문서에 없는 내용은 언급하지 말고, 확실한 정보만 답변에 포함해주세요.
    """

            # AI 응답 생성 및 표시
            response = bedrock.invoke(prompt)

            # 응답 내용과 메타데이터 분리하여 표시
            st.markdown("**답변 내용:**")
            st.markdown(response.content)

            # 메타데이터를 접을 수 있는 expander로 표시
            with st.expander("📊 응답 메타데이터"):
                st.json(
                    {
                        "토큰 사용량": response.additional_kwargs["usage"],
                        "모델": response.additional_kwargs["model_id"],
                        "응답 ID": response.id,
                    }
                )

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.error("데이터베이스 초기화에 실패했습니다. 'vector_db' 디렉토리를 확인해주세요.")
