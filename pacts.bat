@echo off
REM PACTS - Simple test runner for business users (Windows)
REM Usage: pacts test contact
REM        pacts test opportunity
REM        pacts test wikipedia

docker compose run --rm pacts-runner bash -c "python -m backend.cli.main %*"
