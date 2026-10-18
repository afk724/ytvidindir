@echo off
chcp 65001 >nul
cd /d "%~dp0"
title YouTube Video Indirici

:: Python launcher (pyw veya pythonw ile siyah konsol penceresi olmadan açılır)
where pyw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pyw app.py
    exit
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    start "" py app.py
    exit
)

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw app.py
    exit
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    start "" python app.py
    exit
)

echo Python bulunamadı! Lütfen Python'un kurulu olduğundan emin olun.
pause
