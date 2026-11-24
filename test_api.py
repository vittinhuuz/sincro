"""Teste automático da API: python test_api.py"""
import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "teste.db")
os.environ["GEMINI_API_KEY"] = ""
from app import app

c = app.test_client()
def ok(cond, msg):
    print(("OK   " if cond else "FALHA"), msg); assert cond

r = c.post("/api/auth/cadastro", json={"nome":"Vitor","sobrenome":"Silva","idade":19,"email":"v@x.com","senha":"Senha1234"})
ok(r.status_code == 201, "cadastro")
COD = r.json["codigo_recuperacao"]
import re as _re
ok(bool(_re.match(r"^[A-Z2-9]{4}(-[A-Z2-9]{4}){2}$", COD)), f"cadastro devolve código de recuperação ({COD})")
ok(c.post("/api/auth/cadastro", json={"nome":"Vitor","sobrenome":"Silva","idade":19,"email":"v@x.com","senha":"Senha1234"}).status_code == 409, "e-mail duplicado bloqueado")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"errada"}).status_code == 401, "login com senha errada")
tok = c.post("/api/auth/login", json={"email":"v@x.com","senha":"Senha1234"}).json["token"]
H = {"Authorization": f"Bearer {tok}"}
# --- regras de cadastro ---
base = {"nome":"Ana","sobrenome":"Lima","idade":20,"email":"ana@x.com","senha":"Senha1234"}
ok(c.post("/api/auth/cadastro", json={**base,"senha":"abc"}).status_code == 400, "senha curta rejeitada")
ok(c.post("/api/auth/cadastro", json={**base,"senha":"somenteletras"}).status_code == 400, "senha sem número rejeitada")
ok(c.post("/api/auth/cadastro", json={**base,"confirmar_senha":"Outra1234"}).status_code == 400, "confirmação diferente rejeitada")
ok(c.post("/api/auth/cadastro", json={**base,"idade":19.5}).status_code == 400, "idade decimal rejeitada")
ok(c.post("/api/auth/cadastro", json={**base,"nome":"A1"}).status_code == 400, "nome inválido rejeitado")
ok(c.post("/api/auth/cadastro", json={**base,"email":"V@X.COM"}).status_code == 409, "e-mail duplicado (maiúsculas) bloqueado")
# --- alterar senha invalida token antigo ---
ok(c.post("/api/auth/alterar-senha", headers=H, json={"senha_atual":"errada123","nova_senha":"Nova12345"}).status_code == 403, "alterar senha: atual errada")
r = c.post("/api/auth/alterar-senha", headers=H, json={"senha_atual":"Senha1234","nova_senha":"Nova12345"})
ok(r.status_code == 200, "alterar senha")
ok(c.get("/api/auth/me", headers=H).status_code == 401, "token antigo deixa de valer")
tok = r.json["token"]; H = {"Authorization": f"Bearer {tok}"}
ok(c.get("/api/auth/me", headers=H).status_code == 200, "token novo vale")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Senha1234"}).status_code == 401, "senha antiga não entra")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Nova12345"}).status_code == 200, "senha nova entra")
# --- bloqueio por tentativas ---
for _ in range(5): c.post("/api/auth/login", json={"email":"v@x.com","senha":"errada999"})
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Nova12345"}).status_code == 429, "bloqueio após 5 erros")
import database, sqlite3
_c = sqlite3.connect(database.caminho_db()); _c.execute("DELETE FROM tentativas_login"); _c.commit(); _c.close()

ok(c.get("/api/rotinas").status_code == 401, "rota protegida sem token")
ok(c.get("/api/auth/me", headers=H).json["nome"] == "Vitor", "/me")

itens = [{"atividade":"sono","inicio":"23:00","fim":"06:00","descricao":"dormir"},
         {"atividade":"musculacao","inicio":"22:00","fim":"23:00"}]
r = c.post("/api/rotinas/manual", headers=H, json={"titulo":"Teste","itens":itens})
ok(r.status_code == 201 and len(r.json["avisos"]) > 0, f"rotina manual + avisos ({len(r.json['avisos'])})")
ok(c.post("/api/rotinas/manual", headers=H, json={"itens":[{"atividade":"sono","inicio":"25:00","fim":"06:00"}]}).status_code == 400, "hora inválida")

r = c.post("/api/rotinas/ia", headers=H, json={"rotina_atual":"Acordo 7h, trabalho até as 17h, durmo tarde","objetivos":"treinar e dormir melhor","acorda":"07:00","dorme":"23:00","trabalho_inicio":"09:00","trabalho_fim":"17:00"})
ok(r.status_code == 201 and r.json["origem"] == "ia_fallback", "rotina IA (plano B sem chave)")
rid = r.json["id"]
ok(c.get(f"/api/rotinas/{rid}", headers=H).status_code == 200, "ver rotina")
ok(len(c.get("/api/rotinas", headers=H).json) == 2, "listar rotinas")

