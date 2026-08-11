@echo off
setlocal

echo ============================================================
echo  ChatbotAI development servers are starting up...
echo.
echo   Backend:  http://localhost:8000
echo   API docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo  One terminal window will open for each server.
echo  Close a window (or press Ctrl+C inside it) to stop it.
echo ============================================================
echo.

if exist "%~dp0backend\.venv\Scripts\activate.bat" (
    start "ChatbotAI Backend" cmd /k "cd /d ""%~dp0backend"" & call .venv\Scripts\activate.bat & python -m uvicorn app.main:app --reload --port 8000"
) else (
    start "ChatbotAI Backend" cmd /k "cd /d ""%~dp0backend"" & echo [INFO] Virtual environment not found - running with system Python & python -m uvicorn app.main:app --reload --port 8000"
)

start "ChatbotAI Frontend" cmd /k "cd /d ""%~dp0frontend"" & npm run dev"

echo Servers launched. You can now open:
echo   Backend  -> http://localhost:8000/docs
echo   Frontend -> http://localhost:5173
echo.
pause
