/* Sincro — front-end (SPA simples com rotas por hash: #/login, #/painel ...) */
const $ = (s, r = document) => r.querySelector(s);
const app = $("#app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const ATIV = {
  sono: ["😴", "Sono", "#6366f1"], alimentacao: ["🥗", "Alimentação", "#16a34a"], hidratacao: ["💧", "Hidratação", "#0ea5e9"],
  musculacao: ["🏋️", "Musculação", "#ef4444"], trabalho: ["💼", "Trabalho", "#64748b"], estudo: ["📚", "Estudo", "#f59e0b"],
  lazer: ["🎮", "Lazer", "#ec4899"], outro: ["⭐", "Outro", "#8b5cf6"],
};
const PRESETS = { sono: ["23:00", "07:00"], alimentacao: ["07:30", "08:00"], hidratacao: ["09:00", "09:05"], musculacao: ["18:00", "19:00"],
  trabalho: ["09:00", "17:00"], estudo: ["19:30", "21:00"], lazer: ["21:00", "22:00"], outro: ["15:00", "15:30"] };

let usuario = null;

/* ---------- utilidades ---------- */
function toast(msg, erro = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast on" + (erro ? " erro" : "");
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.className = "toast"), 4200);
}
function carregando(ligar, titulo = "Carregando…", texto = "") {
  $("#carregando").hidden = !ligar; $("#car-titulo").textContent = titulo; $("#car-texto").textContent = texto;
}
const min = h => { const [a, b] = h.split(":"); return +a * 60 + +b; };
function partes(i, f) { const a = min(i), b = min(f); return b > a ? [[a, b]] : b === 0 ? [[a, 1440]] : [[a, 1440], [0, b]]; }
const dataBR = s => new Date(s.replace(" ", "T") + "Z").toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
const ir = h => { location.hash = h; };
function selo(o) { return o === "manual" ? '<span class="selo">Manual</span>' : o === "ia" ? '<span class="selo ia">✨ IA</span>' : '<span class="selo fb">Modo automático</span>'; }

/* ---------- topo ---------- */
function renderTopo() {
  const logado = Sincro.estaLogado();
  $("#topo").innerHTML = `
    <a class="marca" href="#/${logado ? "painel" : ""}" aria-label="Sincro — início"><img class="ic" src="img/livro.png" alt=""><img class="lt" src="img/letreiro.png" alt="Sincro"></a>
    <nav>${logado
      ? `<span class="ola">Olá, ${esc(usuario?.nome || "")}!</span><a href="#/painel">Minhas rotinas</a><a class="opc" href="#/manual">Nova manual</a><a class="opc" href="#/ia">Nova com IA</a><a href="#/conta">Minha conta</a><button id="sair">Sair</button>`
      : `<a href="#/login">Entrar</a><a href="#/cadastro" class="btn peq" style="color:#fff">Criar conta</a>`}</nav>`;
  const s = $("#sair"); if (s) s.onclick = () => { Sincro.sair(); usuario = null; toast("Você saiu da conta."); ir("#/"); };
}

