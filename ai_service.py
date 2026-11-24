"""Integração com a IA (Google Gemini, tem plano gratuito).

Fluxo: montamos um prompt com os dados do usuário + regras de saúde,
pedimos a resposta em JSON, validamos tudo e devolvemos uma lista de itens.
Se a IA falhar (sem chave, sem internet, resposta inválida), a API usa
o gerador por regras (routine_rules.gerar_rotina_basica) como plano B.
"""
import json
import os
import requests

import routine_rules as regras


class IAIndisponivel(Exception):
    pass


def _montar_prompt(usuario, dados):
    return f"""Você é o assistente de rotina do site Sincro, que ajuda pessoas com pobreza de tempo.
Crie uma rotina diária COMPLETA, realista e saudável em português do Brasil.

PERFIL: {usuario['nome']}, {usuario['idade']} anos.
HORA DE ACORDAR: {dados['acorda']}   HORA DE DORMIR: {dados['dorme']}
ROTINA ATUAL (descrita pelo usuário): {dados['rotina_atual']}
O QUE ELE QUER MELHORAR / PRECISA: {dados['objetivos']}
COMPROMISSOS FIXOS (não podem ser movidos): {dados.get('compromissos') or 'nenhum informado'}

REGRAS DE SAÚDE (obrigatórias):
{regras.resumo_recomendacoes(usuario['idade'], dados.get('peso'))}

REGRAS DE FORMATO:
- Cubra as 24 horas do dia, respeitando os compromissos fixos.
- Use apenas estas atividades: sono, alimentacao, hidratacao, musculacao, trabalho, estudo, lazer, outro.
- Horários no formato HH:MM (24h). O sono começa na hora de dormir e termina na hora de acordar.
- Inclua pelo menos 5 lembretes de hidratacao (duração de 5 minutos cada).
- Não sobreponha atividades (exceto hidratacao, e alimentacao dentro do expediente).
- Responda SOMENTE com JSON válido neste formato:
{{"titulo": "string curta", "resumo": "2 a 3 frases explicando as melhorias feitas",
  "itens": [{{"atividade": "sono", "inicio": "23:00", "fim": "07:00", "descricao": "texto curto"}}]}}"""


def _limpar_json(texto):
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    return json.loads(texto.strip())


def _validar(resposta):
    itens = []
    for it in resposta.get("itens", []):
        atividade = str(it.get("atividade", "")).lower().strip()
        if atividade not in regras.ATIVIDADES:
            atividade = "outro"
        ini, fim = it.get("inicio"), it.get("fim")
        if not (regras.hora_valida(ini) and regras.hora_valida(fim)):
            continue
        itens.append({
            "atividade": atividade,
            "inicio": ini,
            "fim": fim,
            "descricao": str(it.get("descricao", ""))[:200],
        })
    if len(itens) < 5:
        raise IAIndisponivel("A IA devolveu poucos itens válidos.")
    return {
        "titulo": str(resposta.get("titulo", "Rotina criada pela IA"))[:80],
        "resumo": str(resposta.get("resumo", ""))[:600],
        "itens": itens,
    }


# Modelos tentados em ordem. Cada um tem cota gratuita própria: se um estourar (429) ou não estiver
# disponível para a sua chave (404), o Sincro tenta o próximo antes de cair no plano B.
# O Google restringiu os modelos 2.5 a quem já os usava; para projetos novos recomenda 3.8 Flash / 3.5 Flash-Lite.
MODELOS_PADRAO = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
MAX_MODELOS_POR_PEDIDO = 3


def _modelos():
    """GEMINI_MODEL (se definido, pode ter vários separados por vírgula) vem primeiro."""
    extra = [m.strip() for m in os.getenv("GEMINI_MODEL", "").split(",") if m.strip()]
    lista = []
    for m in extra + MODELOS_PADRAO:
        if m not in lista:
            lista.append(m)
    return lista


