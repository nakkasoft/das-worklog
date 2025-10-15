#!/bin/bash

echo "===================================="
echo "DAS WorkLog EXE 빌드 스크립트 (Linux/Mac)"
echo "===================================="
echo

echo "[1/5] 빌드 환경 확인 중..."
python3 --version
pip3 show pyinstaller > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "PyInstaller가 설치되지 않았습니다. 설치 중..."
    pip3 install pyinstaller
fi

echo "[2/5] 이전 빌드 파일 정리 중..."
rm -rf dist
rm -rf build
rm -rf __pycache__

echo "[3/5] 필수 파일 존재 확인 중..."
if [ ! -f "worklog.py" ]; then
    echo "오류: worklog.py 파일이 없습니다!"
    exit 1
fi

if [ ! -f "worklog.ui" ]; then
    echo "경고: worklog.ui 파일이 없습니다!"
fi

if [ ! -f "user_config.json" ]; then
    echo "경고: user_config.json 파일이 없습니다!"
fi

echo "[4/5] PyInstaller로 실행 파일 빌드 시작..."
pyinstaller worklog.spec

echo "[5/5] 빌드 결과 확인..."
if [ -f "dist/DAS_WorkLog" ]; then
    echo
    echo "✅ 빌드 성공!"
    echo "📁 실행 파일 위치: dist/DAS_WorkLog"
    echo
    echo "배포 준비:"
    echo "1. dist 폴더의 내용을 대상 컴퓨터에 복사"
    echo "2. user_config.json 파일에 실제 API 키 입력"
    echo "3. ./DAS_WorkLog 실행"
    echo
else
    echo
    echo "❌ 빌드 실패!"
    echo "오류 내용을 확인하고 다시 시도하세요."
    echo
fi

echo "빌드 완료. Enter를 누르면 종료됩니다."
read
