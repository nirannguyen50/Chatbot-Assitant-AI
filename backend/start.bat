@echo off
echo Starting Chatbot Platform Backend...
cd /d "%~dp0"
call venv\Scripts\activate
python run.py
