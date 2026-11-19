@echo off
setlocal
title Push AapliSociety to GitHub
echo ========================================================
echo        Push AapliSociety to a New GitHub Repository
echo ========================================================
echo.

set "PATH=%LOCALAPPDATA%\Programs\GitHubCLI;%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

echo Checking GitHub login status...
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] You are not logged in to GitHub yet.
    echo Opening browser authentication...
    echo.
    gh auth login --hostname github.com -p https -w
    if %errorlevel% neq 0 (
        echo.
        echo Login failed or was cancelled.
        pause
        exit /b 1
    )
)

echo.
echo [✓] Logged in to GitHub!
echo.
set /p REPONAME="Enter repository name (Press Enter for 'aaplisociety'): "
if "%REPONAME%"=="" set "REPONAME=aaplisociety"

set /p VISIBILITY="Make repository public or private? (public/private, default: public): "
if "%VISIBILITY%"=="" set "VISIBILITY=public"

echo.
echo Creating repository '%REPONAME%' on your GitHub and pushing code...
gh repo create "%REPONAME%" --%VISIBILITY% --source=. --remote=origin --push

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] Project pushed successfully to GitHub!
    echo ========================================================
) else (
    echo.
    echo If the repository already exists on GitHub, attempting git push directly...
    git push -u origin main
)

echo.
pause
