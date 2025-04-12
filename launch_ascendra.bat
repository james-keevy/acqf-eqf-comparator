@echo off
echo Checking for existing process on port 8501...
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8501') DO (
    echo Killing process ID %%P
    taskkill /PID %%P /F >nul 2>&1
)

cd /d C:\Users\james\ascendra

echo Adding and pushing changes to Git...
git add requirements.txt
git commit -m "Add requirements"
git push

echo Launching Streamlit app...
streamlit run ascendra.py --server.port 8501
pause

