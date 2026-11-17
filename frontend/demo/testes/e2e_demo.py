"""Teste ponta a ponta da demonstração no navegador, com Claude e armazenamento simulados.

Uso (a partir da raiz do repositório):
    python scripts/gerar_demo.py
    python frontend/demo/testes/e2e_demo.py [pasta-dist] [pasta-vendor]

pasta-vendor: cópias locais de pdf.min.js, pdf.worker.min.js (pdf.js 3.11.174) e
jszip.min.js (3.10.1), servidas no lugar do CDN. Requer playwright e Chrome
(CHROME=/caminho/do/chrome).
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

import os
AQUI = Path(__file__).resolve().parent
DIST = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI.parent / "dist"
VENDOR = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "vendor"
SAIDA = Path(os.environ.get("SAIDA", "/tmp"))
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

FICHA = {
  "processo": {"numero": "99000003-1", "modalidade": "AUDITORIA_ESPECIAL", "tipo": "CONFORMIDADE", "orgao_julgador": "PRIMEIRA_CAMARA",
               "relator": "Conselheiro Ciclano Exemplo", "unidade_jurisdicionada": "Vila Serena", "exercicios": [2024, 2025],
               "objeto": "Armazenamento e controle de estoque de vacinas na rede municipal",
               "evidencia": {"trecho": "Auditoria Especial de Conformidade realizada na Secretaria de Saúde do Município de Vila Serena", "pagina": 1}},
  "especie_recursal": None,
  "votacao": {"unanime": True, "relator_vencido": False, "redator_voto_vencedor": None, "evidencia": {"trecho": "Decisão unânime.", "pagina": 3}},
  "ocorrencias": [
    {"id": "oc1", "titulo": "Armazenamento de vacinas em refrigeradores domésticos", "resumo": "Vacinas guardadas em geladeiras domésticas sem controle de temperatura.",
     "relacionada_ao_merito": True,
     "fundamentos": [{"texto": "Contraria a norma sanitária.", "fonte": "voto", "evidencia": {"trecho": "O uso de geladeiras domésticas, sem registro diário de temperatura, expõe as vacinas a variações térmicas", "pagina": 2}},
                     {"texto": "Correção afasta multa.", "fonte": "voto", "evidencia": {"trecho": "a correção da falha no curso da fiscalização afasta a aplicação de multa", "pagina": 2}}],
     "normas": [{"citacao": "Resolução RDC ANVISA nº 197/2017", "evidencia": {"trecho": "A Resolução RDC ANVISA nº 197/2017 exige que os serviços de vacinação", "pagina": 1}}],
     "precedentes": [{"citacao": "Acórdão T.C. nº 9999/2025", "evidencia": {"trecho": "trecho inventado que não existe no voto", "pagina": 2}}],
     "consequencias": {"multa": "NAO_APLICADA", "debito": None, "alteracao_multa": None, "alteracao_debito": None, "evidencia": None},
     "responsaveis": ["Fulano de Tal"]},
    {"id": "oc2", "titulo": "Ausência de controle de estoque de imunobiológicos", "resumo": "Movimentações de vacinas não registradas no sistema.",
     "relacionada_ao_merito": True,
     "fundamentos": [{"texto": "Impede rastreabilidade.", "fonte": "voto", "evidencia": {"trecho": "impede a rastreabilidade dos lotes e a conciliação entre o estoque físico e o registrado", "pagina": 2}}],
     "normas": [], "precedentes": [], "consequencias": {"multa": None, "debito": None}, "responsaveis": ["Fulano de Tal"]},
    {"id": "oc3", "titulo": "Providências corretivas no curso da auditoria", "resumo": "Aquisição de câmaras refrigeradas.", "relacionada_ao_merito": False,
     "fundamentos": [{"texto": "Boa-fé.", "fonte": "parecer_mpc", "evidencia": {"trecho": "as providências adotadas no curso da fiscalização demonstram boa-fé", "pagina": 2}}],
     "normas": [], "precedentes": [], "consequencias": {}, "responsaveis": []}],
  "julgamento": {"resultado": ["REGULAR_COM_RESSALVAS", "INVENTADO"], "providencias": ["DETERMINACOES"], "por_responsavel": [],
                 "evidencia": {"trecho": "JULGAR REGULAR COM RESSALVAS o objeto da presente Auditoria Especial de Conformidade", "pagina": 3}},
  "nao_identificado": [],
}
TESES = {"sem_tese": False, "motivo": None, "teses": [
  {"nivel": 1, "texto": "O armazenamento de vacinas em refrigeradores domésticos, sem monitoramento contínuo de temperatura, contraria as normas sanitárias.", "acrescentou": "regra geral"},
  {"nivel": 2, "texto": "O armazenamento de vacinas em refrigeradores domésticos, sem monitoramento contínuo de temperatura, contraria a Resolução RDC ANVISA nº 197/2017.", "acrescentou": "norma"},
  {"nivel": 3, "texto": "Em Vila Serena, o armazenamento de vacinas em geladeiras domésticas contraria a Lei nº 14.133/2021.", "acrescentou": "condição"},
  {"nivel": 4, "texto": None, "acrescentou": None}]}
TERMOS = {"termos": [{"rotulo": "Rede de frio", "generico": "Vacinação", "justificativa": "Trata do armazenamento de imunobiológicos."},
                     {"rotulo": "Controle de estoque", "generico": "Gestão de materiais", "justificativa": "Registro de entradas e saídas."}]}
REDACAO = {"caso_em_exame": ["Auditoria Especial de Conformidade realizada na Secretaria de Saúde de município, nos exercícios de 2024 e 2025, sobre armazenamento e controle de estoque de vacinas."],
           "razoes": [{"ocorrencia_id": "oc2", "texto": "A ausência de registro das movimentações de imunobiológicos impede a rastreabilidade dos lotes e enseja ressalva."},
                      {"ocorrencia_id": "oc1", "texto": "O armazenamento de vacinas em refrigeradores domésticos, sem monitoramento contínuo de temperatura, contraria a Resolução RDC ANVISA nº 197/2017."}]}
VERIF = {"divergencias": [
            {"descricao": "Divergência inventada", "trecho_a": "isto não está no voto", "pagina_a": 2, "trecho_b": "nem isto", "pagina_b": 3},
            {"descricao": "Prazo da determinação difere entre fundamentação e dispositivo", "trecho_a": "plano de ação para substituir os equipamentos restantes até o fim de 2025", "pagina_a": 1,
             "trecho_b": "conclua, em até 180 dias, a substituição dos refrigeradores domésticos", "pagina_b": 3}],
         "alcance_teses": [{"tese": 1, "situacao": "fiel", "explicacao": "ok", "trecho": "", "pagina": 2}]}

CORRIGE = {"correcoes": [{"caminho": "ocorrencias[oc1].precedentes[0]", "remover": True}]}
UNICO = "Segue a ementa.\n\n**EMENTA:** AUDITORIA ESPECIAL. SAÚDE. REGULARIDADE COM RESSALVAS.\n\nI. CASO EM EXAME\n1. Trata-se de auditoria especial na Secretaria de Saúde.\n\nII. RAZÕES DE DECIDIR\n2. O uso de geladeiras domésticas viola a Lei nº 14.133/2021.\n\nIII. DISPOSITIVO\n3. Julgamento pela regularidade com ressalvas.\n\nIV. TESE DE JULGAMENTO\n4. Vacinas exigem refrigeração adequada.\n\nPARA CONFERIR\na) nada a registrar"
INIT = """
window.__prompts = [];
const resp = %s;
// armazenamento simulado (capacidade db)
const store = new Map(); const ouvintes = [];
const avisa = () => ouvintes.forEach((f) => f());
function semListaAninhada(v, dentroDeLista) {
  if (Array.isArray(v)) { const r = v.map((x) => semListaAninhada(x, true)); return dentroDeLista ? Object.fromEntries(r.map((x, i) => [i, x])) : r; }
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, semListaAninhada(x, false)]));
  return v;
}
const congela = (v) => { if (v && typeof v === "object") { Object.values(v).forEach(congela); Object.freeze(v); } return v; };
const copia = (v) => congela(JSON.parse(JSON.stringify(v)));
function docRef(path){ return { id: path.split("/").pop(), path,
  get: async () => ({ id: path.split("/").pop(), exists: store.has(path), data: () => copia(store.get(path)) }),
  set: async (d) => { store.set(path, semListaAninhada(JSON.parse(JSON.stringify(d)))); avisa(); },
  delete: async () => { store.delete(path); avisa(); },
  collection: (sub) => colRef(path + "/" + sub) }; }
