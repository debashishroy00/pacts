@echo off
REM PACTS - Simple test runner for business users (Windows)
REM Usage: pacts test salesforce_create_contact.txt
REM        pacts test salesforce_opportunity_postlogin.txt
REM        pacts test wikipedia_search.txt

REM Convert "test <filename>" to "test --req <filename>"
if "%1"=="test" (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main test --req %2 %3 %4 %5 %6 %7 %8 %9"
) else (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main %*"
)
