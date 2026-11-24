# Guia passo a passo: GitHub, hospedagem e IA

Este guia leva o Sincro do seu computador até um site online, com a IA funcionando. Siga **na ordem**. Cada parte termina com uma checagem ("Deu certo se...") para você ter certeza de que pode avançar.

**Tempo estimado:** 1h30 a 2h na primeira vez.
**Custo:** R$ 0 (GitHub, PythonAnywhere e Google AI Studio têm planos gratuitos).

> **Regra de ouro:** o arquivo `.env` (que guarda a chave da IA) **nunca** vai para o GitHub e a chave nunca aparece em prints ou mensagens. Se vazar, veja a [seção 6](#6-se-algo-der-errado).

## Índice

1. [Antes de tudo: rodar e testar no seu computador](#1-antes-de-tudo-rodar-e-testar-no-seu-computador)
2. [Conseguir a chave da IA (Google Gemini)](#2-conseguir-a-chave-da-ia-google-gemini)
3. [Enviar o projeto para o GitHub](#3-enviar-o-projeto-para-o-github)
4. [Hospedar no PythonAnywhere](#4-hospedar-no-pythonanywhere)
   - [Alternativa: hospedar no Render](#4b-alternativa-hospedar-no-render-se-o-pythonanywhere-não-funcionar)
5. [Testar tudo online e checklist final](#5-testar-tudo-online-e-checklist-final)
6. [Se algo der errado](#6-se-algo-der-errado)
7. [Como atualizar o site depois](#7-como-atualizar-o-site-depois)

---

## 1. Antes de tudo: rodar e testar no seu computador

1. Extraia o `sincro.zip` (botão direito, **Extrair tudo**).
2. Dentro da pasta `sincro` (a que tem o `app.py`), clique na barra de endereço do Explorador, digite `cmd` e aperte Enter.
3. Rode, um de cada vez:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   python test_api.py
   python app.py
   ```
4. Abra **http://127.0.0.1:5000** no navegador.

**Deu certo se:** o `test_api.py` termina com "Tudo certo!" e o site abre, deixando você criar uma conta.

Se aparecer "python não é reconhecido", reinstale o Python em [python.org/downloads](https://www.python.org/downloads/) marcando **Add python.exe to PATH**.

---

## 2. Conseguir a chave da IA (Google Gemini)

1. Acesse [aistudio.google.com](https://aistudio.google.com) e entre com sua conta Google.
2. Procure **Get API key** (Obter chave de API) e clique em **Create API key** (Criar chave de API). Se pedir um projeto, escolha "Create API key in new project".
3. **Copie** a chave (um texto longo que começa com `AIza...`).
4. Na pasta do projeto, abra o arquivo `.env` com o Bloco de Notas e cole a chave:
   ```
   GEMINI_API_KEY=AIza...sua_chave_aqui
   ```
   Salve o arquivo. **Não coloque aspas e não deixe espaços.** Deixe `GEMINI_MODEL=` vazio (o Sincro escolhe o melhor modelo disponível sozinho).
5. No terminal, pare o servidor (`Ctrl + C`) e rode `python app.py` de novo.
6. No site, entre na sua conta, vá em **Nova com IA** e clique em **Testar a conexão com a IA**.

**Deu certo se:** aparece "✅ A IA está funcionando (modelo ...)". Depois faça uma rotina de teste: ela deve sair **sem** o selo "Modo automático".

**Se aparecer ⚠️,** a mensagem diz o motivo. Os mais comuns:

| Mensagem | O que fazer |
|---|---|
| A chave foi recusada | Gere outra chave no AI Studio e cole de novo no `.env` (sem aspas nem espaços) |
| GEMINI_API_KEY não configurada | A linha do `.env` está vazia, ou você não reiniciou o servidor |
| cota gratuita esgotada | O plano grátis tem limite por modelo. Espere um pouco; o Sincro tenta outros modelos sozinho |
| modelo não disponível para a sua chave | Normal em alguns modelos; o Sincro tenta o próximo. Se todos falharem, gere uma chave em um projeto novo |
| Não foi possível conectar ao Google | Sem internet, ou (em hospedagem) acesso bloqueado. Veja a seção 4 |

> **Atenção:** os limites do plano gratuito são baixos e o Google não os publica de forma fixa; no AI Studio dá para ver os seus. **Não fique testando a IA dezenas de vezes antes de apresentar**: guarde sua cota para a hora H. Se a cota acabar, o site continua funcionando no modo automático.

> **Privacidade:** no plano gratuito, o Google pode usar o texto enviado para melhorar seus produtos. Não escreva dados sensíveis nos testes.

---

## 3. Enviar o projeto para o GitHub

### 3.1 Preparar

1. Crie uma conta em [github.com](https://github.com) (se ainda não tiver).
2. Instale o Git: [git-scm.com/download/win](https://git-scm.com/download/win). Pode aceitar todas as opções padrão.
3. Feche e abra o `cmd` e confira: `git --version`.
4. Configure seu nome e e-mail (os mesmos do GitHub), uma vez só:
   ```
   git config --global user.name "Seu Nome"
   git config --global user.email "seu-email@exemplo.com"
   ```

### 3.2 Criar o repositório no site

1. No GitHub, clique em **+** (canto superior direito), depois em **New repository**.
2. **Repository name:** `sincro`.
3. Escolha **Public** (recomendado: facilita a hospedagem e a banca ver o código. O projeto não tem segredos no código).
4. **Não marque** "Add a README", nem `.gitignore`, nem licença (o projeto já tem os seus).
5. Clique em **Create repository**. Deixe a página aberta: ela mostra o endereço, algo como `https://github.com/SEU_USUARIO/sincro.git`.

### 3.3 Enviar

No `cmd`, dentro da pasta do projeto:

```
git init
git add .
git status
```

**PARE e confira a lista do `git status`.** Ela deve mostrar `app.py`, `static/`, `docs/`, `.env.example` etc. e **NÃO pode** mostrar:

- `.env` (só `.env.example` é permitido)
- `sincro.db` ou qualquer `.db`
- `.secret_key`
- a pasta `venv/`

Se algum aparecer, **não continue**: confira se o arquivo `.gitignore` está na pasta (ele é um arquivo oculto) e rode `git status` de novo.

Quando a lista estiver certa:

```
git commit -m "Primeira versão do Sincro"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/sincro.git
git push -u origin main
```

(Troque `SEU_USUARIO` pelo seu usuário do GitHub.) Na primeira vez, o Git abre uma janela do navegador pedindo para você entrar no GitHub: autorize.

**Deu certo se:** ao recarregar a página do repositório no GitHub, aparecem os arquivos e o README com as imagens. Confirme que **não há** `.env` na lista de arquivos.

### 3.4 Se você enviou o `.env` por engano

1. **Apague a chave imediatamente** no AI Studio (a chave exposta deve ser considerada comprometida) e crie outra.
2. Remova o arquivo do repositório e envie de novo:
   ```
   git rm --cached .env
   git commit -m "Remove .env"
   git push
   ```
3. Como o arquivo continua no histórico, a chave antiga já não vale mais (você apagou). Pela mesma razão, nunca reutilize a chave antiga.

---

## 4. Hospedar no PythonAnywhere

O PythonAnywhere hospeda Flask de graça, **mantém o arquivo do banco (SQLite)** e libera os domínios do Google (`.googleapis.com` está na lista permitida do plano grátis), então a IA consegue funcionar.

> **Sobre o plano grátis:** você tem 1 site no endereço `SEU_USUARIO.pythonanywhere.com`, com limites de uso de CPU. Para o plano grátis, o site precisa ser **renovado** periodicamente (aba Web, botão para estender; o serviço costuma avisar por e-mail). **Confira isso na véspera da apresentação.**

### 4.1 Criar a conta

1. Acesse [pythonanywhere.com](https://www.pythonanywhere.com) e clique em **Pricing & signup**, depois **Create a Beginner account**.
2. Escolha o **nome de usuário** com cuidado: ele vira o endereço do site (`SEU_USUARIO.pythonanywhere.com`). Confirme o e-mail.

### 4.2 Baixar o projeto no servidor

1. No painel, aba **Consoles**, clique em **Bash** (abre um terminal).
2. Rode (trocando pelo seu usuário do GitHub):
   ```
   git clone https://github.com/SEU_USUARIO/sincro.git
   cd sincro
   ```
   Se o repositório for **privado**, o clone pede login; é mais simples deixar o repositório público ou, como alternativa, enviar o zip pela aba **Files** (Upload a file) e rodar `unzip sincro.zip` no console.

### 4.3 Criar o ambiente virtual e instalar

No mesmo console:
```
mkvirtualenv sincro-venv --python=python3.12
pip install -r requirements.txt
```
Se der erro de versão, tente `python3.11` ou `python3.10` (use uma versão 3.10 ou superior disponível no PythonAnywhere). **Anote qual versão usou**: você vai escolher a mesma na aba Web.

### 4.4 Configurar o `.env` no servidor

```
cp .env.example .env
nano .env
```

No editor `nano`, preencha:

```
SECRET_KEY=cole_aqui_um_texto_aleatorio_longo
GEMINI_API_KEY=AIza...sua_chave_aqui
GEMINI_MODEL=
```

Para gerar o `SECRET_KEY`, abra outra aba do console e rode `python -c "import secrets; print(secrets.token_hex(32))"`, depois copie o resultado. Para salvar no `nano`: `Ctrl + O`, `Enter`, `Ctrl + X`.

### 4.5 Criar o site (aba Web)

1. Vá na aba **Web** e clique em **Add a new web app**. Clique em **Next**.
2. Escolha **Manual configuration** (⚠️ **não** escolha "Flask"). Escolha a **mesma versão do Python** do passo 4.3. Clique em **Next**.
3. Na página do site, role até a seção **Virtualenv** e digite:
   ```
   /home/SEU_USUARIO/.virtualenvs/sincro-venv
   ```
4. Na seção **Code**, preencha:
   - **Source code:** `/home/SEU_USUARIO/sincro`
   - **Working directory:** `/home/SEU_USUARIO/sincro`
5. Ainda em **Code**, clique no link do **WSGI configuration file**. **Apague todo o conteúdo** e cole:
   ```python
   import sys

   path = "/home/SEU_USUARIO/sincro"
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```
   Troque `SEU_USUARIO` pelo seu usuário. Clique em **Save**.
6. Volte para a aba **Web** e clique no botão verde **Reload**.

### 4.6 Conferir

Abra `https://SEU_USUARIO.pythonanywhere.com/api/saude` no navegador.

**Deu certo se:** aparece `{"ia_configurada": true, "status": "ok"}`. Em seguida abra `https://SEU_USUARIO.pythonanywhere.com` e o site deve carregar.

**Se aparecer erro:** na aba **Web**, abra o **Error log** (link na seção "Log files"). A última mensagem do arquivo diz o problema. Veja a [seção 6](#6-se-algo-der-errado).

---

## 4B. Alternativa: hospedar no Render (se o PythonAnywhere não funcionar)

O Render hospeda Flask de graça e publica direto do GitHub. **Atenção ao limite:** no plano grátis o disco é **temporário**. O banco de dados (SQLite) é apagado quando o servidor reinicia, quando você publica uma nova versão e quando ele "dorme" (após 15 minutos sem acesso). Ou seja, **contas e rotinas criadas por visitantes somem**. Para a apresentação isso é contornável: o Sincro recria sozinho uma **conta de demonstração** toda vez que o servidor liga (passo 5).

Outros limites do plano grátis: depois de ficar parado, o primeiro acesso leva cerca de **1 minuto** para acordar, e o Render pode reiniciar o serviço a qualquer momento.

**Pré-requisito:** o projeto já está no GitHub (seção 3).

1. Acesse [render.com](https://render.com) e crie a conta com **Sign up with GitHub**. Autorize o acesso ao repositório `sincro`.
2. No painel, clique em **New +** e depois em **Web Service**. Escolha o repositório `sincro` e clique em **Connect**.
3. Preencha:
   - **Name:** `sincro` (vira o endereço `sincro.onrender.com` ou parecido)
   - **Language/Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --timeout 120 --workers 1 --threads 4`
   - **Instance Type:** `Free`
4. Role até **Environment Variables** e adicione uma por uma:

   | Nome | Valor |
   |---|---|
   | `PYTHON_VERSION` | `3.12.3` |
   | `SECRET_KEY` | um texto aleatório longo (gere com `python -c "import secrets; print(secrets.token_hex(32))"`) |
   | `GEMINI_API_KEY` | sua chave `AIza...` |
   | `DEMO_EMAIL` | `demo@sincro.com` (ou outro e-mail) |
   | `DEMO_SENHA` | uma senha com 8+ caracteres, com letras e números (ex.: `Demo12345`) |

   O `SECRET_KEY` **é obrigatório aqui**: sem ele, o servidor gera uma chave nova a cada reinício e derruba todos os logins.
5. Clique em **Create Web Service** e aguarde o build (2 a 3 minutos). O painel mostra os logs; quando aparecer "Live", está no ar.
6. Abra `https://SEU-SERVICO.onrender.com/api/saude`. Deve aparecer `"status": "ok"` e, se a chave foi lida, `"ia_configurada": true`.
7. Abra o site e entre com a **conta de demonstração** (`DEMO_EMAIL` e `DEMO_SENHA`). Ela já vem com uma rotina de exemplo. Teste a IA em **Nova com IA > Testar a conexão com a IA**.

**Dicas para a apresentação**

- **Acorde o site antes:** abra o endereço uns 5 a 10 minutos antes de apresentar e deixe a aba aberta.
- **Use a conta de demonstração.** Contas criadas na hora podem sumir se o servidor reiniciar.
- Se quiser **evitar que ele durma**, um serviço gratuito de monitoramento (como o UptimeRobot) pode acessar `/api/saude` a cada poucos minutos. Isso consome suas horas gratuitas mensais, então use só perto da apresentação.
- Tenha o plano B: o site rodando no seu notebook (`python app.py`).

**Para atualizar:** faça `git push` e o Render publica sozinho. Lembre que cada publicação apaga o banco (a conta demo é recriada).

**Se der erro:** abra a aba **Logs** do serviço. Se o build falhar, confira o **Build Command**; se o site não abrir, confira o **Start Command** e se `SECRET_KEY` e `PYTHON_VERSION` foram salvos.

---

## 5. Testar tudo online e checklist final

Faça este roteiro **no site online** (preferencialmente também pelo celular):

- [ ] Criar uma conta nova e **anotar o código de recuperação**
- [ ] Sair e entrar de novo com e-mail e senha
- [ ] Testar um login com senha errada (deve avisar, sem travar)
- [ ] Em **Nova manual**, escolher um modelo pronto e salvar
- [ ] Abrir a rotina, clicar em **Editar**, mudar algo e salvar
- [ ] Em **Nova com IA**, clicar em **Testar a conexão com a IA** (deve dar ✅)
- [ ] Gerar uma rotina com IA (sem o selo "Modo automático")
- [ ] **Esqueci minha senha**: redefinir usando o código
- [ ] Imprimir uma rotina e apagar uma rotina
- [ ] Abrir o site no celular

### Antes da apresentação

- [ ] **Crie uma conta de demonstração** e anote e-mail, senha e código de recuperação em um papel
- [ ] Deixe algumas rotinas já criadas nessa conta (assim o painel não aparece vazio)
- [ ] Renove o site na aba Web do PythonAnywhere (ver 4)
- [ ] Teste a IA **uma vez** no dia anterior e depois poupe a cota
- [ ] **Plano B de apresentação:** deixe o site rodando também no seu notebook (`python app.py`, endereço `127.0.0.1:5000`), caso a internet do local falhe
- [ ] Confira que o `.env` e a chave **não** aparecem no GitHub nem em prints

---

## 6. Se algo der errado

| Sintoma | Causa provável | Solução |
|---|---|---|
| `{"ia_configurada": false}` online | `.env` ausente ou sem a chave no servidor | Edite o `.env` na pasta `sincro` do PythonAnywhere e clique em **Reload** |
| "Something went wrong" / erro 500 | Erro no código ou instalação | Aba Web, **Error log**: leia a última mensagem |
| `ModuleNotFoundError` no log | Ambiente virtual errado ou dependências não instaladas | Confira o caminho do **Virtualenv** na aba Web e rode `pip install -r requirements.txt` dentro dele |
| Página em branco ou "Not Found" | Caminho do **Source code**/WSGI errado | Confira `SEU_USUARIO` no caminho e no arquivo WSGI |
| IA sempre no modo automático online | Chave ausente/inválida ou cota esgotada | Use **Testar a conexão com a IA** e siga a mensagem |
| "Não foi possível conectar ao Google" online | Bloqueio de rede do plano grátis | Confirme que usa o PythonAnywhere (ele libera `.googleapis.com`); se ainda assim bloquear, é possível pedir liberação ao suporte ou usar uma conta paga |
| Mudei o código e nada mudou | Faltou recarregar | Aba Web, botão **Reload** |
| Login some ao recarregar a página | Navegador bloqueando armazenamento (aba anônima) | Use uma janela normal |
| Mensagem de 429 / "muitas tentativas" | Limite de segurança (5 erros) | Aguarde 5 minutos |

**Se a chave da IA vazou** (apareceu em print, no GitHub ou em mensagem): entre no AI Studio, **apague** essa chave, crie outra e atualize o `.env` (no computador e no servidor).

---

## 7. Como atualizar o site depois

1. No computador, altere o código e teste (`python app.py`).
2. Envie para o GitHub:
   ```
   git add .
   git commit -m "Descreva a mudança"
   git push
   ```
3. No console Bash do PythonAnywhere:
   ```
   cd ~/sincro
   git pull
   ```
   Se você adicionou dependências novas: `workon sincro-venv` e `pip install -r requirements.txt`.
4. Na aba **Web**, clique em **Reload**.

O banco de dados (`sincro.db`) **não** é enviado ao GitHub e fica só no servidor, então as contas e rotinas existentes são preservadas nas atualizações. Para fazer uma cópia de segurança, baixe o arquivo `sincro.db` pela aba **Files** do PythonAnywhere.
