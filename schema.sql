CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    sobrenome   TEXT    NOT NULL,
    idade       INTEGER NOT NULL CHECK (idade BETWEEN 10 AND 120),
    email       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,
    token_versao INTEGER NOT NULL DEFAULT 0,
    codigo_recuperacao_hash TEXT,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rotinas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo      TEXT    NOT NULL,
    origem      TEXT    NOT NULL CHECK (origem IN ('manual', 'ia', 'ia_fallback')),
    resumo      TEXT,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens_rotina (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rotina_id   INTEGER NOT NULL REFERENCES rotinas(id) ON DELETE CASCADE,
    atividade   TEXT    NOT NULL,
    inicio      TEXT    NOT NULL,   -- formato HH:MM
    fim         TEXT    NOT NULL,   -- formato HH:MM
    descricao   TEXT
);

CREATE INDEX IF NOT EXISTS idx_rotinas_usuario ON rotinas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_itens_rotina ON itens_rotina(rotina_id);

CREATE TABLE IF NOT EXISTS tentativas_login (
    chave   TEXT    NOT NULL,   -- e-mail|ip
    quando  INTEGER NOT NULL    -- timestamp (segundos)
);
CREATE INDEX IF NOT EXISTS idx_tentativas ON tentativas_login(chave);
