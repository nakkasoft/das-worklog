@echo off
echo ====================================
echo DAS WorkLog EXE 빌드 스크립트
echo ====================================
echo.

echo [1/5] 빌드 환경 확인 중...
python --version
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller가 설치되지 않았습니다. 설치 중...
    pip install pyinstaller
)

echo [2/5] 이전 빌드 파일 정리 중...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo [3/5] 필수 파일 존재 확인 중...
if not exist "worklog.py" (
    echo 오류: worklog.py 파일이 없습니다!
    pause
    exit /b 1
)

if not exist "worklog.ui" (
    echo 경고: worklog.ui 파일이 없습니다!
)

if not exist "user_config.json" (
    echo 경고: user_config.json 파일이 없습니다!
)

echo [4/5] PyInstaller로 EXE 빌드 시작...
pyinstaller worklog.spec

echo [5/5] 빌드 결과 확인 및 추가 파일 복사...
if exist "dist\DAS_WorkLog.exe" (
    echo ✅ PyInstaller 빌드 성공!
    
    echo [5.1] 추가 파일 복사 중...
    
    REM templates 폴더 복사
    if exist "templates" (
        xcopy "templates" "dist\templates\" /E /I /Y >nul
        echo   ✓ templates 폴더 복사 완료
    )
    
    REM outlook 빈 폴더 생성
    if not exist "dist\outlook" (
        mkdir "dist\outlook" >nul
        echo   ✓ outlook 빈 폴더 생성 완료
    )
    
    REM user_config_template.json 복사 (사용자가 참고할 수 있도록)
    if exist "user_config_template.json" (
        copy "user_config_template.json" "dist\user_config.json" >nul
        echo   ✓ user_config.json 생성 완료 (template에서 복사)
    )
    
    REM USER_GUIDE.md 복사
    if exist "USER_GUIDE.md" (
        copy "USER_GUIDE.md" "dist\" >nul
        echo   ✓ USER_GUIDE.md 복사 완료
    )
    
    echo.
    echo 🎉 빌드 완료!
    echo 📁 실행 파일 위치: dist\DAS_WorkLog.exe
    echo.
    echo 배포 준비:
    echo 1. dist 폴더의 내용을 대상 컴퓨터에 복사
    echo 2. user_config.json 파일에 실제 API 키 입력
    echo 3. DAS_WorkLog.exe 실행
    echo.
) else (
    echo.
    echo ❌ 빌드 실패!
    echo 오류 내용을 확인하고 다시 시도하세요.
    echo.
)

echo 빌드 완료. 아무 키나 누르면 종료됩니다.
pause >nul