function colRef(path){ let ord = null, lim = 1000;
  const snap = () => { const n = path.split("/").length + 1;
    let docs = [...store.keys()].filter((k) => k.startsWith(path + "/") && k.split("/").length === n)
      .map((k) => ({ id: k.split("/").pop(), exists: true, data: () => copia(store.get(k)) }));
    if (ord) docs.sort((a, b) => (a.data()[ord[0]] < b.data()[ord[0]] ? -1 : 1) * (ord[1] === "desc" ? -1 : 1));
    docs = docs.slice(0, lim); return { docs, size: docs.length, empty: !docs.length }; };
  const q = { doc: (id) => docRef(path + "/" + id), orderBy: (f, d) => { ord = [f, d]; return q; }, limit: (n) => { lim = n; return q; },
    get: async () => snap(), onSnapshot: (cb) => { const f = () => cb(snap()); ouvintes.push(f); setTimeout(f, 0); return () => {}; } };
  return q; }
window.__store = store;
function escolhe(t){
  if (t.includes("preencher uma ficha estruturada")) return resp.ficha;
  if (t.includes("quatro redações de tese")) return resp.teses;
  if (t.includes("expressões de busca")) return { consultas: ["vacina", "imunização", "controle de estoque", "almoxarifado"] };
  if (t.includes("escolher, numa lista de candidatos")) {
    const ids = [...t.split("<candidatos>")[1].matchAll(/^(\d+) \| /gm)].map((m) => m[1]);
    window.__candidatosTCN = ids;
    return { escolhas: [{ id: ids[0], justificativa: "teste" }, { id: "999999999", justificativa: "inventado" }, { id: ids[1], justificativa: "teste" }], sugestao_livre: "Rede de frio" };
  }
  if (t.includes("termos de indexação")) return resp.termos;
  if (t.includes("redigir duas partes")) return resp.redacao;
  if (t.includes("divergências materiais")) return resp.verif;
  if (t.includes("não encontrou literalmente")) return resp.corrige;
  throw {code:"invalid_json", message:"?"};
}
const fake = async (t, o) => { window.__prompts.push(t); const text = t.startsWith("PAPEL") ? resp.unico : "O voto trata disso na fundamentação (Voto, p. 2)."; if (o && o.onText) o.onText({text, delta:text}); return {text, truncated:false}; };
fake.json = async (t, o) => { window.__prompts.push(t); await new Promise(r=>setTimeout(r,50)); return JSON.parse(JSON.stringify(escolhe(t))); };
window.claude = { use: async (n) => n==="sample" ? fake : n==="downloads" ? {save: async () => { window.__salvo = true; }} :
  n==="db" ? { doc: docRef, collection: colRef } : n==="user" ? { id: async () => "u_teste" } : null };
