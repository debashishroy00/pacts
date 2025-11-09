@echo off
REM PACTS v3.1s Phase 4 Validation Runner (Windows)
REM Executes complete validation matrix and generates report

echo ======================================================================
echo   PACTS v3.1s - Phase 4 Validation Matrix
echo ======================================================================
echo.
echo Starting validation at %date% %time%
echo.

REM Environment check
echo [1/6] Environment sanity check...
if not exist ".env" (
    echo Warning: .env file not found. Using defaults.
)

REM Verify stealth mode is enabled
set PACTS_STEALTH=true
set PACTS_TZ=America/New_York
set PACTS_LOCALE=en-US

echo Environment configured:
echo    PACTS_STEALTH=%PACTS_STEALTH%
echo    PACTS_TZ=%PACTS_TZ%
echo    PACTS_LOCALE=%PACTS_LOCALE%
echo.

REM Create validation output directory
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set VALIDATION_DIR=runs\validation_%TIMESTAMP%
mkdir "%VALIDATION_DIR%" 2>nul
echo Results will be saved to: %VALIDATION_DIR%
echo.

REM Track results
set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0

REM Run validation suites
echo ======================================================================
echo   Running: Static Sites
echo ======================================================================
set /a TOTAL_TESTS+=1
pacts test tests/validation/static_sites.yaml > "%VALIDATION_DIR%\static_sites.log" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PASSED: static_sites
    set /a PASSED_TESTS+=1
) else (
    echo FAILED: static_sites
    set /a FAILED_TESTS+=1
)
echo.

echo ======================================================================
echo   Running: SPA Sites
echo ======================================================================
set /a TOTAL_TESTS+=1
pacts test tests/validation/spa_sites.yaml > "%VALIDATION_DIR%\spa_sites.log" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PASSED: spa_sites
    set /a PASSED_TESTS+=1
) else (
    echo FAILED: spa_sites
    set /a FAILED_TESTS+=1
)
echo.

echo ======================================================================
echo   Running: Auth Flows
echo ======================================================================
set /a TOTAL_TESTS+=1
pacts test tests/validation/auth_flows.yaml > "%VALIDATION_DIR%\auth_flows.log" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PASSED: auth_flows
    set /a PASSED_TESTS+=1
) else (
    echo FAILED: auth_flows
    set /a FAILED_TESTS+=1
)
echo.

echo ======================================================================
echo   Running: Multi-Dataset
echo ======================================================================
set /a TOTAL_TESTS+=1
pacts test tests/validation/multi_dataset.yaml --data tests/validation/users.csv > "%VALIDATION_DIR%\multi_dataset.log" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PASSED: multi_dataset
    set /a PASSED_TESTS+=1
) else (
    echo FAILED: multi_dataset
    set /a FAILED_TESTS+=1
)
echo.

echo ======================================================================
echo   Running: Full Parallel
echo ======================================================================
set /a TOTAL_TESTS+=1
pacts test tests/validation/ --parallel=3 > "%VALIDATION_DIR%\full_parallel.log" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PASSED: full_parallel
    set /a PASSED_TESTS+=1
) else (
    echo FAILED: full_parallel
    set /a FAILED_TESTS+=1
)
echo.

REM Generate summary
echo ======================================================================
echo   VALIDATION SUMMARY
echo ======================================================================
echo.
echo Total Tests: %TOTAL_TESTS%
echo Passed: %PASSED_TESTS%
echo Failed: %FAILED_TESTS%
echo.

REM Create summary file
(
echo PACTS v3.1s Phase 4 Validation Summary
echo =======================================
echo.
echo Date: %date% %time%
echo Environment:
echo   - PACTS_STEALTH: %PACTS_STEALTH%
echo   - PACTS_TZ: %PACTS_TZ%
echo   - PACTS_LOCALE: %PACTS_LOCALE%
echo.
echo Results:
echo   - Total Tests: %TOTAL_TESTS%
echo   - Passed: %PASSED_TESTS%
echo   - Failed: %FAILED_TESTS%
echo.
echo Success Criteria:
echo   - Pass Rate Target: ≥95%%
echo   - Avg Step Duration: ^<2s ^(static^), ^<3s ^(SPA^)
echo   - Retry Rate: ^<5%%
echo   - Blocked Headless: ^<10%%
echo.
echo Logs: %VALIDATION_DIR%\
) > "%VALIDATION_DIR%\summary.txt"

type "%VALIDATION_DIR%\summary.txt"

REM Exit code based on results
if %FAILED_TESTS% EQU 0 (
    echo.
    echo All validation tests passed! v3.1s is production-ready.
    exit /b 0
) else (
    echo.
    echo Validation completed with %FAILED_TESTS% failure^(s^). Review logs.
    exit /b 1
)
