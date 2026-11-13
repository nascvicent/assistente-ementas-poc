-- Esquema inicial (documento 01, seção 5.2)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE sessao (
  id            uuid PRIMARY KEY,
  usuario       text NOT NULL,
  estado        text NOT NULL,
  criado_em     timestamptz NOT NULL DEFAULT now(),
  atualizado_em timestamptz NOT NULL DEFAULT now(),
  nome_arquivo  text,
  hash_arquivo  text
);

CREATE TABLE documento (
  sessao_id       uuid REFERENCES sessao(id) ON DELETE CASCADE,
  pagina          int  NOT NULL,
  texto           text NOT NULL,
  secao_detectada text,
  PRIMARY KEY (sessao_id, pagina)
);

CREATE TABLE ficha (
  sessao_id     uuid PRIMARY KEY REFERENCES sessao(id) ON DELETE CASCADE,
  json          jsonb NOT NULL,
  versao_prompt text NOT NULL,
  modelo        text NOT NULL
);

CREATE TABLE item_ementa (
  sessao_id         uuid REFERENCES sessao(id) ON DELETE CASCADE,
  ordem             int  NOT NULL,
  ocorrencia_id     text NOT NULL,
  tese_escolhida    text,
  tese_editada      text,
  alternativas_json jsonb,
  termo_id          text,
  PRIMARY KEY (sessao_id, ordem)
);

CREATE TABLE ementa_versao (
  sessao_id     uuid REFERENCES sessao(id) ON DELETE CASCADE,
  n             int  NOT NULL,
  cabecalho     text,
  caso_em_exame text,
  razoes_json   jsonb,
  dispositivo   text,
  teses_json    jsonb,
  texto_final   text,
  PRIMARY KEY (sessao_id, n)
);

CREATE TABLE alerta (
  id         bigserial PRIMARY KEY,
  sessao_id  uuid REFERENCES sessao(id) ON DELETE CASCADE,
  tipo       text NOT NULL,
  gravidade  text NOT NULL,
  mensagem   text NOT NULL,
  referencia text
);

-- Auditoria: tabela de eventos somente-inserção.
CREATE TABLE evento (
  id            bigserial PRIMARY KEY,
  sessao_id     uuid REFERENCES sessao(id) ON DELETE CASCADE,
  quando        timestamptz NOT NULL DEFAULT now(),
  etapa         text NOT NULL,
  tipo          text NOT NULL CHECK (tipo IN ('chamada_modelo','escolha','pergunta','erro','transicao','verificacao')),
  entrada       jsonb,
  saida         jsonb,
  versao_prompt text,
  modelo        text,
  tokens        int,
  duracao_ms    int
);

CREATE FUNCTION evento_imutavel() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'evento é somente-inserção';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER evento_sem_update BEFORE UPDATE ON evento
  FOR EACH ROW EXECUTE FUNCTION evento_imutavel();

-- Wrapper IMMUTABLE: array_to_string não é aceito diretamente em coluna gerada.
CREATE FUNCTION tesauro_texto_busca(rotulo text, alternativos text[], nota text) RETURNS tsvector
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT to_tsvector('portuguese'::regconfig,
                     rotulo || ' ' || array_to_string(alternativos, ' ') || ' ' || coalesce(nota, ''))
$$;

CREATE TABLE tesauro_termo (
  id                  text PRIMARY KEY,
  uri                 text,
  rotulo_preferido    text NOT NULL,
  rotulos_alternativos text[] NOT NULL DEFAULT '{}',
  nota_escopo         text,
  vetor               vector(1024),
  versao_carga        text NOT NULL,
  busca               tsvector GENERATED ALWAYS AS (
    tesauro_texto_busca(rotulo_preferido, rotulos_alternativos, nota_escopo)
  ) STORED
);
CREATE INDEX tesauro_termo_busca ON tesauro_termo USING gin (busca);

CREATE TABLE tesauro_relacao (
  termo_id              text REFERENCES tesauro_termo(id) ON DELETE CASCADE,
  tipo                  text NOT NULL CHECK (tipo IN ('TG','TE','TR','USE','UP')),
  termo_relacionado_id  text NOT NULL,
  PRIMARY KEY (termo_id, tipo, termo_relacionado_id)
);
