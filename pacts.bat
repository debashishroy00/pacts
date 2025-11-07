@echo off
setlocal enabledelayedexpansion
REM PACTS - Simple test runner for business users (Windows)
REM Usage: pacts test salesforce_create_contact.txt
REM        pacts test salesforce_opportunity_postlogin.txt
REM        pacts test wikipedia_search.txt

REM Convert "test <filename>" to "test --req <filename>"
if "%1"=="test" (
    REM Check if this is a Salesforce test using Python (more reliable than findstr)
    python -c "import sys; sys.exit(0 if 'salesforce' in '%2'.lower() else 1)" >nul 2>&1
    if !errorlevel!==0 (
        echo [DEBUG] Salesforce test detected: %2
        REM Salesforce test - check session validity first
        python scripts\check_sf_session.py
        if !errorlevel! neq 0 (
            echo.
            echo [PACTS] Salesforce session expired - refreshing automatically...
            echo.
            REM Auto-refresh session
            python scripts\session_capture_sf.py
            if !errorlevel! neq 0 (
                echo.
                echo [PACTS] Session refresh failed or cancelled
                exit /b 1
            )
            echo.
            echo [PACTS] Session refreshed successfully! Continuing with test...
            echo.
        )
    )

    REM Session valid or refreshed - proceed with test
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main test --req %2 %3 %4 %5 %6 %7 %8 %9"
) else (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main %*"
)
