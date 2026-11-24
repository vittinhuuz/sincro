// Cliente da API do Sincro. Inclua no HTML ANTES dos seus outros scripts:
//   <script src="js/sincro-api.js"></script>
// Como o front e o back ficam no mesmo site, a URL base é só "/api".
const Sincro = (() => {
  const BASE = "/api";

  async function chamar(metodo, caminho, corpo) {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem("sincro_token");
    if (token) headers["Authorization"] = "Bearer " + token;

    const resp = await fetch(BASE + caminho, {
      method: metodo,
      headers,
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const dados = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const erro = new Error(dados.erro || "Erro inesperado.");
      erro.status = resp.status;
      if (resp.status === 401 && token) { // sessão expirou ou foi encerrada
        localStorage.removeItem("sincro_token");
        window.dispatchEvent(new Event("sincro:sessao-expirada"));
      }
      throw erro;
    }
    return dados;
  }

  return {
    estaLogado: () => !!localStorage.getItem("sincro_token"),
    sair: () => localStorage.removeItem("sincro_token"),

    async cadastrar({ nome, sobrenome, idade, email, senha, confirmar_senha }) {
      const d = await chamar("POST", "/auth/cadastro", { nome, sobrenome, idade, email, senha, confirmar_senha });
      localStorage.setItem("sincro_token", d.token);
      return { ...d.usuario, codigo_recuperacao: d.codigo_recuperacao };
    },
    async recuperarSenha({ email, codigo, nova_senha, confirmar_senha }) {
      const d = await chamar("POST", "/auth/recuperar", { email, codigo, nova_senha, confirmar_senha });
      localStorage.setItem("sincro_token", d.token);
      return { ...d.usuario, codigo_recuperacao: d.codigo_recuperacao };
    },
    novoCodigo: senha => chamar("POST", "/auth/novo-codigo", { senha }),
    modelos: () => chamar("GET", "/modelos"),
    diagnosticoIA: () => chamar("GET", "/ia/diagnostico"),
    async entrar(email, senha) {
      const d = await chamar("POST", "/auth/login", { email, senha });
      localStorage.setItem("sincro_token", d.token);
      return d.usuario;
    },
    perfil: () => chamar("GET", "/auth/me"),
    async alterarSenha(senha_atual, nova_senha, confirmar_senha) {
      const d = await chamar("POST", "/auth/alterar-senha", { senha_atual, nova_senha, confirmar_senha });
      localStorage.setItem("sincro_token", d.token);
      return d;
    },
    async excluirConta(senha) { const d = await chamar("DELETE", "/auth/conta", { senha }); localStorage.removeItem("sincro_token"); return d; },
    recomendacoes: () => chamar("GET", "/atividades"),

    // itens = [{atividade:"sono", inicio:"23:00", fim:"07:00", descricao:"..."}, ...]
    criarRotinaManual: (titulo, itens) => chamar("POST", "/rotinas/manual", { titulo, itens }),
    // dados = {rotina_atual, objetivos, acorda:"07:00", dorme:"23:00", compromissos?, peso?}
    criarRotinaComIA: (dados) => chamar("POST", "/rotinas/ia", dados),

    listarRotinas: () => chamar("GET", "/rotinas"),
    verRotina: (id) => chamar("GET", `/rotinas/${id}`),
    editarRotina: (id, titulo, itens) => chamar("PUT", `/rotinas/${id}`, { titulo, itens }),
    apagarRotina: (id) => chamar("DELETE", `/rotinas/${id}`),
  };
})();

/* EXEMPLOS DE USO NO SEU FRONT:

   // Cadastro (no submit do formulário)
   try {
     await Sincro.cadastrar({ nome, sobrenome, idade: Number(idade), email, senha });
     window.location.href = "dashboard.html";
   } catch (e) { alert(e.message); }

   // Rotina com IA (demora 5-20s: mostre um "Carregando...")
   const rotina = await Sincro.criarRotinaComIA({
     rotina_atual: "Acordo 7h, trabalho das 9h às 17h, durmo à 1h",
     objetivos: "Quero treinar 4x por semana e dormir melhor",
     acorda: "07:00", dorme: "23:00",
   });
   // rotina.itens, rotina.resumo, rotina.avisos
*/
