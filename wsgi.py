"""Arquivo WSGI do Sincro (usado pelo PythonAnywhere, gunicorn, etc.).

No PythonAnywhere, o arquivo WSGI da aba Web deve apenas importar este módulo:
    import sys
    sys.path.insert(0, "/home/SEU_USUARIO/sincro")
    from wsgi import application
"""
from app import app as application  # noqa: F401
