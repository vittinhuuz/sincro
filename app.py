"""API do Sincro (Flask).

Rodar local:  python app.py   -> http://127.0.0.1:5000
"""
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import Flask, jsonify, request, g, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import database
import routine_rules as regras
from ai_service import IAIndisponivel, diagnosticar, gerar_com_ia

app = Flask(__name__, static_folder="static", static_url_path="")
def _chave_secreta():
    """Usa SECRET_KEY do .env; se não houver, cria uma aleatória e guarda em .secret_key."""
    k = os.getenv("SECRET_KEY", "").strip()
    if k and not k.startswith("troque"):
        return k
    arq = os.path.join(database.BASE_DIR, ".secret_key")
    if os.path.exists(arq):
        return open(arq, encoding="utf-8").read().strip()
    k = secrets.token_hex(32)
    with open(arq, "w", encoding="utf-8") as f:
        f.write(k)
    return k


app.config["SECRET_KEY"] = _chave_secreta()
app.teardown_appcontext(database.fechar_db)
database.criar_tabelas()

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REGEX_NOME = re.compile(r"^[A-Za-zÀ-ÿ' \-]{2,50}$")
LIMITE_IA_HORA = int(os.getenv("IA_LIMITE_HORA", "10"))
LIMITE_TENTATIVAS, JANELA_SEG = 5, 300  # 5 erros de senha => bloqueio de 5 minutos
HASH_FALSO = generate_password_hash("senha-falsa-para-manter-o-tempo-igual")


