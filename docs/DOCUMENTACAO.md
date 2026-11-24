# Documentação técnica do Sincro

Este documento descreve o que o sistema faz, como foi construído e como cada parte funciona. Tudo aqui corresponde ao código que está no repositório.

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Requisitos](#2-requisitos)
3. [Arquitetura](#3-arquitetura)
4. [Estrutura de arquivos](#4-estrutura-de-arquivos)
5. [Banco de dados](#5-banco-de-dados)
6. [Regras de saúde](#6-regras-de-saúde)
7. [Inteligência artificial](#7-inteligência-artificial)
8. [API (referência)](#8-api-referência)
9. [Front-end](#9-front-end)
10. [Segurança](#10-segurança)
11. [Configuração (variáveis de ambiente)](#11-configuração-variáveis-de-ambiente)
12. [Testes](#12-testes)
13. [Limitações conhecidas e melhorias futuras](#13-limitações-conhecidas-e-melhorias-futuras)

---

## 1. Visão geral

**Problema.** Muitas pessoas sentem que o dia "não rende" e, sem perceber, sacrificam sono, alimentação e água para encaixar compromissos ("pobreza de tempo").

**Solução.** O Sincro permite montar uma rotina diária e confere essa rotina contra recomendações de saúde, devolvendo avisos claros. A rotina pode ser:

- **manual**: o usuário escolhe as atividades e os horários, ou parte de um modelo pronto;
- **com IA**: o usuário descreve o dia atual e o que quer melhorar, e a IA propõe uma rotina;
- **automática (plano B)**: se a IA falhar, o próprio sistema monta uma rotina por regras.

**Público.** Qualquer pessoa de 10 a 120 anos (as recomendações de sono mudam por faixa etária).

## 2. Requisitos

| Item | Detalhe |
|---|---|
| Python | 3.10 ou superior |
| Dependências | Flask, PyJWT, requests, python-dotenv, gunicorn (ver `requirements.txt`) |
| Banco | SQLite (já vem com o Python; não precisa instalar) |
| IA (opcional) | Chave gratuita do Google AI Studio |
| Navegador | Qualquer navegador atual (Chrome, Edge, Firefox, Safari) |

## 3. Arquitetura

```
Navegador (HTML/CSS/JS)  ──HTTP/JSON──▶  Flask (app.py)  ──SQL──▶  SQLite (sincro.db)
                                              │
                                              └──HTTPS──▶  Google Gemini (ai_service.py)
```

- O **Flask** serve o front-end (pasta `static/`) e a API (rotas `/api/...`) no mesmo endereço. Por isso não há problema de CORS e o front usa caminhos relativos.
- O front é uma **página única** (SPA): `index.html` carrega `app.js`, que troca as telas pela parte do endereço depois do `#` (por exemplo `#/painel`).
- A comunicação é sempre em **JSON**. Erros voltam como `{"erro": "mensagem em português"}`.
- A autenticação usa um **token JWT** guardado no navegador (`localStorage`) e enviado no cabeçalho `Authorization: Bearer <token>`.

### Fluxo da "rotina com IA"

1. O front envia a descrição do usuário para `POST /api/rotinas/ia`.
2. O back-end valida os campos e confere o limite de uso da IA do usuário.
3. `ai_service.gerar_com_ia` monta o prompt (perfil, rotina atual, objetivos, regras de saúde) e chama o Gemini, tentando até 3 modelos em sequência.
4. A resposta (JSON) é **validada**: atividades permitidas, horários `HH:MM`, mínimo de 5 itens.
5. Se tudo der certo, a rotina é salva com `origem = "ia"`.
6. Se qualquer etapa falhar, `routine_rules.gerar_rotina_basica` monta a rotina por regras e ela é salva com `origem = "ia_fallback"`. O motivo da falha é devolvido em `motivo_fallback` e exibido ao usuário.

## 4. Estrutura de arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Aplicação Flask: rotas, autenticação, validações, limites de tentativa |
| `ai_service.py` | Prompt, chamada ao Gemini, validação da resposta, diagnóstico |
| `routine_rules.py` | Recomendações de saúde, análise de rotina, modelos prontos, rotina automática |
| `database.py` | Conexão SQLite e criação/migração das tabelas |
| `schema.sql` | Definição das tabelas |
| `wsgi.py` | Ponto de entrada para servidores de produção |
| `Procfile` | Comando de execução com gunicorn |
| `test_api.py` | Testes automáticos |
| `static/index.html` | Casca da página única |
| `static/js/app.js` | Telas, rotas do front, animações |
| `static/js/sincro-api.js` | Cliente da API (funções `Sincro.*`) |
| `static/css/style.css` | Estilos e animações |
| `static/img/` | Logos e imagens |

## 5. Banco de dados

SQLite, com chaves estrangeiras ativadas (`PRAGMA foreign_keys = ON`).

```
usuarios (1) ───< rotinas (1) ───< itens_rotina
```

### `usuarios`

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | INTEGER PK | autoincremento |
| `nome`, `sobrenome` | TEXT | 2 a 50 letras |
| `idade` | INTEGER | de 10 a 120 (`CHECK`) |
| `email` | TEXT UNIQUE | guardado em minúsculas |
| `senha_hash` | TEXT | hash da senha (nunca a senha) |
| `token_versao` | INTEGER | sobe ao trocar/redefinir a senha e invalida tokens antigos |
| `codigo_recuperacao_hash` | TEXT | hash do código de recuperação |
| `criado_em` | TEXT | data/hora do cadastro |

### `rotinas`

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | INTEGER PK | |
| `usuario_id` | INTEGER FK | `ON DELETE CASCADE` |
| `titulo` | TEXT | até 80 caracteres |
| `origem` | TEXT | `manual`, `ia` ou `ia_fallback` |
| `resumo` | TEXT | explicação das melhorias (rotinas de IA/automáticas) |
| `criado_em` | TEXT | |

### `itens_rotina`

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | INTEGER PK | |
| `rotina_id` | INTEGER FK | `ON DELETE CASCADE` |
| `atividade` | TEXT | `sono`, `alimentacao`, `hidratacao`, `musculacao`, `trabalho`, `estudo`, `lazer`, `outro` |
| `inicio`, `fim` | TEXT | formato `HH:MM`; se `fim` for menor que `inicio`, passa da meia-noite |
| `descricao` | TEXT | até 200 caracteres |

### `tentativas_login`

Tabela auxiliar de controle de abuso: guarda `chave` e `quando` (timestamp). Usada para:

- bloqueio de login (`email|ip`);
- bloqueio da recuperação de senha (`rec|email|ip`);
- limite de uso da IA por usuário (`ia|id`).

Excluir uma conta apaga também as rotinas e os itens (cascata).

## 6. Regras de saúde

Implementadas em `routine_rules.py`.

**Sono recomendado por idade** (referência: National Sleep Foundation):

| Idade | Horas por noite |
|---|---|
| 10 a 13 anos | 9 a 11 |
| 14 a 17 anos | 8 a 10 |
| 18 a 64 anos | 7 a 9 |
| 65 anos ou mais | 7 a 8 |

**Água:** cerca de **35 ml por kg** de peso. Sem peso informado, usa-se 2 litros como referência.

**Avisos gerados ao analisar uma rotina:**

| Situação | Aviso |
|---|---|
| Duas atividades no mesmo horário | Conflito de horário (hidratação é ignorada; comer durante trabalho/estudo é permitido) |
| Sem sono definido | Pede para definir o horário de sono |
| Sono abaixo da faixa | Avisa que dorme pouco para a idade |
| Sono muito acima da faixa (mais de 1 h além do máximo) | Avisa que reserva tempo demais para dormir |
| Menos de 3 refeições | Pede ao menos 3 refeições principais |
| Mais de 6 h entre refeições | Aponta o intervalo |
| Última refeição a menos de 1h30 do sono | Avisa para evitar comer tão perto de dormir |
| Menos de 5 lembretes de água | Pede mais lembretes (com a meta em litros) |
| Treino terminando menos de 1 h antes de dormir | Avisa que pode atrapalhar o sono |

Se nenhum aviso é gerado, a tela mostra "Rotina equilibrada".

> As recomendações são orientações gerais e **não substituem** a avaliação de um profissional de saúde.

**Modelos prontos:** Dia equilibrado, Foco em treino, Estudante, Trabalho + faculdade à noite e Fim de semana de descanso. Todos foram ajustados para não gerar avisos para as faixas etárias a que se destinam.

## 7. Inteligência artificial

Arquivo: `ai_service.py`. Serviço: **Google Gemini** (plano gratuito), chamado por REST em `generativelanguage.googleapis.com`.

**Chave.** Enviada no cabeçalho `x-goog-api-key` (e não na URL), para não aparecer em mensagens de erro ou logs. A chave fica só no `.env` do servidor e nunca vai ao navegador.

**Modelos.** O Sincro tenta, em ordem: o modelo definido em `GEMINI_MODEL` (se houver), `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite` e `gemini-3.1-flash-lite`, com no máximo 3 tentativas por pedido. Se um modelo estiver sem cota (429) ou indisponível (404), tenta o seguinte. Se a **chave** for recusada, para na hora e usa o plano B.

**Resposta em JSON.** O pedido usa `responseMimeType: application/json`. A resposta é limpa (remove cercas de código), interpretada e validada: atividades fora da lista viram `outro`, itens com horário inválido são descartados e é exigido o mínimo de 5 itens válidos.

**Plano B.** Qualquer falha (sem chave, sem internet, cota, resposta inválida) gera a rotina por regras (`gerar_rotina_basica`), marcada como `ia_fallback`. O site exibe o aviso "Gerada pelo modo automático" e o motivo.

**Limite de uso.** Cada usuário pode gerar até **10 rotinas com IA por hora** (configurável em `IA_LIMITE_HORA`), para proteger a cota gratuita.

**Diagnóstico.** `GET /api/ia/diagnostico` (também disponível como o link "Testar a conexão com a IA" na tela da IA) testa os modelos e explica em português o que está errado: chave ausente ou recusada, sem conexão, modelo indisponível ou cota esgotada.

**Privacidade.** O texto que o usuário digita na tela da IA é enviado ao Google. No plano gratuito, o Google pode usar o conteúdo para melhorar seus produtos. O site avisa o usuário para não incluir dados sensíveis.

## 8. API (referência)

Base: o mesmo endereço do site, caminho `/api`. Corpo e resposta em JSON. Rotas marcadas com 🔒 exigem `Authorization: Bearer <token>`. Erros: `{"erro": "mensagem"}` com o status HTTP adequado (400 dados inválidos, 401 não autenticado, 403 senha incorreta, 404 não encontrado, 409 e-mail já cadastrado, 429 muitas tentativas).

### Autenticação

| Método e rota | Corpo | Resposta |
|---|---|---|
| `POST /api/auth/cadastro` | `nome`, `sobrenome`, `idade` (10-120), `email`, `senha`, `confirmar_senha` | `201` com `token`, `usuario` e `codigo_recuperacao` (aparece **uma vez**) |
| `POST /api/auth/login` | `email`, `senha` | `200` com `token` e `usuario`. Após 5 erros, bloqueia aquele e-mail por 5 minutos (`429`) |
| 🔒 `GET /api/auth/me` | | dados do usuário |
| 🔒 `POST /api/auth/alterar-senha` | `senha_atual`, `nova_senha`, `confirmar_senha` | novo `token`; os tokens antigos deixam de valer |
| `POST /api/auth/recuperar` | `email`, `codigo`, `nova_senha`, `confirmar_senha` | novo `token` e **novo** `codigo_recuperacao`; o código usado deixa de valer |
| 🔒 `POST /api/auth/novo-codigo` | `senha` | novo `codigo_recuperacao` (o anterior deixa de valer) |
| 🔒 `DELETE /api/auth/conta` | `senha` | exclui a conta e todas as rotinas |

**Regras de senha:** 8 a 128 caracteres, com letras e números. A mensagem de erro de login é a mesma para e-mail inexistente e senha errada. O código de recuperação tem o formato `XXXX-XXXX-XXXX` (aceita minúsculas e espaços ao digitar).

### Rotinas e recomendações

| Método e rota | Corpo | Resposta |
|---|---|---|
| 🔒 `GET /api/atividades` | | lista de atividades e recomendações de sono/água para a idade do usuário |
| 🔒 `GET /api/modelos` | | modelos prontos (`id`, `nome`, `emoji`, `descricao`, `titulo`, `itens`) |
| 🔒 `POST /api/rotinas/manual` | `titulo`, `itens` | `201` com a rotina completa |
| 🔒 `POST /api/rotinas/ia` | `rotina_atual` (mín. 10 caracteres), `objetivos` (mín. 5), `acorda`, `dorme` (`HH:MM`); opcionais: `compromissos`, `peso` (20 a 400), `trabalho_inicio`, `trabalho_fim` | `201` com a rotina; `origem` é `ia` ou `ia_fallback`. Em fallback, vem `motivo_fallback`; com IA, vem `modelo_ia` |
| 🔒 `GET /api/rotinas` | | lista resumida (`id`, `titulo`, `origem`, `criado_em`) |
| 🔒 `GET /api/rotinas/<id>` | | rotina completa com `itens` e `avisos` |
| 🔒 `PUT /api/rotinas/<id>` | `titulo`, `itens` | rotina atualizada, com os avisos recalculados |
| 🔒 `DELETE /api/rotinas/<id>` | | confirmação |

**Formato de cada item:** `{"atividade": "sono", "inicio": "23:00", "fim": "07:00", "descricao": "texto"}`. No máximo 60 itens por rotina. Cada usuário só acessa as próprias rotinas (rotina de outro usuário responde `404`).

### Sistema

| Método e rota | Resposta |
|---|---|
| `GET /api/saude` | `{"status": "ok", "ia_configurada": true/false}` (útil para conferir a hospedagem) |
| 🔒 `GET /api/ia/diagnostico` | resultado do teste da IA, com `ok`, `mensagem` e, quando aplicável, a lista de modelos testados |

## 9. Front-end

Página única, sem framework. As telas:

| Tela | Endereço | O que faz |
|---|---|---|
| Início | `#/` | Apresenta o Sincro, passos de uso e perguntas frequentes |
| Cadastro | `#/cadastro` | Formulário com medidor de força da senha e confirmação; mostra o código de recuperação |
| Login | `#/login` | Entrar; link "Esqueci minha senha" |
| Esqueci a senha | `#/recuperar` | E-mail + código + nova senha |
| Painel | `#/painel` | Lista as rotinas (abrir, editar, apagar) e atalhos para criar |
| Rotina manual | `#/manual` | Modelos prontos e montagem linha a linha, com recomendações para a idade |
| Rotina com IA | `#/ia` | Formulário da IA, mensagens de espera e teste de conexão |
| Ver rotina | `#/rotina/<id>` | Barra de 24 h, avisos, linha do tempo, imprimir, editar, apagar |
| Editar rotina | `#/editar/<id>` | Altera título, horários e atividades |
| Minha conta | `#/conta` | Trocar senha, gerar novo código de recuperação, excluir conta |

Detalhes de comportamento:

- Páginas internas redirecionam para o login quando não há sessão; sessão expirada leva ao login com aviso.
- Os formulários validam no navegador **e** de novo no servidor.
- Erros da API aparecem na tela em português, sem recarregar a página.
- O layout se adapta ao celular; a impressão da rotina esconde menus e botões.
- As animações respeitam a preferência do sistema "reduzir movimento".

## 10. Segurança

| Tema | Como é tratado |
|---|---|
| Senhas | Guardadas só como hash (Werkzeug). Regras de tamanho e composição |
| Sessão | JWT assinado (HS256), validade de 7 dias, invalidado ao trocar/redefinir a senha |
| Força bruta | 5 erros de senha bloqueiam o e-mail por 5 minutos; a recuperação por código tem bloqueio igual |
| Enumeração de contas | Mesma mensagem para e-mail inexistente e senha errada; tempo de resposta equalizado com hash falso |
| Código de recuperação | Aleatório (`secrets`), guardado como hash, de uso único, renovável |
| Segredos | `.env` fora do Git (`.gitignore`); `SECRET_KEY` gerada automaticamente se faltar |
| Chave da IA | Fica só no servidor; enviada em cabeçalho, nunca em URL; nunca devolvida ao navegador |
| Injeção SQL | Todas as consultas usam parâmetros (`?`) |
| XSS | O front escapa os textos antes de exibi-los |
| Isolamento | Toda consulta de rotina filtra por `usuario_id` |
| Cabeçalhos | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Cache-Control: no-store` na API |
| Modo debug | Desligado por padrão (só liga com `FLASK_DEBUG=1`) |
| Cota da IA | Limite de gerações por usuário por hora |

## 11. Configuração (variáveis de ambiente)

Definidas no arquivo `.env` (modelo em `.env.example`):

| Variável | Para que serve | Padrão |
|---|---|---|
| `SECRET_KEY` | Assina os tokens de login | gerada automática em `.secret_key` |
| `GEMINI_API_KEY` | Chave da IA | vazio (usa o modo automático) |
| `GEMINI_MODEL` | Modelo(s) preferido(s), separados por vírgula | `gemini-3.8-flash` e reservas |
| `DB_PATH` | Caminho do banco | `sincro.db` na pasta do projeto |
| `IA_LIMITE_HORA` | Gerações de IA por usuário por hora | `10` |
| `FLASK_DEBUG` | `1` liga o modo debug (só no seu computador) | desligado |
| `PORT` | Porta ao rodar `python app.py` | `5000` |
| `DEMO_EMAIL` e `DEMO_SENHA` | Criam, a cada inicialização, uma conta de demonstração com uma rotina de exemplo (útil em hospedagem com disco temporário) | desligado |

## 12. Testes

`python test_api.py` executa mais de 50 verificações em um banco temporário, sem internet e sem chave de IA. A integração com o Gemini é testada com respostas simuladas (resposta correta, erro de chave, cota esgotada, modelo inexistente com troca para o próximo, JSON quebrado).

Cobertura: cadastro e validações, login e bloqueio, troca de senha e invalidação de tokens, recuperação de senha e novo código, rotas protegidas, rotina manual, modelos prontos, edição, listagem, exclusão, rotina com IA e plano B, limite de uso da IA, diagnóstico e exclusão de conta.

Os testes de tela (navegador) foram executados manualmente com automação, cobrindo cadastro, código de recuperação, modelos, edição, recuperação de senha, IA em modo automático, sessão expirada, rotas inexistentes e ausência de rolagem lateral no celular. Esses scripts não fazem parte do repositório.

## 13. Limitações conhecidas e melhorias futuras

**Limitações**

- Sem envio de e-mail: perder a senha **e** o código de recuperação impede recuperar a conta.
- A qualidade e a disponibilidade da IA dependem do plano gratuito do Gemini (limites baixos por modelo).
- O SQLite atende bem a um site pequeno; para muitos acessos simultâneos o ideal seria migrar para PostgreSQL.
- Não há painel de administração nem verificação de e-mail no cadastro.

**Melhorias futuras**

- Recuperação de senha por e-mail e confirmação de cadastro.
- Rotinas diferentes por dia da semana e lembretes por notificação.
- Exportar a rotina para PDF ou para o calendário do celular.
- Histórico de versões da rotina.