/* ---------- animações e utilidades ---------- */
function animar() {
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return; e.target.classList.add("on"); io.unobserve(e.target);
    e.target.querySelectorAll("[data-count]").forEach(contar);
  }), { threshold: 0.15 });
  document.querySelectorAll(".rev").forEach(el => io.observe(el));
}
function contar(el) {
  const alvo = +el.dataset.count, t0 = performance.now();
  (function passo(t) { const k = Math.min((t - t0) / 1400, 1); el.textContent = Math.round(alvo * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(passo); })(t0);
}
function confete() {
  const cores = ["#7c3aed", "#c4b5fd", "#22c55e", "#f59e0b", "#ec4899", "#0ea5e9"];
  for (let n = 0; n < 40; n++) {
    const c = document.createElement("i"); c.className = "confete";
    c.style.cssText = `left:${Math.random() * 100}vw;background:${cores[n % 6]};animation-delay:${Math.random() * .6}s;--dx:${(Math.random() - .5) * 220}px;--rot:${Math.random() * 720}deg`;
    document.body.appendChild(c); setTimeout(() => c.remove(), 3200);
  }
}
const reNome = /^[A-Za-zÀ-ÿ' -]{2,50}$/;
const senhaErro = s => s.length < 8 ? "A senha precisa ter pelo menos 8 caracteres." : !(/[A-Za-z]/.test(s) && /\d/.test(s)) ? "A senha deve conter letras e números." : "";
const forca = s => (s.length >= 8) + (/[A-Za-z]/.test(s) && /\d/.test(s)) + (s.length >= 12) + (/[^A-Za-z0-9]/.test(s) && s.length >= 8);
const ROT = ["Muito fraca", "Fraca", "Média", "Boa", "Forte"];
function senhaBox(id, rotulo, auto, medidor = false) {
  return `<div class="campo"><label for="${id}">${rotulo}</label><div class="senha-box"><input id="${id}" type="password" autocomplete="${auto}" required>
    <button type="button" class="olho" data-olho="${id}" aria-label="Mostrar senha">👁</button></div>
    ${medidor ? `<div class="medidor" id="m-${id}"><div class="barras"><i></i><i></i><i></i><i></i></div><small></small></div><div class="dica">Mínimo de 8 caracteres, com letras e números.</div>` : ""}</div>`;
}
function ligarSenhas() {
  app.querySelectorAll("[data-olho]").forEach(b => b.onclick = () => {
    const i = $("#" + b.dataset.olho), v = i.type === "password"; i.type = v ? "text" : "password"; b.textContent = v ? "🙈" : "👁"; b.setAttribute("aria-label", v ? "Ocultar senha" : "Mostrar senha");
  });
  app.querySelectorAll(".medidor").forEach(m => { const i = $("#" + m.id.slice(2)); i.addEventListener("input", () => {
    const p = i.value ? forca(i.value) : 0; m.dataset.p = p; m.querySelectorAll("i").forEach((b, n) => b.classList.toggle("on", !!i.value && n < p)); m.querySelector("small").textContent = i.value ? ROT[p] : ""; }); });
}
function alerta(msg, form = "#f") {
  const m = $("#msg"); m.textContent = msg; m.hidden = !msg; const f = $(form);
  f.classList.remove("shake"); if (msg) { void f.offsetWidth; f.classList.add("shake"); }
}

/* ---------- código de recuperação ---------- */
function mostrarCodigo(codigo, titulo, depois) {
  const m = document.createElement("div"); m.className = "overlay modal";
  m.innerHTML = `<div class="overlay-caixa codigo-caixa" role="dialog" aria-modal="true" aria-labelledby="cod-t"><div class="cod-ico">🔑</div><h3 id="cod-t">${esc(titulo)}</h3>
    <p>Este é o seu <b>código de recuperação</b>. Se você esquecer a senha, é com ele que vai voltar para a conta. Ele só aparece agora, então guarde em um lugar seguro.</p>
    <div class="cod-valor" id="cod-v">${esc(codigo)}</div>
    <div class="cod-acoes"><button class="btn sec peq" id="cod-c">📋 Copiar</button><button class="btn sec peq" id="cod-b">⬇ Baixar .txt</button></div>
    <label class="cod-ok"><input type="checkbox" id="cod-chk"> Já guardei o meu código</label>
    <button class="btn bloco" id="cod-f" disabled>Continuar</button></div>`;
  document.body.appendChild(m);
  $("#cod-c").onclick = async () => { try { await navigator.clipboard.writeText(codigo); toast("Código copiado!"); } catch { toast("Selecione o código e copie manualmente.", true); } };
  $("#cod-b").onclick = () => { const u = URL.createObjectURL(new Blob([`Sincro - código de recuperação de senha\n\n${codigo}\n\nGuarde em local seguro. Não compartilhe.\n`], { type: "text/plain" }));
    const l = document.createElement("a"); l.href = u; l.download = "sincro-codigo-recuperacao.txt"; l.click(); URL.revokeObjectURL(u); };
  $("#cod-chk").onchange = e => { $("#cod-f").disabled = !e.target.checked; };
  $("#cod-f").onclick = () => { m.remove(); depois && depois(); };
}

/* ---------- telas ---------- */
function telaInicio() {
  const palavras = ["tempo", "saúde", "foco", "energia", "descanso"]; let k = 0;
  app.innerHTML = `
  <section class="hero"><div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
    ${Array.from({ length: 14 }, (_, n) => `<i class="pt" style="left:${(n * 7.3) % 100}%;animation-delay:${n * .7}s;animation-duration:${9 + n % 5}s"></i>`).join("")}
    <div class="wrap"><div class="hero-txt"><span class="etiqueta">✨ Rotina inteligente</span>
      <h1>Menos correria.<br>Mais <span class="grad" id="palavra">tempo</span> para o que importa.</h1>
      <p class="lead">O Sincro organiza o seu dia em uma rotina saudável de sono, alimentação, hidratação e treino. Monte do seu jeito ou deixe a inteligência artificial fazer isso por você.</p>
      <div class="acoes"><a class="btn" href="#/cadastro">Começar agora</a><a class="btn sec" href="#/login">Já tenho conta</a></div></div>
      <div class="hero-vis"><img class="livro" src="img/livro.png" alt="Caderno do Sincro com um check">
        <span class="flut f1">😴 Sono · 8h</span><span class="flut f2">💧 Água · 2,4 L</span><span class="flut f3">🏋️ Treino · 18h</span><span class="flut f4">🥗 Refeições ✓</span></div></div></section>
  <section class="secao faixa"><div class="wrap"><div class="stats rev">
    <div><b data-count="24">0</b><small>h</small><span>organizadas em uma linha do tempo</span></div><div><b data-count="8">0</b><span>tipos de atividade para planejar</span></div>
    <div><b data-count="35">0</b><small>ml/kg</small><span>meta de água usada como referência</span></div><div><b data-count="5">0</b><small>×</small><span>lembretes de água por dia, no mínimo</span></div></div></div></section>
  <section class="secao"><div class="wrap"><h2 class="rev">Tudo para o seu dia render mais</h2>
    <p class="sub rev">A pobreza de tempo é a sensação de nunca ter tempo suficiente. O Sincro ajuda você a enxergar o seu dia e a usá-lo melhor.</p>
    <div class="grade3">${[["✍️", "Rotina manual", "Escolha cada atividade e horário. Você no controle de tudo."], ["✨", "Rotina com IA", "Conte como é seu dia e o que quer melhorar. A IA monta o resto."],
      ["⚠️", "Avisos de saúde", "Pouco sono, refeições faltando ou horários em conflito? O Sincro avisa."], ["📊", "Linha do tempo de 24h", "Veja o dia inteiro em uma barra colorida e em uma lista clara."],
      ["💧", "Hidratação", "Lembretes de água distribuídos ao longo do dia, com meta por peso."], ["🎂", "Pensado para a sua idade", "As recomendações de sono mudam conforme a sua faixa etária."]]
      .map(([i, t, d], n) => `<div class="card rec-card rev" style="--i:${n}"><div class="ico-c">${i}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}</div></div></section>
  <section class="secao faixa"><div class="wrap duas-v"><div class="rev"><h2 style="text-align:left">Seu dia, de relance</h2>
    <p class="sub" style="text-align:left;margin-left:0">Cada atividade ganha uma cor. Em um olhar você vê onde o tempo está indo.</p><a class="btn" href="#/cadastro">Criar minha rotina</a></div>
    <div class="card rev demo"><b>Exemplo de rotina</b><div class="dia" style="margin-top:.7rem">${[[0, 29, "#6366f1"], [30, 33, "#16a34a"], [37.5, 33.3, "#64748b"], [53, 4.5, "#16a34a"], [75, 4.2, "#ef4444"], [83.3, 2.8, "#16a34a"], [95.8, 4.2, "#6366f1"]]
      .map(([l, w, c], n) => `<div class="seg" style="--i:${n};left:${l}%;width:${w}%;background:${c}"></div>`).join("")}</div>
      <div class="eixo"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>24h</span></div>
      <div class="legenda"><span><i style="background:#6366f1"></i>Sono</span><span><i style="background:#16a34a"></i>Refeições</span><span><i style="background:#64748b"></i>Trabalho</span><span><i style="background:#ef4444"></i>Treino</span></div></div></div></section>
  <section class="secao"><div class="wrap"><h2 class="rev">Como funciona</h2><div class="passos">${[["Crie sua conta", "Informe nome, sobrenome e idade. A idade ajusta as recomendações de sono."],
      ["Escolha o modo", "Manual, com horários definidos por você, ou com IA, a partir do seu relato."], ["Receba sua rotina", "Linha do tempo do dia e avisos de saúde, prontos para seguir ou imprimir."]]
      .map(([t, d], n) => `<div class="passo rev" style="--i:${n}"><div class="num">${n + 1}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}</div></div></section>
  <section class="secao faixa"><div class="wrap" style="max-width:760px"><h2 class="rev">Perguntas frequentes</h2><div class="faq rev">
    <details><summary>Como a IA monta a minha rotina?</summary><p>Você descreve o dia atual e o que quer melhorar. A IA considera os seus horários e as recomendações de sono, alimentação, hidratação e treino para a sua idade.</p></details>
    <details><summary>Meus dados estão seguros?</summary><p>Sua senha é guardada com criptografia (nunca em texto puro), o acesso é protegido por login e você pode trocar a senha ou excluir a conta quando quiser.</p></details>
    <details><summary>O Sincro substitui um profissional de saúde?</summary><p>Não. As sugestões são orientações gerais. Para necessidades específicas, procure um médico, nutricionista ou educador físico.</p></details>
    <details><summary>Esqueci minha senha. E agora?</summary><p>Ao criar a conta você recebe um código de recuperação. Na tela de login, clique em “Esqueci minha senha”, informe o e-mail, o código e escolha uma nova senha. Guarde o código em um lugar seguro; dentro da conta você pode gerar um novo.</p></details>
    <details><summary>Posso editar uma rotina depois de criada?</summary><p>Sim. No painel, clique em Editar para mudar o nome, os horários e as atividades quando quiser. Você também pode imprimir ou apagar a rotina.</p></details></div></div></section>
  <section class="cta"><div class="wrap rev"><h2>Pronto para ganhar tempo?</h2><p>Crie sua conta e monte sua primeira rotina em minutos.</p><a class="btn" href="#/cadastro">Criar minha conta</a></div></section>
  <footer class="rodape">© 2026 Sincro · Organize seu dia, ganhe tempo.<br><small>As recomendações são gerais e não substituem a orientação de profissionais de saúde.</small></footer>`;
  const el = $("#palavra"); window.__rot = setInterval(() => { el.classList.add("troca"); setTimeout(() => { k = (k + 1) % palavras.length; el.textContent = palavras[k]; el.classList.remove("troca"); }, 350); }, 2600);
}

function telaAuth(modo) {
  const cad = modo === "cadastro";
  app.innerHTML = `<div class="auth"><div class="lado" role="img" aria-label="Logo do Sincro"><div class="brilho"></div></div>
  <div class="form"><div>
    <h1>${cad ? "Crie sua conta" : "Bem-vindo de volta"}</h1>
    <p class="sub" style="color:var(--mut)">${cad ? "Leva menos de um minuto." : "Entre para ver suas rotinas."}</p>
    <form id="f" novalidate><div id="msg" class="alerta" role="alert" hidden></div>
      ${cad ? `<div class="lin2"><div class="campo"><label for="nome">Nome</label><input id="nome" autocomplete="given-name" maxlength="50" required></div>
        <div class="campo"><label for="sobrenome">Sobrenome</label><input id="sobrenome" autocomplete="family-name" maxlength="50" required></div></div>
        <div class="campo"><label for="idade">Idade</label><input id="idade" type="number" min="10" max="120" step="1" inputmode="numeric" required></div>` : ""}
      <div class="campo"><label for="email">E-mail</label><input id="email" type="email" autocomplete="email" maxlength="120" required></div>
      ${senhaBox("senha", "Senha", cad ? "new-password" : "current-password", cad)}
      ${cad ? senhaBox("conf", "Confirmar senha", "new-password") : ""}
      <button class="btn bloco" id="enviar">${cad ? "Criar conta" : "Entrar"}</button>
      ${cad ? "" : '<p class="esq"><a href="#/recuperar">Esqueci minha senha</a></p>'}
    </form>
    <p style="margin-top:1.2rem">${cad ? 'Já tem conta? <a href="#/login">Entrar</a>' : 'Novo por aqui? <a href="#/cadastro">Criar conta</a>'}</p>
  </div></div></div>`;
  ligarSenhas();
  $("#f").onsubmit = async e => {
    e.preventDefault(); alerta("");
    const v = id => ($("#" + id)?.value ?? "");
    if (cad) {
      if (!reNome.test(v("nome").trim()) || !reNome.test(v("sobrenome").trim())) return alerta("Informe nome e sobrenome válidos (apenas letras).");
      const idade = Number(v("idade")); if (!Number.isInteger(idade) || idade < 10 || idade > 120) return alerta("Informe uma idade entre 10 e 120 anos.");
    }
    if (!$("#email").checkValidity() || !v("email").trim()) return alerta("Informe um e-mail válido.");
    if (cad) { const se = senhaErro(v("senha")); if (se) return alerta(se); if (v("senha") !== v("conf")) return alerta("As senhas não coincidem."); }
    else if (!v("senha")) return alerta("Informe a sua senha.");
    const b = $("#enviar"); b.disabled = true; b.classList.add("carrega");
    try {
      usuario = cad
        ? await Sincro.cadastrar({ nome: v("nome").trim(), sobrenome: v("sobrenome").trim(), idade: Number(v("idade")), email: v("email").trim(), senha: v("senha"), confirmar_senha: v("conf") })
        : await Sincro.entrar(v("email").trim(), v("senha"));
      if (cad) { const cod = usuario.codigo_recuperacao; delete usuario.codigo_recuperacao; renderTopo(); mostrarCodigo(cod, "Conta criada! 🎉", () => { toast("Bem-vindo ao Sincro."); ir("#/painel"); }); return; }
      toast(`Bem-vindo, ${usuario.nome}!`); ir("#/painel");
    } catch (err) { alerta(err.message); b.disabled = false; b.classList.remove("carrega"); }
  };
}

function telaRecuperar() {
  app.innerHTML = `<div class="auth"><div class="lado" role="img" aria-label="Logo do Sincro"><div class="brilho"></div></div>
  <div class="form"><div><h1>Esqueci minha senha</h1>
    <p class="sub" style="color:var(--mut)">Informe o e-mail, o código de recuperação que você recebeu ao criar a conta e escolha uma nova senha.</p>
    <form id="f" novalidate><div id="msg" class="alerta" role="alert" hidden></div>
      <div class="campo"><label for="email">E-mail</label><input id="email" type="email" autocomplete="email" maxlength="120" required></div>
      <div class="campo"><label for="cod">Código de recuperação</label><input id="cod" class="mono" maxlength="20" placeholder="XXXX-XXXX-XXXX" autocomplete="off" spellcheck="false" required></div>
      ${senhaBox("nova", "Nova senha", "new-password", true)}${senhaBox("conf", "Confirmar nova senha", "new-password")}
      <button class="btn bloco" id="enviar">Redefinir senha</button></form>
    <p style="margin-top:1.2rem"><a href="#/login">← Voltar para o login</a></p>
    <p class="dica">Perdeu o código também? Sem envio de e-mail, não há como recuperar a conta; crie uma nova conta.</p></div></div></div>`;
  ligarSenhas();
  $("#cod").addEventListener("input", e => { const v = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12); e.target.value = v.match(/.{1,4}/g)?.join("-") || ""; });
  $("#f").onsubmit = async e => {
    e.preventDefault(); alerta("");
    if (!$("#email").checkValidity() || !$("#email").value.trim()) return alerta("Informe um e-mail válido.");
    if ($("#cod").value.replace(/-/g, "").length !== 12) return alerta("O código tem 12 caracteres (XXXX-XXXX-XXXX).");
    const se = senhaErro($("#nova").value); if (se) return alerta(se); if ($("#nova").value !== $("#conf").value) return alerta("As senhas não coincidem.");
    const b = $("#enviar"); b.disabled = true; b.classList.add("carrega");
    try {
      usuario = await Sincro.recuperarSenha({ email: $("#email").value.trim(), codigo: $("#cod").value, nova_senha: $("#nova").value, confirmar_senha: $("#conf").value });
      const cod = usuario.codigo_recuperacao; delete usuario.codigo_recuperacao; renderTopo();
      mostrarCodigo(cod, "Senha redefinida! ✅", () => { toast(`Bem-vindo de volta, ${usuario.nome}!`); ir("#/painel"); });
    } catch (err) { alerta(err.message); b.disabled = false; b.classList.remove("carrega"); }
  };
}

function telaConta() {
  const ini = (usuario.nome[0] + usuario.sobrenome[0]).toUpperCase();
  app.innerHTML = `<div class="pag"><div class="wrap" style="max-width:760px"><h1>Minha conta</h1>
    <div class="card perfil"><div class="avatar">${esc(ini)}</div><div><b>${esc(usuario.nome)} ${esc(usuario.sobrenome)}</b><br><span class="sub">${esc(usuario.email)} · ${usuario.idade} anos</span></div></div>
    <form class="card" id="fs" novalidate style="margin-top:1rem"><h3>Alterar senha</h3><div id="msg" class="alerta" role="alert" hidden></div>
      ${senhaBox("atual", "Senha atual", "current-password")}${senhaBox("nova", "Nova senha", "new-password", true)}${senhaBox("conf", "Confirmar nova senha", "new-password")}
      <button class="btn" id="bs">Salvar nova senha</button></form>
    <form class="card" id="fc" novalidate style="margin-top:1rem"><h3>Código de recuperação</h3>
      <p class="sub">Usado em “Esqueci minha senha”. Gerar um novo invalida o anterior. Digite sua senha para confirmar.</p>
      ${senhaBox("sc", "Sua senha", "current-password")}<button class="btn sec">Gerar novo código</button></form>
    <form class="card zona" id="fx" novalidate style="margin-top:1rem"><h3>Excluir conta</h3><p class="sub">Apaga sua conta e todas as suas rotinas de forma permanente.</p>
      ${senhaBox("sx", "Digite sua senha para confirmar", "current-password")}<button class="btn perigo">Excluir minha conta</button></form></div></div>`;
  ligarSenhas();
  $("#fs").onsubmit = async e => {
    e.preventDefault(); alerta("", "#fs"); const nv = $("#nova").value;
    if (!$("#atual").value) return alerta("Informe a senha atual.", "#fs");
    if (senhaErro(nv)) return alerta(senhaErro(nv), "#fs"); if (nv !== $("#conf").value) return alerta("As senhas não coincidem.", "#fs");
    const b = $("#bs"); b.disabled = true;
    try { await Sincro.alterarSenha($("#atual").value, nv, $("#conf").value); toast("Senha alterada com sucesso!"); telaConta(); }
    catch (err) { alerta(err.message, "#fs"); b.disabled = false; }
  };
  $("#fc").onsubmit = async e => {
    e.preventDefault(); if (!$("#sc").value) return toast("Digite a sua senha para gerar o código.", true);
    try { const r = await Sincro.novoCodigo($("#sc").value); $("#sc").value = ""; mostrarCodigo(r.codigo_recuperacao, "Novo código gerado 🔑"); } catch (err) { toast(err.message, true); }
  };
  $("#fx").onsubmit = async e => {
    e.preventDefault(); if (!$("#sx").value) return toast("Digite a senha para confirmar.", true);
    if (!confirm("Tem certeza? Esta ação não pode ser desfeita.")) return;
    try { await Sincro.excluirConta($("#sx").value); usuario = null; toast("Conta excluída."); ir("#/"); } catch (err) { toast(err.message, true); }
  };
}

async function telaPainel() {
  app.innerHTML = `<div class="pag"><div class="wrap"><h1>Olá, ${esc(usuario.nome)}! 👋</h1><p class="sub">O que vamos organizar hoje?</p>
    <div class="acoes2">
      <a class="acao" href="#/manual"><div class="ico">✍️</div><h3>Montar manualmente</h3><p>Escolha atividades e horários do seu jeito e receba avisos de saúde.</p></a>
      <a class="acao ia" href="#/ia"><div class="ico">✨</div><h3>Montar com IA</h3><p>Conte sua rotina atual e o que quer melhorar. A IA monta o dia completo.</p></a></div>
    <h2>Minhas rotinas</h2><div class="lista" id="lista"><div class="sk"></div><div class="sk"></div></div></div></div>`;
  try {
    const l = await Sincro.listarRotinas();
    $("#lista").innerHTML = l.length ? l.map(r => `<div class="it"><div><b>${esc(r.titulo)} ${selo(r.origem)}</b><small>Criada em ${dataBR(r.criado_em)}</small></div>
      <div><a class="btn sec peq" href="#/rotina/${r.id}">Abrir</a> <a class="btn sec peq" href="#/editar/${r.id}">Editar</a> <button class="btn perigo peq" data-del="${r.id}">Apagar</button></div></div>`).join("")
      : `<div class="vazio"><img src="img/livro.png" alt=""><p>Você ainda não tem nenhuma rotina.<br>Crie a primeira acima!</p></div>`;
    $("#lista").onclick = async e => {
      const id = e.target.dataset.del; if (!id || !confirm("Apagar esta rotina?")) return;
      try { await Sincro.apagarRotina(id); toast("Rotina apagada."); telaPainel(); } catch (err) { toast(err.message, true); }
    };
  } catch (err) { toast(err.message, true); }
}

function linhaHTML(a = "outro", i = "", f = "", d = "") {
  return `<div class="linha"><select aria-label="Atividade">${Object.entries(ATIV).map(([k, v]) => `<option value="${k}" ${k === a ? "selected" : ""}>${v[0]} ${v[1]}</option>`).join("")}</select>
    <input type="time" value="${i}" aria-label="Início" required><input type="time" value="${f}" aria-label="Fim" required>
    <input type="text" maxlength="200" placeholder="Descrição (opcional)" value="${esc(d)}"><button type="button" class="x" title="Remover" aria-label="Remover">×</button></div>`;
}

async function telaManual() {
  app.innerHTML = `<div class="pag"><div class="wrap"><h1>Montar rotina manualmente</h1><p class="sub">Adicione as atividades do seu dia com horário de início e fim. O sono pode atravessar a meia-noite.</p>
  <div class="card modelos-box"><b>⚡ Comece por um modelo pronto</b><p class="sub" style="margin:.2rem 0 .8rem">Escolha com um clique e ajuste o que quiser antes de salvar.</p><div class="modelos" id="modelos"><div class="sk"></div></div></div>
  <div class="duas"><div class="card"><div class="campo"><label for="titulo">Nome da rotina</label><input id="titulo" maxlength="80" placeholder="Ex.: Rotina de semana"></div>
    <label>Adicionar atividade</label><div class="presets">${Object.entries(ATIV).map(([k, v]) => `<button type="button" class="chip" data-add="${k}">${v[0]} ${v[1]}</button>`).join("")}</div>
    <div id="linhas"></div><button class="btn bloco" id="salvar" style="margin-top:.8rem">Salvar rotina</button></div>
  <aside class="card rec" id="rec"><h3>Recomendações</h3><p class="sub">Carregando…</p></aside></div></div></div>`;
  const L = $("#linhas");
  [["sono", "23:00", "07:00", "Sono reparador"], ["alimentacao", "07:30", "08:00", "Café da manhã"], ["alimentacao", "12:30", "13:10", "Almoço"],
   ["alimentacao", "20:00", "20:40", "Jantar"], ["hidratacao", "09:00", "09:05", "Água"]].forEach(x => L.insertAdjacentHTML("beforeend", linhaHTML(...x)));
  document.querySelector(".presets").onclick = e => { const k = e.target.dataset.add; if (k) L.insertAdjacentHTML("beforeend", linhaHTML(k, ...PRESETS[k], ATIV[k][1])); };
  L.onclick = e => { if (e.target.classList.contains("x")) e.target.closest(".linha").remove(); };
  $("#salvar").onclick = async () => {
    const itens = [...L.querySelectorAll(".linha")].map(r => { const c = r.querySelectorAll("select,input"); return { atividade: c[0].value, inicio: c[1].value, fim: c[2].value, descricao: c[3].value }; });
    if (!itens.length) return toast("Adicione pelo menos uma atividade.", true);
    if (itens.some(i => !i.inicio || !i.fim)) return toast("Preencha o início e o fim de todas as atividades.", true);
    const b = $("#salvar"); b.disabled = true;
    try { const r = await Sincro.criarRotinaManual($("#titulo").value, itens); window.__confete = true; toast("Rotina salva!"); ir("#/rotina/" + r.id); }
    catch (err) { toast(err.message, true); b.disabled = false; }
  };
  Sincro.modelos().then(ms => {
    $("#modelos").innerHTML = ms.map(m => `<button type="button" class="modelo" data-m="${esc(m.id)}"><span class="me">${m.emoji}</span><b>${esc(m.nome)}</b><small>${esc(m.descricao)}</small></button>`).join("");
    $("#modelos").onclick = e => { const b = e.target.closest("[data-m]"); if (!b) return; const m = ms.find(x => x.id === b.dataset.m);
      $("#titulo").value = m.titulo; L.innerHTML = m.itens.map(i => linhaHTML(i.atividade, i.inicio, i.fim, i.descricao)).join("");
      $("#modelos").querySelectorAll(".modelo").forEach(x => x.classList.toggle("sel", x === b)); toast(`Modelo “${m.nome}” aplicado. Ajuste e salve!`); L.scrollIntoView({ behavior: "smooth", block: "nearest" }); };
  }).catch(() => { $("#modelos").innerHTML = '<small class="sub">Não foi possível carregar os modelos.</small>'; });
  try {
    const r = await Sincro.recomendacoes();
    $("#rec").innerHTML = `<h3>Para a sua idade</h3><div class="big"><div><b>${r.recomendacoes.sono_horas[0]}–${r.recomendacoes.sono_horas[1]} h</b>de sono</div><div><b>~${r.recomendacoes.agua_litros} L</b>de água</div></div>
      <ul>${r.recomendacoes.texto.split("\n").map(t => `<li>${esc(t.replace(/^- /, ""))}</li>`).join("")}</ul>`;
  } catch (e) { $("#rec").innerHTML = ""; }
}

function telaIA() {
  app.innerHTML = `<div class="pag"><div class="wrap" style="max-width:760px"><h1>✨ Montar rotina com IA</h1>
  <p class="sub">Conte como é o seu dia hoje e o que você quer melhorar. A IA cria uma rotina completa e saudável nos seus horários.</p>
  <form class="card" id="f" novalidate>
    <div class="campo"><label for="atual">Como é a sua rotina hoje?</label><textarea id="atual" placeholder="Ex.: Acordo às 7h, vou para a faculdade de manhã, trabalho à tarde e costumo dormir só depois da 1h..."></textarea></div>
    <div class="campo"><label for="obj">O que você quer melhorar?</label><textarea id="obj" placeholder="Ex.: Quero treinar 4 vezes por semana, comer melhor e dormir mais cedo."></textarea></div>
    <div class="lin2"><div class="campo"><label for="acorda">Horário de acordar</label><input id="acorda" type="time" value="07:00" required></div>
      <div class="campo"><label for="dorme">Horário de dormir</label><input id="dorme" type="time" value="23:00" required></div></div>
    <div class="campo"><label for="comp">Compromissos fixos (opcional)</label><input id="comp" maxlength="500" placeholder="Ex.: Aula 8h–12h, trabalho 14h–18h"><div class="dica">Esses horários não serão movidos.</div></div>
    <div class="lin2"><div class="campo"><label for="peso">Peso em kg (opcional)</label><input id="peso" type="number" min="25" max="300" step="0.1"><div class="dica">Usado para calcular a meta de água.</div></div>
      <div class="campo"><label>Expediente (opcional)</label><div class="lin2"><input id="ti" type="time" aria-label="Início do expediente"><input id="tf" type="time" aria-label="Fim do expediente"></div></div></div>
    <button class="btn bloco" id="gerar">✨ Gerar minha rotina</button></form>
    <p class="dica" style="margin-top:1rem">🔒 Para montar a rotina, o texto que você escreve é enviado ao Google Gemini. Evite incluir dados sensíveis (documentos, endereço, telefone).</p>
    <p class="dica">A IA não está respondendo? <a href="#" id="diag">Testar a conexão com a IA</a><span id="diag-r"></span></p></div></div>`;
  $("#diag").onclick = async e => { e.preventDefault(); const r = $("#diag-r"); r.textContent = " Testando…";
    try { const d = await Sincro.diagnosticoIA(); r.innerHTML = ` <b style="color:${d.ok ? "#16a34a" : "#b45309"}">${d.ok ? "✅" : "⚠️"} ${esc(d.mensagem)}</b>`; } catch (err) { r.textContent = " " + err.message; } };
  $("#f").onsubmit = async e => {
    e.preventDefault();
    const d = { rotina_atual: $("#atual").value.trim(), objetivos: $("#obj").value.trim(), acorda: $("#acorda").value, dorme: $("#dorme").value, compromissos: $("#comp").value.trim() };
    if (d.rotina_atual.length < 10) return toast("Descreva um pouco mais a sua rotina atual (mínimo de 10 caracteres).", true);
    if (d.objetivos.length < 5) return toast("Conte o que você quer melhorar.", true);
    if (!d.acorda || !d.dorme) return toast("Informe os horários de acordar e dormir.", true);
    if ($("#peso").value) d.peso = Number($("#peso").value);
    if ($("#ti").value && $("#tf").value) { d.trabalho_inicio = $("#ti").value; d.trabalho_fim = $("#tf").value; }
    const msgs = ["Analisando a sua rotina atual…", "Calculando o sono ideal para a sua idade…", "Distribuindo refeições e hidratação…", "Encaixando o treino no melhor horário…", "Quase pronto, ajustando os detalhes…"]; let m = 0;
    carregando(true, "Montando a sua rotina…", msgs[0]); const iv = setInterval(() => { m = (m + 1) % msgs.length; $("#car-texto").textContent = msgs[m]; }, 2600);
    try { const r = await Sincro.criarRotinaComIA(d); clearInterval(iv); carregando(false); window.__confete = true; window.__motivo = r.motivo_fallback || null; toast("Rotina criada!"); ir("#/rotina/" + r.id); }
    catch (err) { clearInterval(iv); carregando(false); toast(err.message, true); }
  };
}

async function telaEditar(id) {
  app.innerHTML = `<div class="pag"><div class="wrap"><p class="sub">Carregando…</p></div></div>`;
  let r; try { r = await Sincro.verRotina(id); } catch (err) { toast(err.message, true); return ir("#/painel"); }
  app.innerHTML = `<div class="pag"><div class="wrap"><h1>✏️ Editar rotina</h1><p class="sub">Mude o nome, os horários e as atividades. Ao salvar, os avisos de saúde são recalculados.</p>
  <div class="duas"><div class="card"><div class="campo"><label for="titulo">Nome da rotina</label><input id="titulo" maxlength="80" value="${esc(r.titulo)}"></div>
    <label>Adicionar atividade</label><div class="presets">${Object.entries(ATIV).map(([k, v]) => `<button type="button" class="chip" data-add="${k}">${v[0]} ${v[1]}</button>`).join("")}</div>
    <div id="linhas"></div><div class="acoes-ed"><button class="btn" id="salvar">Salvar alterações</button><a class="btn sec" href="#/rotina/${id}">Cancelar</a></div></div>
  <aside class="card rec" id="rec"><h3>Recomendações</h3><p class="sub">Carregando…</p></aside></div></div></div>`;
  const L = $("#linhas"); L.innerHTML = r.itens.map(i => linhaHTML(i.atividade, i.inicio, i.fim, i.descricao)).join("");
  document.querySelector(".presets").onclick = e => { const k = e.target.dataset.add; if (k) L.insertAdjacentHTML("beforeend", linhaHTML(k, ...PRESETS[k], ATIV[k][1])); };
  L.onclick = e => { if (e.target.classList.contains("x")) e.target.closest(".linha").remove(); };
  $("#salvar").onclick = async () => {
    const itens = [...L.querySelectorAll(".linha")].map(x => { const c = x.querySelectorAll("select,input"); return { atividade: c[0].value, inicio: c[1].value, fim: c[2].value, descricao: c[3].value }; });
    if (!itens.length) return toast("Deixe pelo menos uma atividade.", true);
    if (itens.some(i => !i.inicio || !i.fim)) return toast("Preencha o início e o fim de todas as atividades.", true);
    const b = $("#salvar"); b.disabled = true;
    try { await Sincro.editarRotina(id, $("#titulo").value.trim() || r.titulo, itens); toast("Alterações salvas!"); ir("#/rotina/" + id); }
    catch (err) { toast(err.message, true); b.disabled = false; }
  };
  try { const x = await Sincro.recomendacoes();
    $("#rec").innerHTML = `<h3>Para a sua idade</h3><div class="big"><div><b>${x.recomendacoes.sono_horas[0]}–${x.recomendacoes.sono_horas[1]} h</b>de sono</div><div><b>~${x.recomendacoes.agua_litros} L</b>de água</div></div>
      <ul>${x.recomendacoes.texto.split("\n").map(t => `<li>${esc(t.replace(/^- /, ""))}</li>`).join("")}</ul>`; } catch { $("#rec").innerHTML = ""; }
}

async function telaRotina(id) {
  app.innerHTML = `<div class="pag"><div class="wrap"><p class="sub">Carregando…</p></div></div>`;
  let r; try { r = await Sincro.verRotina(id); } catch (err) { toast(err.message, true); return ir("#/painel"); }
  const usadas = [...new Set(r.itens.map(i => i.atividade))];
  const seg = r.itens.flatMap((i, n) => partes(i.inicio, i.fim).map(([a, b]) =>
    `<div class="seg" title="${esc(ATIV[i.atividade][1])} ${i.inicio}–${i.fim}" style="--i:${n};left:${a / 14.4}%;width:${Math.max((b - a) / 14.4, 0.7)}%;background:${ATIV[i.atividade][2]};${i.atividade === "hidratacao" ? "top:0;bottom:60%;z-index:2" : ""}"></div>`)).join("");
  app.innerHTML = `<div class="pag"><div class="wrap" style="max-width:860px">
    <div class="cab"><div><h1>${esc(r.titulo)} ${selo(r.origem)}</h1><p class="sub">Criada em ${dataBR(r.criado_em)}</p></div>
      <div class="nao-imprimir"><a class="btn sec peq" href="#/painel">← Voltar</a> <a class="btn sec peq" href="#/editar/${r.id}">✏️ Editar</a> <button class="btn sec peq" onclick="print()">🖨️ Imprimir</button> <button class="btn perigo peq" id="del">Apagar</button></div></div>
    ${r.origem === "ia_fallback" ? `<div class="avisos warn nao-imprimir"><b>ℹ️ Gerada pelo modo automático</b><p style="margin:.3rem 0 0">A IA não respondeu desta vez, então o Sincro montou a rotina por regras de saúde. Você pode editá-la.${window.__motivo ? `<br><small>Motivo: ${esc(window.__motivo)}</small>` : ""}</p></div>` : ""}
    ${r.resumo ? `<div class="card resumo"><b>${r.origem === "ia" ? "✨ O que a IA ajustou" : "Resumo"}</b><p style="margin:.3rem 0 0">${esc(r.resumo)}</p></div>` : ""}
    <div class="card" style="margin-top:1rem"><b>Seu dia em 24 horas</b><div class="dia" style="margin-top:.6rem">${seg}</div>
      <div class="eixo"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>24h</span></div>
      <div class="legenda">${usadas.map(k => `<span><i style="background:${ATIV[k][2]}"></i>${ATIV[k][1]}</span>`).join("")}</div></div>
    ${r.avisos.length ? `<div class="avisos warn"><b>⚠️ Pontos de atenção</b><ul>${r.avisos.map(a => `<li>${esc(a)}</li>`).join("")}</ul></div>`
      : `<div class="avisos ok">✅ Rotina equilibrada: sono, refeições e hidratação dentro das recomendações.</div>`}
    <ul class="tl">${r.itens.map((i, n) => `<li style="--i:${n}"><div class="h">${i.inicio}<br><small style="color:var(--mut);font-weight:500">até ${i.fim}</small></div>
      <div class="c" style="--cor:${ATIV[i.atividade][2]}"><b>${ATIV[i.atividade][0]} ${ATIV[i.atividade][1]}</b>${i.descricao ? `<span>${esc(i.descricao)}</span>` : ""}</div></li>`).join("")}</ul></div></div>`;
  window.__motivo = null;
  if (window.__confete) { window.__confete = false; confete(); }
  $("#del").onclick = async () => { if (!confirm("Apagar esta rotina?")) return;
    try { await Sincro.apagarRotina(id); toast("Rotina apagada."); ir("#/painel"); } catch (err) { toast(err.message, true); } };
}

/* ---------- roteador ---------- */
async function rotear() {
  const [, rota = "", arg] = (location.hash || "#/").slice(1).split("/");
  const publica = ["", "login", "cadastro", "recuperar"].includes(rota);
  if (Sincro.estaLogado() && !usuario) { try { usuario = await Sincro.perfil(); } catch { Sincro.sair(); } }
  if (!Sincro.estaLogado() && !publica) { toast("Faça login para continuar.", true); return ir("#/login"); }
  if (Sincro.estaLogado() && (rota === "login" || rota === "cadastro" || rota === "recuperar")) return ir("#/painel");
  clearInterval(window.__rot); renderTopo(); window.scrollTo(0, 0);
  if (rota === "") telaInicio(); else if (rota === "login" || rota === "cadastro") telaAuth(rota); else if (rota === "recuperar") telaRecuperar();
  else if (rota === "painel") telaPainel(); else if (rota === "manual") telaManual(); else if (rota === "ia") telaIA();
  else if (rota === "conta") telaConta(); else if (rota === "rotina" && arg) telaRotina(arg); else if (rota === "editar" && arg) telaEditar(arg); else ir("#/");
  app.classList.remove("in"); void app.offsetWidth; app.classList.add("in"); animar(); app.focus({ preventScroll: true });
}
window.addEventListener("hashchange", rotear);
window.addEventListener("sincro:sessao-expirada", () => { usuario = null; toast("Sua sessão expirou. Entre novamente.", true); ir("#/login"); });
window.addEventListener("scroll", () => $("#topo").classList.toggle("rolou", scrollY > 8), { passive: true });
rotear();