def _chave():
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if not chave or chave.startswith("cole_aqui"):
        raise IAIndisponivel("GEMINI_API_KEY não configurada no arquivo .env.")
    return chave


def _chamar(modelo, chave, corpo, timeout):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    return requests.post(url, headers={"x-goog-api-key": chave}, json=corpo, timeout=timeout)


def _msg_erro(resposta):
    """Extrai a mensagem de erro da resposta do Gemini (sem expor a chave)."""
    try:
        return str(resposta.json()["error"]["message"])[:300]
    except Exception:
        return resposta.text[:200]


def _chave_invalida(resposta):
    m = _msg_erro(resposta).lower()
    return resposta.status_code in (401, 403) or "api key" in m or "api_key" in m


def gerar_com_ia(usuario, dados):
    chave = _chave()
    corpo = {
        "contents": [{"parts": [{"text": _montar_prompt(usuario, dados)}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    falhas = []
    for modelo in _modelos()[:MAX_MODELOS_POR_PEDIDO]:
        try:
            r = _chamar(modelo, chave, corpo, timeout=60)
        except requests.RequestException as erro:  # sem internet, tempo esgotado...
            raise IAIndisponivel(f"Sem conexão com a IA ({type(erro).__name__}).")
        if r.status_code != 200:
            if _chave_invalida(r):
                raise IAIndisponivel(f"Chave da IA recusada (HTTP {r.status_code}): {_msg_erro(r)}")
            falhas.append(f"{modelo}: HTTP {r.status_code}")
            continue  # cota, modelo indisponível ou erro do servidor: tenta o próximo modelo
        try:
            texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            resultado = _validar(_limpar_json(texto))
            resultado["modelo"] = modelo
            return resultado
        except Exception as erro:  # JSON quebrado, poucos itens...
            falhas.append(f"{modelo}: resposta inválida ({type(erro).__name__})")
    raise IAIndisponivel("A IA não respondeu. Tentativas: " + "; ".join(falhas))


def diagnosticar():
    """Testa cada modelo com um pedido mínimo e explica, em português, o que funciona."""
    try:
        chave = _chave()
    except IAIndisponivel as e:
        return {"ok": False, "modelos": [], "mensagem": str(e)}
    dicas = {400: "pedido recusado (confira o nome do modelo)", 404: "modelo não disponível para a sua chave",
             429: "cota gratuita esgotada por agora"}
    resultados, funcionando = [], None
    for modelo in _modelos():
        try:
            r = _chamar(modelo, chave, {"contents": [{"parts": [{"text": "Responda apenas: ok"}]}]}, timeout=25)
        except requests.RequestException as e:
            return {"ok": False, "modelos": resultados,
                    "mensagem": f"Não foi possível conectar ao Google ({type(e).__name__}). Sem internet, ou o servidor "
                                "bloqueia o acesso (no PythonAnywhere grátis, confira se .googleapis.com está liberado)."}
        if r.status_code == 200:
            resultados.append({"modelo": modelo, "ok": True, "detalhe": "funcionando"})
            funcionando = funcionando or modelo
            break  # achou um que funciona; não gasta mais cota testando os outros
        if _chave_invalida(r):
            return {"ok": False, "modelos": resultados,
                    "mensagem": f"A chave foi recusada (HTTP {r.status_code}): {_msg_erro(r)}. Gere outra em aistudio.google.com e confira o .env."}
        resultados.append({"modelo": modelo, "ok": False, "detalhe": f"HTTP {r.status_code}: {dicas.get(r.status_code, _msg_erro(r))}"})
    if funcionando:
        return {"ok": True, "modelos": resultados, "modelo": funcionando,
                "mensagem": f"A IA está funcionando (modelo {funcionando})."}
    return {"ok": False, "modelos": resultados,
            "mensagem": "Nenhum modelo respondeu: " + "; ".join(f"{x['modelo']} → {x['detalhe']}" for x in resultados)}
