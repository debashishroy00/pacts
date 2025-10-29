@echo off
REM ====================================================================
REM PACTS Git Upload Script
REM Commits and pushes all changes to GitHub
REM ====================================================================

echo.
echo ===================================================
echo   PACTS - Git Upload Script
echo ===================================================
echo.

REM Check if we're in a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Not a git repository!
    echo Run 'git init' first.
    pause
    exit /b 1
)

echo [1/5] Checking git status...
git status

echo.
echo [2/5] Adding all changes...
git add .

echo.
echo [3/5] Showing what will be committed...
git status --short

echo.
echo ===================================================
set /p COMMIT_MSG="Enter commit message (or press Enter for default): "

if "%COMMIT_MSG%"=="" (
    REM Generate timestamp-based commit message
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATE=%%a-%%b-%%c
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIME=%%a-%%b
    set COMMIT_MSG=Update: %DATE% %TIME%
)

echo.
echo [4/5] Committing with message: "%COMMIT_MSG%"
git commit -m "%COMMIT_MSG%"

if errorlevel 1 (
    echo.
    echo [WARNING] Commit failed or nothing to commit
    echo.
    pause
    exit /b 0
)

echo.
echo [5/5] Pushing to origin...
git push origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed! Trying 'master' branch...
    git push origin master
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Push failed on both 'main' and 'master'
        echo.
        echo Possible fixes:
        echo   1. Check internet connection
        echo   2. Set remote: git remote add origin https://github.com/yourusername/pacts.git
        echo   3. Check branch name: git branch
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ===================================================
echo   SUCCESS! All changes pushed to GitHub
echo ===================================================
echo.
pause