# --- editar rotina ---
r = c.put(f"/api/rotinas/{rid}", headers=H, json={"titulo":"Editada","itens":[{"atividade":"sono","inicio":"23:00","fim":"07:00"},{"atividade":"estudo","inicio":"08:00","fim":"10:00"}]})
ok(r.status_code == 200 and r.json["titulo"] == "Editada" and len(r.json["itens"]) == 2, "editar rotina (título e itens)")
ok(c.put(f"/api/rotinas/{rid}", headers=H, json={"itens":[{"atividade":"xx","inicio":"08:00","fim":"10:00"}]}).status_code == 400, "editar com atividade inválida é rejeitado")
ok(c.put("/api/rotinas/99999", headers=H, json={"itens":[]}).status_code == 404, "editar rotina inexistente")
ok(c.delete(f"/api/rotinas/{rid}", headers=H).status_code == 200, "apagar")

# --- modelos prontos ---
m = c.get("/api/modelos", headers=H)
ok(m.status_code == 200 and len(m.json) >= 4, f"modelos prontos ({len(m.json)})")
r = c.post("/api/rotinas/manual", headers=H, json={"titulo": m.json[0]["titulo"], "itens": m.json[0]["itens"]})
ok(r.status_code == 201, "modelo pronto vira rotina válida")
ok(c.get("/api/modelos").status_code == 401, "modelos exigem login")

# --- IA simulada (sem internet): resposta boa e erros do Google ---
import ai_service, json as _json
class _Resp:
    def __init__(s, code, corpo): s.status_code, s._c, s.text = code, corpo, _json.dumps(corpo)
    def json(s): return s._c
_orig = ai_service.requests.post
boa = {"titulo":"Rotina IA","resumo":"Ajustei seu sono.","itens":[
  {"atividade":"sono","inicio":"23:00","fim":"07:00","descricao":"x"},{"atividade":"alimentacao","inicio":"07:30","fim":"08:00","descricao":"x"},
  {"atividade":"trabalho","inicio":"09:00","fim":"17:00","descricao":"x"},{"atividade":"alimentacao","inicio":"12:30","fim":"13:10","descricao":"x"},
  {"atividade":"musculacao","inicio":"18:00","fim":"19:00","descricao":"x"},{"atividade":"hidratacao","inicio":"10:00","fim":"10:05","descricao":"x"}]}
corpo_ia = {"rotina_atual":"Acordo 7h e trabalho o dia todo","objetivos":"treinar e dormir melhor","acorda":"07:00","dorme":"23:00"}
os.environ["GEMINI_API_KEY"] = "chave-de-teste-SEGREDO"
ai_service.requests.post = lambda *a, **k: _Resp(200, {"candidates":[{"content":{"parts":[{"text":"```json\n"+_json.dumps(boa)+"\n```"}]}}]})
r = c.post("/api/rotinas/ia", headers=H, json=corpo_ia)
ok(r.status_code == 201 and r.json["origem"] == "ia" and r.json["titulo"] == "Rotina IA", "IA simulada: resposta válida vira rotina (origem=ia)")
ai_service.requests.post = lambda *a, **k: _Resp(403, {"error":{"message":"API key not valid"}})
r = c.post("/api/rotinas/ia", headers=H, json=corpo_ia)
ok(r.json["origem"] == "ia_fallback" and "403" in r.json["motivo_fallback"], "IA simulada: erro 403 cai no plano B com motivo")
ok("SEGREDO" not in _json.dumps(r.json), "a chave da IA nunca aparece na resposta")

# encadeamento de modelos: o 1º não existe (404), o 2º responde
chamados = []
def _fake(url, **k):
    chamados.append(url.split("models/")[1].split(":")[0])
    return _Resp(404, {"error":{"message":"model not found"}}) if len(chamados) == 1 else _Resp(200, {"candidates":[{"content":{"parts":[{"text":_json.dumps(boa)}]}}]})
ai_service.requests.post = _fake
r = c.post("/api/rotinas/ia", headers=H, json=corpo_ia)
ok(r.json["origem"] == "ia" and r.json["modelo_ia"] == chamados[1] and len(chamados) == 2, f"IA tenta o próximo modelo quando o primeiro falha ({chamados})")
ai_service.requests.post = lambda *a, **k: _Resp(200, {"candidates":[{"content":{"parts":[{"text":_json.dumps(boa)}]}}]})
ok(c.post("/api/rotinas/ia", headers=H, json={**corpo_ia, "peso": 5}).status_code == 400, "peso fora do intervalo é rejeitado")
ok(c.post("/api/rotinas/ia", headers=H, json={**corpo_ia, "peso": 72.5}).status_code == 201, "peso válido é aceito")
ai_service.requests.post = lambda *a, **k: _Resp(200, {"candidates":[{"content":{"parts":[{"text":"isto não é json"}]}}]})
ok(c.post("/api/rotinas/ia", headers=H, json=corpo_ia).json["origem"] == "ia_fallback", "IA simulada: resposta quebrada cai no plano B")

