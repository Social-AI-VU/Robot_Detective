@echo off
REM Run supporting services in separate terminals, then start Episode_0_NAO.py
SET REPO=C:\Users\viq021\repositories\Robot_Detective

REM Redis
start "Redis" cmd /k "cd /d %REPO% && call .venv\Scripts\activate.bat && run-redis --data-dir RAG_Vectors"

REM ElevenLabs TTS service
start "ElevenLabs TTS" cmd /k "cd /d %REPO% && call .venv\Scripts\activate.bat && run-elevenlabs-tts"

REM GPT service
start "GPT" cmd /k "cd /d %REPO% && call .venv\Scripts\activate.bat && run-gpt"

REM Dialogflow (local runner)
start "Dialogflow" cmd /k "cd /d %REPO% && call .venv\Scripts\activate.bat && run-dialogflow"

REM Give services a few seconds to start (adjust if needed)
timeout /t 5 /nobreak >nul

REM Start Episode 0 (NAO)
start "Episode 0 NAO" cmd /k "cd /d %REPO% && call .venv\Scripts\activate.bat && python RobotDetectiveEpisodeScripts\Episode_0_NAO.py"

echo Launched services and Episode_0_NAO. Check the opened windows for logs.
pause