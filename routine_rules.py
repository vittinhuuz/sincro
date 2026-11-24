"""Regras de saúde e utilidades de horário usadas pela API.

Aqui ficam as recomendações (sono, alimentação, hidratação, treino) que servem
para: 1) avisar o usuário quando a rotina manual tem problemas; 2) guiar a IA;
3) gerar uma rotina básica quando a IA estiver indisponível.
"""
import re

ATIVIDADES = {
    "sono": "Sono",
    "alimentacao": "Alimentação",
    "hidratacao": "Hidratação",
    "musculacao": "Musculação",
    "trabalho": "Trabalho",
    "estudo": "Estudo",
    "lazer": "Lazer",
    "outro": "Outro",
}

REGEX_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


# ---------- utilidades de horário ----------
def hora_valida(txt):
    return isinstance(txt, str) and bool(REGEX_HORA.match(txt))


def para_min(txt):
    h, m = txt.split(":")
    return int(h) * 60 + int(m)


def para_txt(minutos):
    minutos %= 1440
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def duracao_min(inicio, fim):
    """Duração em minutos; se o fim for 'menor' que o início, passou da meia-noite."""
    d = para_min(fim) - para_min(inicio)
    return d if d > 0 else d + 1440


def intervalos(inicio, fim):
    """Converte para lista de intervalos dentro de 0..1440 (divide se cruzar meia-noite)."""
    a, b = para_min(inicio), para_min(fim)
    if b > a:
        return [(a, b)]
    return [(a, 1440), (0, b)] if b > 0 else [(a, 1440)]


def conflita(i1, f1, i2, f2):
    for a1, b1 in intervalos(i1, f1):
        for a2, b2 in intervalos(i2, f2):
            if a1 < b2 and a2 < b1:
                return True
    return False


# ---------- recomendações ----------
def faixa_sono(idade):
    """Horas de sono recomendadas (referência: National Sleep Foundation)."""
    if idade <= 13:
        return (9, 11)
    if idade <= 17:
        return (8, 10)
    if idade <= 64:
        return (7, 9)
    return (7, 8)


def meta_agua_litros(peso_kg=None):
    """~35 ml por kg de peso. Sem peso informado, usa 2 litros como referência."""
    if peso_kg and 25 <= peso_kg <= 300:
        return round(peso_kg * 0.035, 1)
    return 2.0


def resumo_recomendacoes(idade, peso_kg=None):
    smin, smax = faixa_sono(idade)
    return (
        f"- Sono: entre {smin}h e {smax}h por noite, em horários regulares.\n"
        "- Alimentação: 3 refeições principais + 1 ou 2 lanches, com intervalo de 3 a 4 horas; "
        "jantar pelo menos 2h antes de dormir.\n"
        f"- Hidratação: cerca de {meta_agua_litros(peso_kg)} litros por dia, distribuídos em lembretes "
        "ao longo do dia (a cada 2 horas, aproximadamente).\n"
        "- Musculação: 3 a 5 vezes por semana, 45 a 90 minutos, terminando ao menos 1h antes de dormir.\n"
        "- Evitar telas e atividades intensas na hora anterior ao sono."
    )


