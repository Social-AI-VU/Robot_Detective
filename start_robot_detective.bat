@echo off
REM ============================================================================
REM  Robot Detective launcher
REM  1. Asks which episode (0-4), how to run it (robot or laptop only) and which version
REM     (kort = 5 interviews, 3 = 3 interviews + 2 note-keepers, vol = full episode)
REM     and which language model (OpenAI gpt-5.4-mini/nano or gpt-4o-mini, or a local model via Ollama; see local_llm.py)
REM  2. Starts the services that are not running yet (Redis, ElevenLabs TTS, GPT, Dialogflow),
REM     each in its own window that restarts the service if it crashes
REM  3. Sets up the episode in THIS window, then waits for your go-ahead:
REM     press Enter here, touch the NAO's head or chest, or say "start".
REM ============================================================================
SETLOCAL
SET REPO=%~dp0
SET REPO=%REPO:~0,-1%
cd /d "%REPO%"

echo.
echo  ROBOT DETECTIVE
echo  ===============
echo.
choice /c 01234 /n /m "Which episode? [0] Introductie  [1] Achtbaan  [2] Gigagiebels  [3] Intercom  [4] Parkieten : "
SET /A EP=%ERRORLEVEL%-1
echo.
echo  How do you want to run it?
echo    [R] robot, with the NAO's own microphones
echo    [M] robot, with the laptop microphone
echo    [L] laptop only, no robot (laptop speakers and microphone)
echo    [T] laptop only, typing the answers (for testing)
choice /c RMLT /n /m "Choice: "
SET MODE=%ERRORLEVEL%
SET EPISODE_VERSION=kort
IF "%EP%"=="0" GOTO :versiondone
echo.
echo  Which version?
echo    [K] kort: 5 interviews (~65 min)
echo    [3] 3 interviews + 2 notulisten (~50 min); set the names in the episode's runner
echo    [V] volledig: the full episode
choice /c K3V /n /m "Choice: "
IF ERRORLEVEL 3 SET EPISODE_VERSION=vol& GOTO :versiondone
IF ERRORLEVEL 2 SET EPISODE_VERSION=3& GOTO :versiondone
:versiondone
echo.
echo  Which language model for the chats and interviews?
echo    [F] OpenAI gpt-5.4-mini: fast and smart (recommended)
echo    [N] OpenAI gpt-5.4-nano: a little faster, but the smallest model
echo    [O] OpenAI gpt-4o-mini via the GPT service (the previous default)
echo    [L] small local model on this laptop via Ollama (qwen2.5:3b; slower, for testing)
choice /c FNOL /n /m "Choice: "
SET LLM_CHOICE=%ERRORLEVEL%
REM gpt-5.4-mini/nano are called straight from the episode (LLM_BACKEND=openai_direct, see local_llm.py),
REM so they do not need the GPT service. One SET per line: "IF ... SET a& SET b& GOTO" can run the
REM GOTO even when the IF is false.
SET LLM_BACKEND=openai_direct
SET OPENAI_MODEL=gpt-5.4-mini
SET LLM_NAME=gpt-5.4-mini
SET LLM_LOCAL=0
SET NEED_GPT=0
IF "%LLM_CHOICE%"=="2" SET OPENAI_MODEL=gpt-5.4-nano
IF "%LLM_CHOICE%"=="2" SET LLM_NAME=gpt-5.4-nano
IF "%LLM_CHOICE%"=="3" SET LLM_BACKEND=openai
IF "%LLM_CHOICE%"=="3" SET NEED_GPT=1
IF "%LLM_CHOICE%"=="3" SET LLM_NAME=gpt-4o-mini
IF "%LLM_CHOICE%"=="4" SET LLM_BACKEND=local
IF "%LLM_CHOICE%"=="4" SET LLM_LOCAL=1
IF "%LLM_CHOICE%"=="4" SET LLM_NAME=local

