"""Conexão com o banco de dados SQLite.

SQLite guarda tudo em um único arquivo (sincro.db). Para um projeto deste porte é perfeito:
não precisa instalar nada e é um banco relacional de verdade (SQL).
"""
import os
import sqlite3
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def caminho_db():
    caminho = os.getenv("DB_PATH", "sincro.db")
    if not os.path.isabs(caminho):
        caminho = os.path.join(BASE_DIR, caminho)
    return caminho


def get_db():
    """Abre uma conexão por requisição e reaproveita dentro dela."""
    if "db" not in g:
        g.db = sqlite3.connect(caminho_db())
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def fechar_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def criar_tabelas():
    """Executa o schema.sql (só cria o que ainda não existe)."""
    conexao = sqlite3.connect(caminho_db())
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conexao.executescript(f.read())
    try:  # migração: bancos criados antes da coluna token_versao
        conexao.execute("ALTER TABLE usuarios ADD COLUMN token_versao INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:  # migração: código de recuperação de senha
        conexao.execute("ALTER TABLE usuarios ADD COLUMN codigo_recuperacao_hash TEXT")
    except sqlite3.OperationalError:
        pass
    conexao.commit()
    conexao.close()
