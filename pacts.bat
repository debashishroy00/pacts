@echo off
REM PACTS - Simple test runner for business users (Windows)
REM Usage: pacts test contact
REM        pacts test opportunity
REM        pacts test wikipedia

REM Convert "test <name>" to "test --req <name>"
if "%1"=="test" (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main test --req %2 %3 %4 %5 %6 %7 %8 %9"
) else (
    docker compose run --rm pacts-runner bash -c "python -m backend.cli.main %*"
)
