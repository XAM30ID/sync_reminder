chcp 65001
@echo on
cd "C:\Users\Khamz\Программирование\Проекты\Работа\J_GET\projects\📌В процессе\AI_reminder\sync_reminder\"
call .venv\Scripts\activate.bat
python manage.py minute_task
deactivate
pause