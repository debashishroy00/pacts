@echo off
REM PACTS - Simple test runner for business users (Windows)
REM Usage: pacts test salesforce_create_contact.txt
REM        pacts test salesforce_opportunity_postlogin.txt
REM        pacts test wikipedia_search.txt

REM Convert "test <filename>" to "test --req <filename>"
if "%1"=="test" (
    REM Check if this is a Salesforce test (contains salesforce in filename)
    echo %2 | findstr /i "salesforce" >nul
    if %errorlevel%==0 (
        REM Salesforce test - check session validity first
        python scripts\check_sf_session.py
        if %errorlevel% neq 0 (
            echo.
            echo [PACTS] Salesforce session check failed
            echo [PACTS] Run: python scripts\session_capture_sf.py
            echo [PACTS] Then re-run your test
            exit /b 1
        )
    )

    REM Session valid or not Salesforce - proceed with test
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main test --req %2 %3 %4 %5 %6 %7 %8 %9"
) else (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main %*"
)
