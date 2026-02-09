@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   AI Financial CRM
echo ========================================
echo   폴더: %~dp0
echo   브라우저: http://localhost:8501
echo ========================================
echo.

echo [ERD API] 테이블 스키마 API 시작 - 포트 8765
start "ERD API" cmd /k "cd /d "%~dp0" && python serve_erd_api.py"
timeout /t 2 /nobreak >nul
echo.

if not exist "erd-viewer\package.json" goto run_crm

if not exist "erd-viewer\node_modules" (
    echo [ERD] npm install 자동 실행 중...
    cd /d "%~dp0erd-viewer"
    call npm install
    cd /d "%~dp0"
    echo [ERD] npm install 완료.
    echo.
)

echo [ERD] 뷰어 시작 - 포트 5173
start "ERD Viewer" cmd /k "cd /d "%~dp0erd-viewer" && npm run dev"
timeout /t 4 /nobreak >nul
echo.

:run_crm
echo [CRM] Streamlit 시작 - 포트 8501
python -m streamlit run app.py --server.headless true

if errorlevel 1 (
    echo.
    echo [오류] Python 실행 실패. python.org 에서 설치 후 PATH 추가 확인.
)

echo.
pause