@app.after_request
def cabecalhos_seguranca(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------- utilidades ----------------
def erro(mensagem, codigo=400):
    return jsonify({"erro": mensagem}), codigo


def gerar_token(usuario_id, versao=0):
    payload = {"sub": str(usuario_id), "v": versao, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def login_obrigatorio(funcao):
    """Decorator: exige o cabeçalho  Authorization: Bearer <token>."""
    @wraps(funcao)
    def interna(*args, **kwargs):
        cabecalho = request.headers.get("Authorization", "")
        if not cabecalho.startswith("Bearer "):
            return erro("Faça login para continuar.", 401)
        try:
            dados = jwt.decode(cabecalho[7:], app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.PyJWTError:
            return erro("Sessão inválida ou expirada. Entre novamente.", 401)
        usuario = database.get_db().execute(
            "SELECT id, nome, sobrenome, idade, email, token_versao FROM usuarios WHERE id = ?", (dados["sub"],)
        ).fetchone()
        if usuario is None or usuario["token_versao"] != dados.get("v", 0):
            return erro("Usuário não encontrado.", 401)
        g.usuario = {k: usuario[k] for k in ("id", "nome", "sobrenome", "idade", "email")}
        g.token_versao = usuario["token_versao"]
        return funcao(*args, **kwargs)
    return interna


def validar_itens(itens):
    """Valida a lista de atividades vinda do front. Devolve (itens_limpos, mensagem_erro)."""
    if not isinstance(itens, list) or not itens:
        return None, "Envie ao menos uma atividade em 'itens'."
    if len(itens) > 60:
        return None, "Máximo de 60 atividades por rotina."
    limpos = []
    for n, it in enumerate(itens, start=1):
        atividade = str(it.get("atividade", "")).lower().strip()
        if atividade not in regras.ATIVIDADES:
            return None, f"Item {n}: atividade inválida. Use: {', '.join(regras.ATIVIDADES)}."
        if not (regras.hora_valida(it.get("inicio")) and regras.hora_valida(it.get("fim"))):
            return None, f"Item {n}: use horários no formato HH:MM (ex.: 07:30)."
        limpos.append({"atividade": atividade, "inicio": it["inicio"], "fim": it["fim"],
                       "descricao": str(it.get("descricao", "")).strip()[:200]})
    return limpos, None


def salvar_rotina(usuario_id, titulo, origem, resumo, itens):
    db = database.get_db()
    cur = db.execute(
        "INSERT INTO rotinas (usuario_id, titulo, origem, resumo) VALUES (?, ?, ?, ?)",
        (usuario_id, titulo, origem, resumo),
    )
    rotina_id = cur.lastrowid
    db.executemany(
        "INSERT INTO itens_rotina (rotina_id, atividade, inicio, fim, descricao) VALUES (?, ?, ?, ?, ?)",
        [(rotina_id, i["atividade"], i["inicio"], i["fim"], i["descricao"]) for i in itens],
    )
    db.commit()
    return rotina_id


def rotina_completa(rotina_id, usuario_id):
    db = database.get_db()
    r = db.execute("SELECT * FROM rotinas WHERE id = ? AND usuario_id = ?", (rotina_id, usuario_id)).fetchone()
    if r is None:
        return None
    itens = db.execute(
        "SELECT id, atividade, inicio, fim, descricao FROM itens_rotina WHERE rotina_id = ?", (rotina_id,)
    ).fetchall()
    itens = sorted((dict(i) for i in itens), key=lambda i: regras.para_min(i["inicio"]))
    resposta = dict(r)
    resposta["itens"] = itens
    resposta["avisos"] = regras.analisar(itens, g.usuario["idade"])
    return resposta


# ---------------- autenticação ----------------
def senha_invalida(senha):
    """Devolve a mensagem de erro da regra de senha, ou None se estiver ok."""
    if len(senha) < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    if len(senha) > 128:
        return "A senha pode ter no máximo 128 caracteres."
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        return "A senha deve conter letras e números."
    return None


def novo_codigo():
    """Código de recuperação no formato XXXX-XXXX-XXXX (sem letras parecidas, como 0/O e 1/I)."""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "-".join("".join(secrets.choice(alfabeto) for _ in range(4)) for _ in range(3))


def _normalizar_codigo(txt):
    return re.sub(r"[^A-Z0-9]", "", str(txt).upper())


def _guardar_codigo(db, usuario_id):
    codigo = novo_codigo()
    db.execute("UPDATE usuarios SET codigo_recuperacao_hash = ? WHERE id = ?",
               (generate_password_hash(_normalizar_codigo(codigo)), usuario_id))
    return codigo


def _usuario_json(u):
    return {"id": u["id"], "nome": u["nome"], "sobrenome": u["sobrenome"], "idade": u["idade"], "email": u["email"]}


@app.post("/api/auth/cadastro")
def cadastro():
    d = request.get_json(silent=True) or {}
    nome = " ".join(str(d.get("nome", "")).split())
    sobrenome = " ".join(str(d.get("sobrenome", "")).split())
    email = str(d.get("email", "")).strip().lower()
    senha = str(d.get("senha", ""))
    bruto = d.get("idade")
    if isinstance(bruto, bool) or not (isinstance(bruto, int) or (isinstance(bruto, str) and bruto.strip().isdigit())):
        return erro("Informe uma idade válida (número inteiro).")
    idade = int(bruto)

    if not REGEX_NOME.match(nome) or not REGEX_NOME.match(sobrenome):
        return erro("Informe nome e sobrenome válidos (apenas letras, de 2 a 50 caracteres).")
    if not 10 <= idade <= 120:
        return erro("A idade deve estar entre 10 e 120 anos.")
    if not REGEX_EMAIL.match(email) or len(email) > 120:
        return erro("E-mail inválido.")
    if senha_invalida(senha):
        return erro(senha_invalida(senha))
    if str(d.get("confirmar_senha", senha)) != senha:
        return erro("As senhas não coincidem.")

    db = database.get_db()
    try:
        cur = db.execute(
            "INSERT INTO usuarios (nome, sobrenome, idade, email, senha_hash) VALUES (?, ?, ?, ?, ?)",
            (nome.title(), sobrenome.title(), idade, email, generate_password_hash(senha)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return erro("Este e-mail já está cadastrado. Tente entrar.", 409)
    codigo = _guardar_codigo(db, cur.lastrowid)
    db.commit()
    u = db.execute("SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"mensagem": "Cadastro realizado!", "token": gerar_token(u["id"], u["token_versao"]),
                    "usuario": _usuario_json(u), "codigo_recuperacao": codigo}), 201


@app.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()
    senha = str(d.get("senha", ""))
    db = database.get_db()
    agora = int(time.time())
    chave = f"{email}|{request.remote_addr}"

    db.execute("DELETE FROM tentativas_login WHERE quando < ? AND chave NOT LIKE 'ia|%'", (agora - JANELA_SEG,))
    n, primeira = db.execute("SELECT COUNT(*), MIN(quando) FROM tentativas_login WHERE chave = ?", (chave,)).fetchone()
    if n >= LIMITE_TENTATIVAS:
        minutos = max(1, math.ceil((primeira + JANELA_SEG - agora) / 60))
        db.commit()
        return erro(f"Muitas tentativas incorretas. Tente novamente em {minutos} min.", 429)

    u = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    # compara sempre com algum hash, para o tempo de resposta não revelar se o e-mail existe
    senha_ok = check_password_hash(u["senha_hash"] if u else HASH_FALSO, senha)
    if u is None or not senha_ok:
        db.execute("INSERT INTO tentativas_login (chave, quando) VALUES (?, ?)", (chave, agora))
        db.commit()
        restantes = LIMITE_TENTATIVAS - n - 1
        aviso = f" Restam {restantes} tentativa(s)." if 0 < restantes <= 2 else ""
        return erro("E-mail ou senha incorretos." + aviso, 401)

    db.execute("DELETE FROM tentativas_login WHERE chave = ?", (chave,))
    db.commit()
    return jsonify({"token": gerar_token(u["id"], u["token_versao"]), "usuario": _usuario_json(u)})


@app.get("/api/auth/me")
@login_obrigatorio
def me():
    return jsonify(g.usuario)


@app.post("/api/auth/alterar-senha")
@login_obrigatorio
def alterar_senha():
    d = request.get_json(silent=True) or {}
    atual, nova = str(d.get("senha_atual", "")), str(d.get("nova_senha", ""))
    db = database.get_db()
    u = db.execute("SELECT * FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
    if not check_password_hash(u["senha_hash"], atual):
        return erro("A senha atual está incorreta.", 403)
    if senha_invalida(nova):
        return erro(senha_invalida(nova))
    if nova == atual:
        return erro("A nova senha deve ser diferente da atual.")
    if str(d.get("confirmar_senha", nova)) != nova:
        return erro("As senhas não coincidem.")
    versao = u["token_versao"] + 1  # invalida todos os tokens antigos (outros dispositivos)
    db.execute("UPDATE usuarios SET senha_hash = ?, token_versao = ? WHERE id = ?",
               (generate_password_hash(nova), versao, u["id"]))
    db.commit()
    return jsonify({"mensagem": "Senha alterada com sucesso!", "token": gerar_token(u["id"], versao)})


@app.post("/api/auth/novo-codigo")
@login_obrigatorio
def gerar_novo_codigo():
    """Gera um novo código de recuperação (o antigo deixa de valer). Exige a senha."""
    d = request.get_json(silent=True) or {}
    db = database.get_db()
    u = db.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
    if not check_password_hash(u["senha_hash"], str(d.get("senha", ""))):
        return erro("Senha incorreta.", 403)
    codigo = _guardar_codigo(db, g.usuario["id"])
    db.commit()
    return jsonify({"codigo_recuperacao": codigo})


@app.post("/api/auth/recuperar")
def recuperar_senha():
    """Esqueci minha senha: e-mail + código de recuperação + nova senha."""
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()
    codigo = _normalizar_codigo(d.get("codigo", ""))
    nova = str(d.get("nova_senha", ""))
    db = database.get_db()
    agora = int(time.time())
    chave = f"rec|{email}|{request.remote_addr}"
    db.execute("DELETE FROM tentativas_login WHERE quando < ? AND chave NOT LIKE 'ia|%'", (agora - JANELA_SEG,))
    n, primeira = db.execute("SELECT COUNT(*), MIN(quando) FROM tentativas_login WHERE chave = ?", (chave,)).fetchone()
    if n >= LIMITE_TENTATIVAS:
        minutos = max(1, math.ceil((primeira + JANELA_SEG - agora) / 60))
        db.commit()
        return erro(f"Muitas tentativas incorretas. Tente novamente em {minutos} min.", 429)

    u = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    hash_cod = (u["codigo_recuperacao_hash"] if u else None) or HASH_FALSO
    codigo_ok = len(codigo) == 12 and check_password_hash(hash_cod, codigo)
    if u is None or not u["codigo_recuperacao_hash"] or not codigo_ok:
        db.execute("INSERT INTO tentativas_login (chave, quando) VALUES (?, ?)", (chave, agora))
        db.commit()
        return erro("E-mail ou código de recuperação incorretos.", 401)
    if senha_invalida(nova):
        return erro(senha_invalida(nova))
    if str(d.get("confirmar_senha", nova)) != nova:
        return erro("As senhas não coincidem.")

    versao = u["token_versao"] + 1  # derruba as sessões antigas
    novo = novo_codigo()  # o código usado deixa de valer; entrega um novo
    db.execute("UPDATE usuarios SET senha_hash = ?, token_versao = ?, codigo_recuperacao_hash = ? WHERE id = ?",
               (generate_password_hash(nova), versao, generate_password_hash(_normalizar_codigo(novo)), u["id"]))
    db.execute("DELETE FROM tentativas_login WHERE chave = ? OR chave LIKE ?", (chave, f"{email}|%"))
    db.commit()
    return jsonify({"mensagem": "Senha redefinida!", "token": gerar_token(u["id"], versao),
                    "usuario": _usuario_json(u), "codigo_recuperacao": novo})


@app.delete("/api/auth/conta")
@login_obrigatorio
def excluir_conta():
    d = request.get_json(silent=True) or {}
    db = database.get_db()
    u = db.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (g.usuario["id"],)).fetchone()
    if not check_password_hash(u["senha_hash"], str(d.get("senha", ""))):
        return erro("Senha incorreta.", 403)
    db.execute("DELETE FROM usuarios WHERE id = ?", (g.usuario["id"],))  # rotinas saem junto (CASCADE)
    db.commit()
    return jsonify({"mensagem": "Conta excluída."})


# ---------------- rotinas ----------------
@app.get("/api/atividades")
@login_obrigatorio
def listar_atividades():
    smin, smax = regras.faixa_sono(g.usuario["idade"])
    return jsonify({"atividades": regras.ATIVIDADES,
                    "recomendacoes": {"sono_horas": [smin, smax], "agua_litros": regras.meta_agua_litros(),
                                      "texto": regras.resumo_recomendacoes(g.usuario["idade"])}})


@app.get("/api/modelos")
@login_obrigatorio
def listar_modelos():
    """Modelos prontos para escolher com um clique na rotina manual."""
    return jsonify(regras.MODELOS)


@app.post("/api/rotinas/manual")
@login_obrigatorio
def criar_manual():
    d = request.get_json(silent=True) or {}
    itens, msg = validar_itens(d.get("itens"))
    if msg:
        return erro(msg)
    titulo = str(d.get("titulo", "")).strip()[:80] or "Minha rotina"
    rotina_id = salvar_rotina(g.usuario["id"], titulo, "manual", None, itens)
    return jsonify(rotina_completa(rotina_id, g.usuario["id"])), 201


@app.post("/api/rotinas/ia")
@login_obrigatorio
def criar_com_ia():
    d = request.get_json(silent=True) or {}
    rotina_atual = str(d.get("rotina_atual", "")).strip()
    objetivos = str(d.get("objetivos", "")).strip()
    acorda, dorme = d.get("acorda"), d.get("dorme")
    if len(rotina_atual) < 10 or len(objetivos) < 5:
        return erro("Descreva sua rotina atual e o que você quer melhorar.")
    if not (regras.hora_valida(acorda) and regras.hora_valida(dorme)):
        return erro("Informe 'acorda' e 'dorme' no formato HH:MM.")

    peso = d.get("peso")
    if peso not in (None, "") and not (isinstance(peso, (int, float)) and not isinstance(peso, bool) and 20 <= peso <= 400):
        return erro("Peso inválido. Informe um número entre 20 e 400 (kg) ou deixe em branco.")

    # limite de uso da IA por usuário, para proteger a cota gratuita do Gemini
    db, agora = database.get_db(), int(time.time())
    chave_ia = f"ia|{g.usuario['id']}"
    db.execute("DELETE FROM tentativas_login WHERE chave = ? AND quando < ?", (chave_ia, agora - 3600))
    usadas = db.execute("SELECT COUNT(*) FROM tentativas_login WHERE chave = ?", (chave_ia,)).fetchone()[0]
    if usadas >= LIMITE_IA_HORA:
        db.commit()
        return erro(f"Você já gerou {LIMITE_IA_HORA} rotinas com IA na última hora. Tente de novo mais tarde "
                    "ou monte uma rotina manual com os modelos prontos.", 429)
    db.execute("INSERT INTO tentativas_login (chave, quando) VALUES (?, ?)", (chave_ia, agora))
    db.commit()

    dados = {"rotina_atual": rotina_atual[:2000], "objetivos": objetivos[:1000], "acorda": acorda,
             "dorme": dorme, "compromissos": str(d.get("compromissos", ""))[:500],
             "peso": peso if isinstance(peso, (int, float)) else None}
    motivo = None
    try:
        resultado = gerar_com_ia(g.usuario, dados)
        origem = "ia"
    except IAIndisponivel as e:
        motivo = str(e)
        app.logger.warning("IA indisponível, usando plano B: %s", e)
        itens = regras.gerar_rotina_basica(g.usuario["idade"], acorda, dorme,
                                           d.get("trabalho_inicio") if regras.hora_valida(d.get("trabalho_inicio")) else None,
                                           d.get("trabalho_fim") if regras.hora_valida(d.get("trabalho_fim")) else None)
        resultado = {"titulo": "Rotina saudável sugerida", "itens": itens,
                     "resumo": "Rotina gerada pelo modo automático do Sincro, seguindo as recomendações de "
                               "sono, alimentação, hidratação e treino para a sua idade."}
        origem = "ia_fallback"

    rotina_id = salvar_rotina(g.usuario["id"], resultado["titulo"], origem, resultado["resumo"], resultado["itens"])
    resposta = rotina_completa(rotina_id, g.usuario["id"])
    if motivo:
        resposta["motivo_fallback"] = motivo  # ajuda a descobrir por que a IA não respondeu
    elif resultado.get("modelo"):
        resposta["modelo_ia"] = resultado["modelo"]
    return jsonify(resposta), 201


@app.get("/api/rotinas")
@login_obrigatorio
def listar_rotinas():
    linhas = database.get_db().execute(
        "SELECT id, titulo, origem, criado_em FROM rotinas WHERE usuario_id = ? ORDER BY id DESC",
        (g.usuario["id"],)).fetchall()
    return jsonify([dict(l) for l in linhas])


@app.get("/api/rotinas/<int:rotina_id>")
@login_obrigatorio
def ver_rotina(rotina_id):
    r = rotina_completa(rotina_id, g.usuario["id"])
    return jsonify(r) if r else erro("Rotina não encontrada.", 404)


@app.put("/api/rotinas/<int:rotina_id>")
@login_obrigatorio
def editar_rotina(rotina_id):
    if rotina_completa(rotina_id, g.usuario["id"]) is None:
        return erro("Rotina não encontrada.", 404)
    d = request.get_json(silent=True) or {}
    itens, msg = validar_itens(d.get("itens"))
    if msg:
        return erro(msg)
    db = database.get_db()
    db.execute("DELETE FROM itens_rotina WHERE rotina_id = ?", (rotina_id,))
    db.executemany(
        "INSERT INTO itens_rotina (rotina_id, atividade, inicio, fim, descricao) VALUES (?, ?, ?, ?, ?)",
        [(rotina_id, i["atividade"], i["inicio"], i["fim"], i["descricao"]) for i in itens])
    if d.get("titulo"):
        db.execute("UPDATE rotinas SET titulo = ? WHERE id = ?", (str(d["titulo"]).strip()[:80], rotina_id))
    db.commit()
    return jsonify(rotina_completa(rotina_id, g.usuario["id"]))


@app.delete("/api/rotinas/<int:rotina_id>")
@login_obrigatorio
def apagar_rotina(rotina_id):
    if rotina_completa(rotina_id, g.usuario["id"]) is None:
        return erro("Rotina não encontrada.", 404)
    db = database.get_db()
    db.execute("DELETE FROM rotinas WHERE id = ?", (rotina_id,))
    db.commit()
    return jsonify({"mensagem": "Rotina apagada."})


# ---------------- front-end e saúde ----------------
@app.get("/api/saude")
def saude():
    return jsonify({"status": "ok", "ia_configurada": bool(os.getenv("GEMINI_API_KEY"))})


@app.get("/api/ia/diagnostico")
@login_obrigatorio
def diagnostico_ia():
    """Testa a chave do Gemini e explica, em português, o que está errado (se estiver)."""
    return jsonify(diagnosticar())


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(404)
def nao_encontrado(_e):
    if request.path.startswith("/api/"):
        return erro("Rota não encontrada.", 404)
    return send_from_directory(app.static_folder, "index.html")


def _criar_demo():
    """Cria (se faltar) uma conta de demonstração a partir de DEMO_EMAIL e DEMO_SENHA.

    Útil em hospedagens grátis com disco temporário (ex.: Render), onde o banco é apagado quando o
    servidor "dorme": a conta de demonstração é recriada sozinha a cada inicialização.
    """
    email, senha = os.getenv("DEMO_EMAIL", "").strip().lower(), os.getenv("DEMO_SENHA", "")
    if not email or not senha:
        return
    if not REGEX_EMAIL.match(email) or senha_invalida(senha):
        app.logger.warning("DEMO_EMAIL/DEMO_SENHA ignorados: e-mail inválido ou senha fraca (use 8+ caracteres com letras e números).")
        return
    con = sqlite3.connect(database.caminho_db())
    try:
        if con.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone():
            return
        cur = con.execute(
            "INSERT INTO usuarios (nome, sobrenome, idade, email, senha_hash, codigo_recuperacao_hash) VALUES (?, ?, ?, ?, ?, ?)",
            ("Demo", "Sincro", 20, email, generate_password_hash(senha),
             generate_password_hash(_normalizar_codigo(novo_codigo()))))
        modelo = regras.MODELOS[0]
        rid = con.execute("INSERT INTO rotinas (usuario_id, titulo, origem, resumo) VALUES (?, ?, 'manual', NULL)",
                          (cur.lastrowid, modelo["titulo"])).lastrowid
        con.executemany("INSERT INTO itens_rotina (rotina_id, atividade, inicio, fim, descricao) VALUES (?, ?, ?, ?, ?)",
                        [(rid, i["atividade"], i["inicio"], i["fim"], i["descricao"]) for i in modelo["itens"]])
        con.commit()
    except sqlite3.IntegrityError:
        pass  # outro processo criou ao mesmo tempo
    finally:
        con.close()


_criar_demo()


if __name__ == "__main__":
    # debug fica DESLIGADO por padrão (o modo debug expõe um console que executa código).
    # Para ligar só no seu computador: defina FLASK_DEBUG=1 no .env.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
