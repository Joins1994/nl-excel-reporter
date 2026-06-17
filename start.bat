@echo off
echo ============================================
echo   NL Excel Reporter - 自然语言报表工具
echo ============================================
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/2] Starting server...
echo.
echo   Open: http://localhost:5000
echo.
echo   Optional env vars:
echo     LLM_API_KEY=your-api-key
echo     LLM_API_BASE=https://api.openai.com/v1
echo     LLM_MODEL=gpt-4o-mini
echo.

python app.py
pause