# ---------- análise de uma rotina ----------
def analisar(itens, idade, peso_kg=None):
    """Recebe a lista de itens e devolve uma lista de avisos (strings)."""
    avisos = []

    # conflitos de horário (hidratação é um lembrete rápido, então é ignorada)
    principais = [i for i in itens if i["atividade"] != "hidratacao"]
    for a in range(len(principais)):
        for b in range(a + 1, len(principais)):
            x, y = principais[a], principais[b]
            pausa = {x["atividade"], y["atividade"]} & {"alimentacao"} and {x["atividade"], y["atividade"]} & {"trabalho", "estudo"}
            if pausa:
                continue  # almoçar durante o expediente é normal
            if conflita(x["inicio"], x["fim"], y["inicio"], y["fim"]):
                avisos.append(
                    f"Conflito de horário entre {ATIVIDADES.get(x['atividade'], x['atividade'])} "
                    f"({x['inicio']}-{x['fim']}) e {ATIVIDADES.get(y['atividade'], y['atividade'])} "
                    f"({y['inicio']}-{y['fim']})."
                )

    # sono
    sonos = [i for i in itens if i["atividade"] == "sono"]
    smin, smax = faixa_sono(idade)
    if not sonos:
        avisos.append(f"Nenhum horário de sono definido. Para a sua idade, o ideal é {smin}h a {smax}h por noite.")
    else:
        total = sum(duracao_min(s["inicio"], s["fim"]) for s in sonos) / 60
        if total < smin:
            avisos.append(f"Você dorme {total:.1f}h por noite; para a sua idade o recomendado é {smin}h a {smax}h.")
        elif total > smax + 1:
            avisos.append(f"Você reserva {total:.1f}h para dormir, acima do recomendado ({smin}h a {smax}h).")

    # alimentação
    refeicoes = sorted(
        (i for i in itens if i["atividade"] == "alimentacao"), key=lambda i: para_min(i["inicio"])
    )
    if len(refeicoes) < 3:
        avisos.append("Inclua ao menos 3 refeições principais (café da manhã, almoço e jantar).")
    for a, b in zip(refeicoes, refeicoes[1:]):
        folga = para_min(b["inicio"]) - para_min(a["fim"])
        if folga > 360:
            avisos.append(f"Intervalo de mais de 6h sem comer entre {a['fim']} e {b['inicio']}.")
    if sonos and refeicoes:
        ini_sono = para_min(sonos[0]["inicio"])
        ultima = max(refeicoes, key=lambda i: para_min(i["fim"]))
        dif = (ini_sono - para_min(ultima["fim"])) % 1440
        if dif < 90:
            avisos.append("Evite comer menos de 2h antes de dormir (a última refeição está muito perto do sono).")

    # hidratação
    hid = [i for i in itens if i["atividade"] == "hidratacao"]
    if len(hid) < 5:
        avisos.append(
            f"Programe pelo menos 5 lembretes de água ao longo do dia (meta de ~{meta_agua_litros(peso_kg)} L)."
        )

    # musculação perto do sono
    for t in (i for i in itens if i["atividade"] == "musculacao"):
        for s in sonos:
            if (para_min(s["inicio"]) - para_min(t["fim"])) % 1440 < 60:
                avisos.append("Treino terminando menos de 1h antes de dormir pode atrapalhar o sono.")
                break
    return avisos


# ---------- rotina básica (plano B quando a IA falha) ----------
def _ocupado(ocupados, ini, fim):
    return any(conflita(ini, fim, o[0], o[1]) for o in ocupados)


def gerar_rotina_basica(idade, acorda, dorme, trabalho_ini=None, trabalho_fim=None, quer_treinar=True):
    """Monta uma rotina saudável por regras (sem IA)."""
    itens = []
    ocupados = []

    bloqueios_refeicao = []  # tudo que ocupa horário, exceto trabalho/estudo (pausa para comer é permitida)

    def add(atividade, ini, fim, desc):
        itens.append({"atividade": atividade, "inicio": ini, "fim": fim, "descricao": desc})
        if atividade != "hidratacao":
            ocupados.append((ini, fim))
            if atividade not in ("trabalho", "estudo"):
                bloqueios_refeicao.append((ini, fim))

    a, d = para_min(acorda), para_min(dorme)
    add("sono", dorme, acorda, "Sono reparador em horário regular")
    if trabalho_ini and trabalho_fim:
        add("trabalho", trabalho_ini, trabalho_fim, "Expediente / atividades principais")

    # refeições
    cafe = para_txt(a + 20)
    add("alimentacao", cafe, para_txt(a + 50), "Café da manhã")
    for ini, nome in (("12:30", "Almoço"), ("16:00", "Lanche da tarde")):
        fim = para_txt(para_min(ini) + 40)
        if not _ocupado(bloqueios_refeicao, ini, fim):
            add("alimentacao", ini, fim, nome)
        else:  # tenta deslocar para uma janela livre
            for deslocamento in range(30, 240, 30):
                ini2 = para_txt(para_min(ini) + deslocamento)
                fim2 = para_txt(para_min(ini2) + 40)
                if not _ocupado(bloqueios_refeicao, ini2, fim2):
                    add("alimentacao", ini2, fim2, nome)
                    break
    jantar = para_txt(d - 180)
    add("alimentacao", jantar, para_txt(para_min(jantar) + 40), "Jantar leve (2h+ antes de dormir)")

    # treino
    if quer_treinar:
        duracao = 60
        candidatos = ["18:00", "18:30", "19:00", "07:00", "12:00", "17:00", "06:30", "20:00"]
        for c in candidatos:
            fim = para_txt(para_min(c) + duracao)
            ate_dormir = (d - para_min(fim)) % 1440
            if not _ocupado(ocupados, c, fim) and ate_dormir >= 120:
                add("musculacao", c, fim, "Treino de musculação (3 a 5x por semana)")
                break

    # hidratação a cada ~2h enquanto acordado, parando 1h antes de dormir
    t = a
    limite = d if d > a else d + 1440
    pos = a
    while pos < limite - 60:
        itens.append({"atividade": "hidratacao", "inicio": para_txt(pos), "fim": para_txt(pos + 5),
                      "descricao": "Beber um copo de água (250 ml)"})
        pos += 120

    itens.sort(key=lambda i: (para_min(i["inicio"]) - a) % 1440)
    return itens