""" % json.dumps({"ficha": FICHA, "teses": TESES, "termos": TERMOS, "redacao": REDACAO, "verif": VERIF, "corrige": CORRIGE, "unico": UNICO})


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
        async def rota(route):
            nome = route.request.url.rsplit("/", 1)[-1]
            if (VENDOR / nome).exists():
                await route.fulfill(path=str(VENDOR / nome), content_type="application/javascript")
            else:
                await route.abort()
        await pg.route("https://cdnjs.cloudflare.com/**", rota)
        await pg.route("https://fonts.googleapis.com/**", lambda r: r.abort())
        await pg.add_init_script(INIT)
        await pg.goto((DIST / "index.html").as_uri())
        ops = lambda: pg.locator(".ops").last

        await pg.click("#exemplo")
        await pg.wait_for_selector("text=Encontrei 3 pontos decididos")
        prompt_ficha = (await pg.evaluate("window.__prompts"))[0]
        assert "[[p. 1]]" in prompt_ficha and "TESE DE JULGAMENTO" not in prompt_ficha and "EMENTA:" not in prompt_ficha, "ementa vazou"
        corpo = await pg.inner_text("#col")
        assert "não localizado" not in corpo, "o trecho inventado deveria ter sido retirado na nova tentativa"
        await pg.click("[data-aba=registro]")
        assert "1 item(ns) sem suporte retirado" in await pg.inner_text("#conteudo")
        await pg.screenshot(path=str(SAIDA / "e2e_ficha.png"))

        await ops().locator(".op[data-i='0']").click()                      # ponto 1
        await pg.wait_for_selector("text=Escrever ou editar a tese")
        await pg.wait_for_timeout(1200)                                      # gravação da sessão
        await pg.click("#nova")
        await pg.wait_for_selector("[data-sessao]")
        await pg.click("[data-sessao]")
        await pg.wait_for_selector("text=Sessão retomada", timeout=8000)
        await pg.wait_for_selector("text=Escrever ou editar a tese", timeout=8000)
        assert "Tese" in await pg.inner_text("[aria-current=step]"), "trilha deveria estar na Tese"
        assert await pg.locator("[data-sessao]").count() == 0, "a sessão retomada não deveria aparecer em Anteriores"
        assert "Parou na tese" in await pg.inner_text("#atualSit") or "tese" in (await pg.inner_text("#atualSit")).lower()
        await pg.screenshot(path=str(SAIDA / "e2e_retomada.png"))
        await ops().locator(".op[data-i='3']").click()                      # editar
        await pg.fill("textarea.cola >> nth=-1", "Em Vila Serena, vacinas não podem ficar em refrigeradores domésticos.")
        await pg.click("button.ok >> nth=-1")
        await pg.wait_for_selector("text=Usar mesmo assim")
        await pg.click("button.ok >> nth=-1")
        await pg.wait_for_selector("text=Digitar outro termo")
        await pg.screenshot(path=str(SAIDA / "e2e_termos.png"))
        txt_termos = await ops().inner_text()
        assert txt_termos.count("TCN") >= 2 and "fora do tesauro" in txt_termos and "Buscar no tesauro" in txt_termos, txt_termos
        await pg.click("[data-aba=registro]")
        assert "identificador(es) fora da lista descartado(s): 999999999" in await pg.inner_text("#conteudo")
        await ops().locator(".op[data-i='4']").click()                      # digitar termo
        await pg.fill("textarea.cola >> nth=-1", "Vacinação > Rede de frio")
        await pg.click("button.ok >> nth=-1")
        await pg.wait_for_selector("text=não existe na cópia do TCN")
        await pg.click("button.ok >> nth=-1")
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 3")
        await pg.fill("#txt", "sim"); await pg.press("#txt", "Enter")
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 4")
        await ops().locator(".op[data-i='0']").click()                      # ponto 2
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 5")
        await pg.fill("#txt", "dispensar a tese"); await pg.press("#txt", "Enter")
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 6")
        await ops().locator(".op[data-i='3']").click()                      # buscar no tesauro
        await pg.fill(".resultados >> xpath=preceding-sibling::input", "restos a pagar")
        await pg.wait_for_selector(".resultados [data-id]")
        await pg.click(".resultados [data-id] >> nth=0")
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 7")
        await ops().locator(".op[data-i='2']").click()                      # retirar
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 8")
        await ops().locator(".op[data-i='1']").click()                      # tira o ponto 2
        await pg.wait_for_function("document.querySelectorAll('.ops').length >= 9")
        ementa = await pg.inner_text("#conteudo")
        assert "CONTROLE DE ESTOQUE" not in ementa and "REDE DE FRIO" in ementa, ementa[:300]
        await ops().locator(".op[data-i='1']").click()                      # concluir
        await pg.wait_for_selector("text=Ementa concluída", timeout=15000)
        await pg.check("#refs")
        ementa = await pg.inner_text("#conteudo")
        assert "Referências normativas: Resolução RDC ANVISA nº 197/2017." in ementa, ementa[-400:]
        assert "Vila Serena" in ementa  # a tese editada entrou, com o aviso registrado
        final = await pg.inner_text("#col")
        assert "E10" in final, "a tese com o município deveria gerar alerta E10"
        if await pg.locator("#ciente").count(): await pg.check("#ciente")

        await pg.click("[data-aba=avaliacao]")
        await pg.click("#rodaUnico")
        await pg.wait_for_selector("text=Ver a ementa do prompt único")
        aval = await pg.inner_text("#conteudo")
        assert "Prompt único" in aval and "Semelhança com a publicada" in aval
        await pg.select_option("[data-nota=nota]", "4")
        await pg.screenshot(path=str(SAIDA / "e2e_aval.png"))

        await pg.wait_for_timeout(1500)
        sess = await pg.evaluate("[...window.__store.entries()].filter(([k]) => k.split('/').length === 4).map(([k, v]) => [k, v.situacao, v.dados.avaliacao.nota])")
        assert len(sess) == 1 and sess[0][1].startswith("Ementa concluída") and sess[0][2] == "4", sess
        await pg.click("#nova")
        await pg.wait_for_selector("[data-sessao]")
        await pg.click("[data-sessao]")
        await pg.wait_for_selector("text=Sessão retomada")
        await pg.wait_for_selector("text=Ementa concluída")
        ementa2 = await pg.inner_text("#conteudo")
        assert "REDE DE FRIO" in ementa2 and "Referências normativas" in ementa2
        await pg.screenshot(path=str(SAIDA / "e2e_final.png"))
        print("prompts enviados:", len(await pg.evaluate("window.__prompts")))
        print("erros:", erros)
        print("final:\n", final[-1200:])
        await b.close()

asyncio.run(main())