# limite de uso da IA por hora
import app as _app
codigos = [c.post("/api/rotinas/ia", headers=H, json=corpo_ia).status_code for _ in range(_app.LIMITE_IA_HORA + 1)]
ok(codigos[-1] == 429 and 201 in codigos, f"limite de {_app.LIMITE_IA_HORA} gerações de IA por hora (último = {codigos[-1]})")
_c = sqlite3.connect(database.caminho_db()); _c.execute("DELETE FROM tentativas_login"); _c.commit(); _c.close()
ai_service.requests.post = lambda *a, **k: _Resp(429, {"error":{"message":"quota"}})
d = c.get("/api/ia/diagnostico", headers=H).json
ok(d["ok"] is False and "cota" in d["mensagem"], "diagnóstico explica cota esgotada em todos os modelos")
ai_service.requests.post = lambda *a, **k: _Resp(200, {"candidates":[]})
ok(c.get("/api/ia/diagnostico", headers=H).json["ok"] is True, "diagnóstico: IA ok")
ai_service.requests.post = _orig
os.environ["GEMINI_API_KEY"] = ""
ok(c.get("/api/ia/diagnostico", headers=H).json["ok"] is False, "diagnóstico sem chave avisa")

# --- esqueci a senha (código de recuperação) ---
rec = {"email":"v@x.com","codigo":COD,"nova_senha":"Recuperada77","confirmar_senha":"Recuperada77"}
ok(c.post("/api/auth/recuperar", json={**rec,"codigo":"AAAA-BBBB-CCCC"}).status_code == 401, "recuperar: código errado")
ok(c.post("/api/auth/recuperar", json={**rec,"email":"naoexiste@x.com"}).status_code == 401, "recuperar: e-mail inexistente (mesma mensagem)")
ok(c.post("/api/auth/recuperar", json={**rec,"nova_senha":"curta","confirmar_senha":"curta"}).status_code == 400, "recuperar: senha fraca rejeitada")
r = c.post("/api/auth/recuperar", json={**rec,"codigo":COD.lower().replace("-"," ")})
ok(r.status_code == 200, "recuperar: código certo (aceita minúsculas e espaços)")
COD2 = r.json["codigo_recuperacao"]; H = {"Authorization": "Bearer " + r.json["token"]}
ok(COD2 != COD, "recuperar: gera código novo")
ok(c.post("/api/auth/recuperar", json=rec).status_code == 401, "recuperar: código usado não vale de novo")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Nova12345"}).status_code == 401, "recuperar: senha antiga não entra")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Recuperada77"}).status_code == 200, "recuperar: senha nova entra")
for _ in range(5): c.post("/api/auth/recuperar", json={**rec,"codigo":"ZZZZ-ZZZZ-ZZZZ"})
ok(c.post("/api/auth/recuperar", json={**rec,"codigo":COD2}).status_code == 429, "recuperar: bloqueio após 5 erros")
_c = sqlite3.connect(database.caminho_db()); _c.execute("DELETE FROM tentativas_login"); _c.commit(); _c.close()
ok(c.post("/api/auth/novo-codigo", headers=H, json={"senha":"errada999"}).status_code == 403, "novo código exige senha")
COD3 = c.post("/api/auth/novo-codigo", headers=H, json={"senha":"Recuperada77"}).json["codigo_recuperacao"]
ok(c.post("/api/auth/recuperar", json={**rec,"codigo":COD2}).status_code == 401, "novo código invalida o anterior")
ok(c.post("/api/auth/recuperar", json={**rec,"codigo":COD3,"nova_senha":"Nova12345","confirmar_senha":"Nova12345"}).status_code == 200, "recuperar com o código novo")
tok = c.post("/api/auth/login", json={"email":"v@x.com","senha":"Nova12345"}).json["token"]; H = {"Authorization": f"Bearer {tok}"}

ok(c.delete("/api/auth/conta", headers=H, json={"senha":"errada"}).status_code == 403, "excluir conta exige senha")
ok(c.delete("/api/auth/conta", headers=H, json={"senha":"Nova12345"}).status_code == 200, "excluir conta")
ok(c.post("/api/auth/login", json={"email":"v@x.com","senha":"Nova12345"}).status_code == 401, "conta excluída não entra")

# --- conta de demonstração automática (hospedagem com disco temporário) ---
os.environ["DEMO_EMAIL"] = "demo@sincro.com"; os.environ["DEMO_SENHA"] = "Demo12345"
import app as _app2
_app2._criar_demo(); _app2._criar_demo()  # chamar 2x não duplica
ok(c.post("/api/auth/login", json={"email":"demo@sincro.com","senha":"Demo12345"}).status_code == 200, "conta demo criada e login funciona")
_tok = c.post("/api/auth/login", json={"email":"demo@sincro.com","senha":"Demo12345"}).json["token"]
ok(len(c.get("/api/rotinas", headers={"Authorization": f"Bearer {_tok}"}).json) == 1, "conta demo vem com 1 rotina e sem duplicar")
os.environ["DEMO_EMAIL"] = ""

print("\nTudo certo!")
