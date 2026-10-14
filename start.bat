@echo off
rem JARVIS no Windows. Rode com duplo clique ou no Prompt de Comando (nao dentro do Claude Code).
cd /d "%~dp0"
set "CLAUDECODE="
set "CLAUDE_CODE_SESSION_ID="
set "CLAUDE_CODE_ENTRYPOINT="
set "ANTHROPIC_AUTH_TOKEN="
set "ANTHROPIC_API_KEY="
where python >nul 2>&1
if not errorlevel 1 (
  python server.py
  goto :fim
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 server.py
  goto :fim
)
echo Python 3 nao foi encontrado. Instale em python.org e marque "Add python.exe to PATH".
:fim
pause