IF "%EP%"=="0" SET RUNNER=Episode_0_NAO
IF "%EP%"=="1" SET RUNNER=Episode_1_NAO
IF "%EP%"=="2" SET RUNNER=Episode_2_gigagiebels
IF "%EP%"=="3" SET RUNNER=Episode_3_kapotte_intercom
IF "%EP%"=="4" SET RUNNER=Episode_4_parkietenplaag
SET ARGS=
IF "%MODE%"=="2" (
    IF "%EP%"=="0" (SET RUNNER=Episode_0_NAO_laptop_mic) ELSE IF "%EP%"=="1" (SET RUNNER=Episode_1_NAO_laptop_mic) ELSE (SET RUNNER=%RUNNER%_NAO_laptop_mic)
)
IF "%MODE%"=="3" (SET RUNNER=Episode_laptop& SET ARGS=--episode %EP%)
IF "%MODE%"=="4" (SET RUNNER=Episode_laptop& SET ARGS=--episode %EP% --typing)

REM Participant number, children's names (saved in conf\participant_names.json) and the scene to start from (for testing).
SET "SETUP_FILE=%TEMP%\robot_detective_session.bat"
".venv\Scripts\python.exe" utils\session_setup.py --episode %EP% --version %EPISODE_VERSION% --runner %RUNNER% --out "%SETUP_FILE%"
IF EXIST "%SETUP_FILE%" call "%SETUP_FILE%"

REM Services: start the ones that are not running yet, each in its own window. A service window
REM restarts its service when it stops, and keeps its output in logs\service_<name>.log
REM (see utils\service_runner.py). Leave the windows open between episodes: that saves ~80 s.
SET NEEDED=redis elevenlabs
IF "%LLM_LOCAL%"=="1" echo Local language model ^(LLM_BACKEND=local^): the GPT service is not needed. Make sure Ollama is running.
IF "%NEED_GPT%"=="1" SET NEEDED=%NEEDED% gpt
IF NOT "%MODE%"=="4" SET NEEDED=%NEEDED% dialogflow
echo.
call echo %%date%% %%time%%  launcher: checking services: %NEEDED%>>"%REPO%\logs\startup_times.log"
REM Restart Dialogflow and GPT before every episode: an episode stopped with Ctrl+C can leave its
REM Dialogflow / GPT component behind, which then answers every request of the next episode as well
REM (an empty transcript, or a reply to the wrong question: "sorry, ik verstond je niet").
REM The same goes for ElevenLabs: a leftover component generates every line a second time (paid twice).
SET RESTART=elevenlabs
IF NOT "%MODE%"=="4" SET RESTART=%RESTART% dialogflow
IF "%NEED_GPT%"=="1" SET RESTART=%RESTART% gpt
IF NOT "%RESTART%"=="" ".venv\Scripts\python.exe" utils\service_runner.py --restart %RESTART%
".venv\Scripts\python.exe" utils\service_runner.py --ensure %NEEDED%
call echo %%date%% %%time%%  launcher: services ready>>"%REPO%\logs\startup_times.log"

echo.
echo Starting %RUNNER%.py %ARGS% (version: %EPISODE_VERSION%, language model: %LLM_NAME%, participant: %PARTICIPANT_ID%)
IF "%MODE%"=="3" (echo When it says READY: press Enter here, or say "start".) ELSE IF "%MODE%"=="4" (echo When it says READY: press Enter here.) ELSE (echo Booting the NAO. When its eyes turn blue: press Enter here, touch its head or chest, or say "start".)
echo.
call .venv\Scripts\activate.bat
echo %date% %time%  launcher: starting %RUNNER% version=%EPISODE_VERSION% llm=%LLM_NAME% participant=%PARTICIPANT_ID%>>"%REPO%\logs\startup_times.log"
python "RobotDetectiveEpisodeScripts\%RUNNER%.py" %ARGS%

echo.
echo The episode has ended.
echo Startup timings: logs\startup_times.log
pause
