@echo off

REM Delete the existing weights.yaml files and create new empty ones
for /d %%i in (./Data/*) do (
    if "%%~nxi"=="Data" (
        del "%%i\weights.yaml" && type nul > "%%i\weights.yaml"
    )
)
REM Add the files to the Git repository
git add ./Data/*/weights.yaml
REM Mark the files as unchanged
git update-index --assume-unchanged ./Data/*/weights.yaml
