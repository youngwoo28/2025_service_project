#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

def main():
    import sys
    import os

    print("manage.py main 진입")
    print(f"sys.argv: {sys.argv}")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ping_project.settings')

    try:
        from django.core.management import execute_from_command_line
        print("Django import 성공")
    except ImportError as exc:
        print("Django import 실패")
        raise ImportError("Django 설치 필요") from exc

    try:
        execute_from_command_line(sys.argv)
        print("execute_from_command_line 성공")
    except Exception as e:
        print(f"execute_from_command_line 예외 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
