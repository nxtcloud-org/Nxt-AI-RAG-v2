#!/bin/bash
# Admin 서비스 실행 스크립트

echo "1. Python 의존성 설치 중..."
cd server
pip install -r requirements.txt
cd ..

echo "2. 클라이언트 빌드 중 (최초 1회 필수)..."
cd client
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

echo "3. Admin 서비스 시작 (http://localhost:8001)"
cd server
python main.py
