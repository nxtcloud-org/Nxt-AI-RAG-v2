import boto3
import streamlit as st
from langchain_aws import ChatBedrock
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryMemory
from langchain.prompts import PromptTemplate

# AWS Bedrock 클라이언트 초기화
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

# LangChain BedrockChat 초기화
bedrock = ChatBedrock(
    client=bedrock_client,
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    model_kwargs={"anthropic_version": "bedrock-2023-05-31"},
)

# Streamlit 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    # 한글 요약을 강제하는 프롬프트
    summary_prompt = PromptTemplate(
        input_variables=["summary", "new_lines"],
        template="AI와 사용자의 대화를 반드시 한글로 간략하게 요약해서 메모리를 유지해라 \n 기존 내용 : {summary} \n 새로운 내용 : {new_lines}",
    )
    # ConversationSummaryMemory에 한글 요약 프롬프트 적용
    st.session_state.memory = ConversationSummaryMemory(
        llm=bedrock,
        memory_key="history",
        return_messages=True,
        max_token_limit=1000,
        prompt=summary_prompt,
    )

# ConversationChain 초기화
conversation = ConversationChain(
    llm=bedrock, memory=st.session_state.memory, verbose=True
)

# Streamlit UI 설정
st.title("Chatbot Ver.2.4 : 한글 대화 요약 메모리 챗봇")
st.caption("이전 대화 내용을 **한글로 요약**하여 저장하는 방식으로 토큰을 절약합니다.")

# 대화 히스토리 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ✅ 현재 대화 요약 (한글 적용)
with st.sidebar:
    st.header("💭 현재 대화 요약")
    current_summary = conversation.memory.load_memory_variables({})
    if current_summary["history"]:
        st.info(current_summary["history"])  # 🔹 자동으로 한글 요약됨
    else:
        st.info("아직 대화가 시작되지 않았습니다.")

    st.divider()
    st.caption("대화가 진행될수록 AI가 자동으로 이전 대화를 요약합니다.")

# 사용자 입력 처리
if prompt := st.chat_input("Message Bedrock..."):
    # 사용자 입력 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # LangChain 대화 실행
    with st.chat_message("assistant"):
        with st.spinner("AI가 답변을 고민 중입니다..."):
            response = conversation.run(input=prompt)
            st.markdown(response)

    # 모델 응답 저장
    st.session_state.messages.append({"role": "assistant", "content": response})

# 디버그 정보 (개발 참고용)
with st.expander("🔍 디버그 정보", expanded=False):
    st.subheader("메모리 변수")
    st.json(conversation.memory.load_memory_variables({}))

    st.subheader("전체 메시지 기록")
    st.json(st.session_state.messages)