# ---------- modelos prontos (rotina manual com 1 clique) ----------
def _it(a, i, f, d=""):
    return {"atividade": a, "inicio": i, "fim": f, "descricao": d}


_AGUA = [_it("hidratacao", h, h[:3] + "05", "Beber um copo de água") for h in ("09:30", "11:00", "15:00", "17:00", "21:00")]

MODELOS = [
    {"id": "equilibrada", "nome": "Dia equilibrado", "emoji": "⚖️",
     "descricao": "Sono, refeições, trabalho e lazer em equilíbrio.",
     "titulo": "Dia equilibrado",
     "itens": [_it("sono", "23:00", "07:00", "Sono reparador"), _it("alimentacao", "07:30", "08:00", "Café da manhã"),
               _it("trabalho", "09:00", "17:00", "Expediente"), _it("alimentacao", "12:30", "13:15", "Almoço"),
               _it("alimentacao", "16:00", "16:20", "Lanche da tarde"), _it("musculacao", "18:00", "19:00", "Treino"),
               _it("alimentacao", "20:00", "20:40", "Jantar"), _it("lazer", "21:00", "22:30", "Tempo livre")] + _AGUA},
    {"id": "treino", "nome": "Foco em treino", "emoji": "🏋️",
     "descricao": "Treino pela manhã e refeições pensadas para a recuperação.",
     "titulo": "Foco em treino",
     "itens": [_it("sono", "22:30", "06:30", "Sono reparador"), _it("alimentacao", "06:40", "07:00", "Lanche pré-treino"),
               _it("musculacao", "07:00", "08:15", "Treino"), _it("alimentacao", "08:30", "09:00", "Café da manhã"),
               _it("trabalho", "09:30", "17:30", "Expediente"), _it("alimentacao", "12:30", "13:15", "Almoço"),
               _it("alimentacao", "16:00", "16:20", "Lanche da tarde"), _it("alimentacao", "19:30", "20:15", "Jantar"),
               _it("lazer", "20:30", "22:00", "Descanso")] + _AGUA},
    {"id": "estudante", "nome": "Estudante", "emoji": "📚",
     "descricao": "Aulas pela manhã, estudo à tarde e pausas para respirar.",
     "titulo": "Rotina de estudante",
     "itens": [_it("sono", "22:30", "06:30", "Sono reparador"), _it("alimentacao", "06:45", "07:15", "Café da manhã"),
               _it("estudo", "07:30", "12:00", "Aulas"), _it("alimentacao", "12:15", "13:00", "Almoço"),
               _it("estudo", "14:00", "16:30", "Estudo e tarefas"), _it("alimentacao", "16:30", "16:50", "Lanche"),
               _it("musculacao", "17:00", "18:00", "Atividade física"),
               _it("alimentacao", "19:30", "20:15", "Jantar"), _it("estudo", "20:30", "21:30", "Revisão"),
               _it("lazer", "21:30", "22:30", "Tempo livre")] + _AGUA},
    {"id": "trabalho-noite", "nome": "Trabalho + faculdade à noite", "emoji": "🌙",
     "descricao": "Para quem trabalha de dia e estuda à noite.",
     "titulo": "Trabalho e faculdade",
     "itens": [_it("sono", "23:30", "06:30", "Sono reparador"), _it("alimentacao", "06:45", "07:15", "Café da manhã"),
               _it("trabalho", "08:00", "17:00", "Expediente"), _it("alimentacao", "12:00", "12:50", "Almoço"),
               _it("alimentacao", "17:15", "17:45", "Lanche"), _it("estudo", "19:00", "22:30", "Aulas"),
               _it("alimentacao", "18:15", "18:55", "Jantar")] + _AGUA},
    {"id": "descanso", "nome": "Fim de semana de descanso", "emoji": "🌿",
     "descricao": "Mais sono, lazer e uma atividade leve.",
     "titulo": "Fim de semana de descanso",
     "itens": [_it("sono", "00:00", "08:30", "Dormir sem pressa"), _it("alimentacao", "09:00", "09:45", "Café da manhã"),
               _it("musculacao", "10:30", "11:30", "Atividade leve"), _it("alimentacao", "13:00", "14:00", "Almoço"),
               _it("lazer", "15:00", "18:00", "Lazer"), _it("alimentacao", "20:00", "21:00", "Jantar"),
               _it("lazer", "21:30", "23:30", "Descanso")] + _AGUA},
]
