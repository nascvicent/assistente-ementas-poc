"""Linter de ementa — regras E01 a E21 (documento 02, seção 7).

Regras que dependem de contexto (Ficha, texto do voto, tesauro) só rodam quando o
contexto é fornecido. E18 e E19 são heurísticas (listas de palavras) e podem ter
falso positivo; por isso o resultado é sempre "pontos a conferir", nunca bloqueio.

Uso em linha de comando:  python -m app.verificadores.linter_ementa ementa.txt
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from app.dominio.dispositivo import EXPRESSOES_POR_MODALIDADE, resultados_no_texto
from app.dominio.enumeracoes import Gravidade, Modalidade, Resultado, modalidade_por_rotulo
from app.esquemas.ficha import Ficha
from app.verificadores.normalizacao import normalizar, sem_acento

# ---------------------------------------------------------------------------
# Configuração e contexto
# ---------------------------------------------------------------------------

TITULO_CASO = "CASO EM EXAME"
TITULO_RAZOES = "RAZÕES DE DECIDIR"
TITULO_DISPOSITIVO = "DISPOSITIVO"


@dataclass
class ConfigLinter:
    # A Portaria usa "tese de julgamento"; o Diário também publica "TESE" (a confirmar).
    titulo_tese_preferido: str = "TESE DE JULGAMENTO"
    titulos_tese_aceitos: tuple[str, ...] = ("TESE DE JULGAMENTO", "TESE")
    max_segmentos_cabecalho: int = 8
    max_frases_por_razao: int = 3


@dataclass
class TermoCabecalho:
    rotulo: str
    termo_id: str | None = None
    fora_do_tesauro: bool = False
    confirmado_pelo_usuario: bool = False


@dataclass
class ContextoLinter:
    modalidade: Modalidade | None = None
    ficha: Ficha | None = None
    texto_voto: str | None = None
    termos_cabecalho: list[TermoCabecalho] | None = None
    rotulos_tesauro: set[str] | None = None  # rótulos preferidos do TCN


@dataclass(frozen=True)
class Achado:
    codigo: str
    gravidade: Gravidade
    mensagem: str
    referencia: str | None = None


# ---------------------------------------------------------------------------
# Análise estrutural
# ---------------------------------------------------------------------------

_RE_TITULO_SECAO = re.compile(
    r"^\s*(?P<numeral>I{1,3}|IV|V|VI)\s*[.\-–]\s*(?P<titulo>[A-ZÀ-Ý][A-ZÀ-Ý ]+?)\s*:?\s*$",
    re.MULTILINE,
)
_RE_ITEM = re.compile(r"^\s*(?P<numero>\d+)\s*[.)]\s+(?P<resto>.*)$")
_RE_NUMERO_DUPLICADO = re.compile(r"^\s*(\d+)\s*\.\s+(\d+)\s*\.\s")


@dataclass
class Item:
    numero: int
    texto: str
    numeracao_duplicada: bool = False


@dataclass
class Secao:
    numeral: str
    titulo: str
    itens: list[Item] = field(default_factory=list)
    texto_solto: str = ""  # texto da seção fora de itens numerados

    @property
    def texto(self) -> str:
        return " ".join([self.texto_solto] + [i.texto for i in self.itens]).strip()


@dataclass
class EmentaAnalisada:
    texto: str
    tem_prefixo: bool
    cabecalho: str
    secoes: list[Secao]

    @property
    def segmentos(self) -> list[str]:
        cab = self.cabecalho.strip().rstrip(".").strip()
        return [s.strip() for s in re.split(r"\.\s+", cab) if s.strip()] if cab else []

    def secao(self, titulo: str | tuple[str, ...]) -> Secao | None:
        titulos = (titulo,) if isinstance(titulo, str) else titulo
        for s in self.secoes:
            if s.titulo in titulos:
                return s
        return None


def analisar(texto: str) -> EmentaAnalisada:
    texto = texto.replace("\r\n", "\n").strip()
    tem_prefixo = texto.startswith("EMENTA:")
    corpo = texto[len("EMENTA:"):] if tem_prefixo else texto

    titulos = list(_RE_TITULO_SECAO.finditer(corpo))
    cabecalho = corpo[: titulos[0].start()] if titulos else corpo
    cabecalho = re.sub(r"\s+", " ", cabecalho).strip()

    secoes: list[Secao] = []
    for i, m in enumerate(titulos):
        fim = titulos[i + 1].start() if i + 1 < len(titulos) else len(corpo)
        secao = Secao(m["numeral"], re.sub(r"\s+", " ", m["titulo"]).strip())
        atual: Item | None = None
        soltos: list[str] = []
        for linha in corpo[m.end():fim].split("\n"):
            if not linha.strip():
                continue
            mi = _RE_ITEM.match(linha)
            if mi:
                dup = bool(_RE_NUMERO_DUPLICADO.match(linha))
                resto = mi["resto"]
                if dup:
                    resto = re.sub(r"^\d+\s*\.\s+", "", resto)
                atual = Item(int(mi["numero"]), resto.strip(), dup)
                secao.itens.append(atual)
            elif atual is not None:
                atual.texto = f"{atual.texto} {linha.strip()}"
            else:
                soltos.append(linha.strip())
        secao.texto_solto = " ".join(soltos)
        secoes.append(secao)

    return EmentaAnalisada(texto, tem_prefixo, cabecalho, secoes)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

_ABREVIATURAS = r"(?:art|arts|inc|incs|al|p|pp|fl|fls|n|nº|sr|sra|dr|dra|ex|min|cons|proc|res|aux|v|cf|c\.c|etc|lc|ec)"


def contar_frases(texto: str) -> int:
    # Protege abreviações antes de dividir (lookbehind de largura variável não é permitido).
    protegido = re.sub(rf"\b({_ABREVIATURAS})\.", r"\1<P>", texto, flags=re.IGNORECASE)
    partes = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý\"“(])", protegido) if p.strip()]
    return len(partes)


def _chave(texto: str) -> str:
    return normalizar(texto, tirar_acento=True)


def _sem_milhar(texto: str) -> str:
    return re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", texto)


# ---------------------------------------------------------------------------
# Listas usadas pelas regras
# ---------------------------------------------------------------------------

INICIOS_VEDADOS = ("trata-se de", "trata-se do", "trata-se da", "cuida-se de", "cuida-se do", "cuida-se da", "cuidam os autos")

MARCAS_CASO_CONCRETO = ("no caso", "na especie", "nos autos", "em analise preliminar", "neste momento processual", "no presente caso", "in casu")

PALAVRAS_VETADAS = (
    "carta magna", "lei maior", "carta politica", "mandamus", "data venia", "data maxima venia",
    "excelso pretorio", "pretorio excelso", "in casu", "ex vi", "parquet",
)

# E18 (heurística): formas verbais finitas comuns em cabeçalhos mal formados.
VERBOS_CONJUGADOS = {
    "E", "SAO", "FOI", "FORAM", "SERA", "SERAO", "DEVE", "DEVEM", "PODE", "PODEM", "HA", "HOUVE",
    "CONFIGURA", "CONFIGURAM", "CARACTERIZA", "CARACTERIZAM", "ENSEJA", "ENSEJAM", "CONSTITUI",
    "CONSTITUEM", "AFASTA", "AFASTAM", "IMPLICA", "IMPLICAM", "EXIGE", "EXIGEM", "VEDA", "PERMITE",
    "AUTORIZA", "DETERMINA", "JULGA", "APLICA", "ESTA", "ESTAO", "TEM", "POSSUI", "CABE", "COMPETE",
    "INCIDE", "INCIDEM", "OBSERVA", "OBSERVOU", "DEIXOU", "DEIXARAM", "REALIZOU", "UTILIZOU",
}
CONECTIVOS_DE_ORACAO = {"QUE", "QUANDO", "PORQUE", "EMBORA", "CASO", "SE"}

# E19 (heurística): adjetivos valorativos.
ADJETIVOS_VALORATIVOS = (
    "gravissim", "flagrante", "absurd", "escandalos", "lamentavel", "inadmissivel", "inaceitavel",
    "vergonhos", "gritante", "temerari", "descalabro", "estarrecedor", "abominavel",
)

_RE_NORMA = re.compile(
    r"(?P<tipo>Lei\s+Complementar|Lei\s+Org[aâ]nica|Lei|LC|Decreto-Lei|Decreto|Resolu[cç][aã]o(?:\s+TC)?|"
    r"Portaria(?:\s+Normativa)?(?:\s+TC)?|Instru[cç][aã]o\s+Normativa|Emenda\s+Constitucional|EC|"
    r"S[uú]mula(?:\s+Vinculante)?|RDC(?:\s+ANVISA)?)"
    r"(?:\s+(?:Federal|Estadual|Municipal))?"
    r"\s*(?:n\s*[º°o.]\s*|n\.\s*º\s*|nº\s*)?(?P<num>\d[\d.]*\d|\d)(?:\s*/\s*(?P<ano>\d{2,4}))?",
    re.IGNORECASE,
)
# Citações da própria norma de ementas, inseridas por código (ex.: tese dispensada).
NORMAS_DE_SISTEMA = {("portaria", "322")}

_RE_VALOR = re.compile(r"R\$\s*(?P<v>\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)")
_RE_PERCENTUAL = re.compile(r"(?P<v>\d+(?:[.,]\d+)?)\s*%")
_RE_DATA = re.compile(r"\b(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4})\b")
_RE_PROCESSO = re.compile(r"\b\d{7,8}-\d\b|\bprocesso\s+(?:tc[e]?(?:-pe)?\s+)?n[º°o.]", re.IGNORECASE)

_RE_NUMERO_MAL_FORMATADO = re.compile(
    r"\b(Lei|Decreto|Resolu[cç][aã]o|Portaria|S[uú]mula|Instru[cç][aã]o Normativa)\b[^\n.;]{0,25}?"
    r"\b(?P<forma>n\.(?!\s*º)|n°|no\.?|nr\.?|n\.o|num\.|número)\s*\d",
    re.IGNORECASE,
)
_RE_ANO_DOIS_DIGITOS = re.compile(
    r"\b(?:Lei|Decreto|Resolu[cç][aã]o|Portaria|S[uú]mula|LC|EC)\b[^\n;]{0,25}?\d[\d.]*\s*/\s*\d{2}\b(?!\d)",
    re.IGNORECASE,
)


def _tipo_base(tipo: str) -> str:
    t = sem_acento(tipo.lower())
    if t.startswith("lei complementar") or t == "lc":
        return "lei complementar|lc"
    for base in ("lei organica", "decreto-lei", "decreto", "resolucao", "portaria", "instrucao normativa",
                 "emenda constitucional|ec", "sumula", "rdc", "lei"):
        if any(t.startswith(b) for b in base.split("|")):
            return base
    if t == "ec":
        return "emenda constitucional|ec"
    return t


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------

def _a(codigo: str, gravidade: Gravidade, mensagem: str, referencia: str | None = None) -> Achado:
    return Achado(codigo, gravidade, mensagem, referencia)


def _e01(e: EmentaAnalisada) -> list[Achado]:
    if not e.tem_prefixo:
        return [_a("E01", Gravidade.ALTA, 'A ementa deve começar com "EMENTA: ".')]
    if not e.texto.startswith("EMENTA: "):
        return [_a("E01", Gravidade.ALTA, 'Falta espaço depois de "EMENTA:".')]
    return []


def _e02(e: EmentaAnalisada) -> list[Achado]:
    achados = []
    cab = e.cabecalho
    if not cab:
        return [_a("E02", Gravidade.ALTA, "Cabeçalho vazio.")]
    letras = re.sub(r"[^A-Za-zÀ-ÿ]", "", cab)
    if letras != letras.upper():
        minusc = [p for p in re.findall(r"[A-Za-zÀ-ÿ]+", cab) if p != p.upper()][:5]
        achados.append(_a("E02", Gravidade.ALTA, "Cabeçalho deve estar todo em maiúsculas.", ", ".join(minusc)))
    if re.search(r"\s[–—-]\s", cab):
        achados.append(_a("E02", Gravidade.ALTA, "Segmentos do cabeçalho devem ser separados por ponto, não por travessão ou hífen."))
    if not cab.endswith("."):
        achados.append(_a("E02", Gravidade.ALTA, "Cabeçalho deve terminar com ponto final."))
    if re.search(r"\.(?=[A-ZÀ-Ý])", cab) or re.search(r"[;,]\s*$", cab):
        achados.append(_a("E02", Gravidade.ALTA, 'Segmentos devem ser separados por ". " (ponto e espaço).'))
    return achados


def _modalidade(e: EmentaAnalisada, ctx: ContextoLinter) -> Modalidade | None:
    if ctx.modalidade:
        return ctx.modalidade
    if ctx.ficha:
        return ctx.ficha.especie_recursal or ctx.ficha.processo.modalidade
    if e.segmentos:
        candidatas = modalidade_por_rotulo(e.segmentos[0])
        if len(candidatas) == 1:
            return candidatas[0]
    return None


def _e03(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    if not e.segmentos:
        return []
    primeiro = e.segmentos[0]
    candidatas = modalidade_por_rotulo(primeiro)
    if not candidatas:
        return [_a("E03", Gravidade.ALTA, "O primeiro segmento do cabeçalho não é uma modalidade processual reconhecida.", primeiro)]
    esperada = ctx.modalidade or (ctx.ficha and (ctx.ficha.especie_recursal or ctx.ficha.processo.modalidade))
    if esperada and esperada not in candidatas:
        return [_a("E03", Gravidade.ALTA, f"Modalidade do cabeçalho ({primeiro}) difere da modalidade do processo ({esperada}).", primeiro)]
    return []


def _e04(e: EmentaAnalisada, cfg: ConfigLinter) -> list[Achado]:
    achados = []
    esperado = [("I", TITULO_CASO), ("II", TITULO_RAZOES), ("III", TITULO_DISPOSITIVO)]
    encontrados = [(s.numeral, s.titulo) for s in e.secoes]

    for s in e.secoes:
        if "QUESTÃO EM DISCUSSÃO" in s.titulo or "QUESTAO EM DISCUSSAO" in s.titulo:
            achados.append(_a("E04", Gravidade.ALTA, 'A ementa do TCE-PE não tem a seção "Questão em discussão".', f"{s.numeral}. {s.titulo}"))
        if s.titulo == "DISPOSITIVO E TESE":
            achados.append(_a("E04", Gravidade.ALTA, "Dispositivo e tese devem ficar em seções separadas (III e IV).", f"{s.numeral}. {s.titulo}"))

    if encontrados[:3] != esperado:
        achados.append(_a(
            "E04", Gravidade.ALTA,
            "Seções devem ser: I. CASO EM EXAME; II. RAZÕES DE DECIDIR; III. DISPOSITIVO; IV. " + cfg.titulo_tese_preferido + ".",
            "; ".join(f"{n}. {t}" for n, t in encontrados) or "nenhuma seção encontrada",
        ))
        return achados

    resto = e.secoes[3:]
    if len(resto) > 1:
        achados.append(_a("E04", Gravidade.ALTA, "Há seções além da IV.", "; ".join(f"{s.numeral}. {s.titulo}" for s in resto)))
    if resto:
        iv = resto[0]
        if iv.numeral != "IV" or iv.titulo not in cfg.titulos_tese_aceitos:
            achados.append(_a("E04", Gravidade.ALTA, f'A seção IV deve ser "IV. {cfg.titulo_tese_preferido}".', f"{iv.numeral}. {iv.titulo}"))
        elif iv.titulo != cfg.titulo_tese_preferido:
            achados.append(_a("E04", Gravidade.BAIXA, f'Título da seção IV fora do padrão: usar "{cfg.titulo_tese_preferido}" (a confirmar com a Diretoria de Julgamento).', iv.titulo))
    return achados


def _e05(e: EmentaAnalisada) -> list[Achado]:
    achados = []
    numeros = [i.numero for s in e.secoes for i in s.itens]
    for s in e.secoes:
        for i in s.itens:
            if i.numeracao_duplicada:
                achados.append(_a("E05", Gravidade.ALTA, f'Numeração duplicada no item {i.numero} (ex.: "{i.numero}. {i.numero}.").', f"{s.numeral}. {s.titulo}"))
    if numeros and numeros != list(range(1, len(numeros) + 1)):
        achados.append(_a("E05", Gravidade.ALTA, "Itens devem ser numerados em sequência contínua (1, 2, 3…) do início ao fim, atravessando as seções.", " ".join(map(str, numeros))))
    for s in e.secoes:
        if not s.itens and s.texto_solto:
            achados.append(_a("E05", Gravidade.ALTA, "Seção sem item numerado.", f"{s.numeral}. {s.titulo}"))
    return achados


def _e06(e: EmentaAnalisada) -> list[Achado]:
    caso = e.secao(TITULO_CASO)
    if not caso or not caso.texto:
        return []
    achados = []
    for item in caso.itens or [Item(0, caso.texto)]:
        inicio = _chave(item.texto)
        for vedado in INICIOS_VEDADOS:
            if inicio.startswith(vedado):
                achados.append(_a("E06", Gravidade.MEDIA, f'Caso em exame não deve começar com "{vedado.capitalize()}": comece pelo objeto do processo.', item.texto[:60]))
                break
    return achados


def _e07(e: EmentaAnalisada, cfg: ConfigLinter) -> list[Achado]:
    razoes = e.secao(TITULO_RAZOES)
    if not razoes:
        return []
    return [
        _a("E07", Gravidade.MEDIA, f"Item {i.numero} das razões tem {n} frases (máximo {cfg.max_frases_por_razao}); provavelmente reúne mais de um fundamento.", i.texto[:60])
        for i in razoes.itens
        if (n := contar_frases(i.texto)) > cfg.max_frases_por_razao
    ]


def _e08(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    disp = e.secao(TITULO_DISPOSITIVO)
    modalidade = _modalidade(e, ctx)
    if not disp or not modalidade:
        return []
    expressoes = EXPRESSOES_POR_MODALIDADE.get(modalidade)
    if expressoes is None:  # A DEFINIR (pendência P1)
        return []
    texto = _chave(disp.texto)
    if not any(re.search(p, texto) for p in expressoes):
        return [_a("E08", Gravidade.ALTA, f"Dispositivo não usa expressão padronizada para {modalidade} (tabela provisória, pendência P1).", disp.texto[:80])]
    return []


_GRUPOS_EXCLUSIVOS = [
    {Resultado.REGULAR, Resultado.REGULAR_COM_RESSALVAS, Resultado.IRREGULAR},
    {Resultado.APROVACAO, Resultado.APROVACAO_COM_RESSALVAS, Resultado.REJEICAO},
    {Resultado.LEGAL, Resultado.ILEGAL},
    {Resultado.CAUTELAR_CONCEDIDA, Resultado.CAUTELAR_NAO_CONCEDIDA},
    {Resultado.PROVIDO, Resultado.PARCIALMENTE_PROVIDO, Resultado.NAO_PROVIDO, Resultado.NAO_CONHECIDO},
    {Resultado.ACOLHIDOS, Resultado.REJEITADOS},
    {Resultado.PROCEDENTE, Resultado.IMPROCEDENTE},
]


def _e09(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    disp = e.secao(TITULO_DISPOSITIVO)
    if not disp or not ctx.ficha:
        return []
    esperados = set(ctx.ficha.julgamento.resultado) | {r.resultado for r in ctx.ficha.julgamento.por_responsavel}
    achados_txt = resultados_no_texto(_chave(disp.texto))
    achados = []
    for r in sorted(esperados - achados_txt):
        achados.append(_a("E09", Gravidade.ALTA, f"Resultado do julgamento ({r}) não aparece no dispositivo.", disp.texto[:80]))
    for grupo in _GRUPOS_EXCLUSIVOS:
        if esperados & grupo:
            for r in sorted((achados_txt & grupo) - esperados):
                achados.append(_a("E09", Gravidade.ALTA, f"Dispositivo menciona {r}, que não é o resultado registrado na Ficha ({', '.join(sorted(esperados & grupo))}).", disp.texto[:80]))
    return achados


def _secao_tese(e: EmentaAnalisada, cfg: ConfigLinter) -> Secao | None:
    return e.secao(cfg.titulos_tese_aceitos)


def _termos_proibidos(ctx: ContextoLinter) -> set[str]:
    if not ctx.ficha:
        return set()
    termos = set(ctx.ficha.nomes_de_pessoas())
    if ctx.ficha.processo.unidade_jurisdicionada:
        termos.add(ctx.ficha.processo.unidade_jurisdicionada)
    if ctx.ficha.processo.numero:
        termos.add(ctx.ficha.processo.numero)
    return termos


def _e10(e: EmentaAnalisada, ctx: ContextoLinter, cfg: ConfigLinter) -> list[Achado]:
    tese = _secao_tese(e, cfg)
    if not tese:
        return []
    proibidos = {_chave(t): t for t in _termos_proibidos(ctx)}
    achados = []
    for item in tese.itens:
        chave = _chave(item.texto)
        if "r$" in chave:
            achados.append(_a("E10", Gravidade.ALTA, f"Tese {item.numero} cita valor em reais; a tese deve ser abstrata.", item.texto[:60]))
        if _RE_PROCESSO.search(item.texto):
            achados.append(_a("E10", Gravidade.ALTA, f"Tese {item.numero} cita número de processo.", item.texto[:60]))
        for k, original in proibidos.items():
            if k and re.search(rf"\b{re.escape(k)}\b", chave):
                achados.append(_a("E10", Gravidade.ALTA, f"Tese {item.numero} cita nome próprio do caso.", original))
    return achados


def _e11(e: EmentaAnalisada, cfg: ConfigLinter) -> list[Achado]:
    tese = _secao_tese(e, cfg)
    if not tese:
        return []
    achados = []
    for item in tese.itens:
        chave = _chave(item.texto)
        for marca in MARCAS_CASO_CONCRETO:
            if re.search(rf"\b{re.escape(marca)}\b", chave):
                achados.append(_a("E11", Gravidade.MEDIA, f'Tese {item.numero} contém marca de caso concreto ("{marca}").', item.texto[:60]))
    return achados


def _e12(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    if not ctx.texto_voto:
        return []
    voto = _sem_milhar(_chave(ctx.texto_voto))
    corpo = " ".join(s.texto for s in e.secoes)
    achados, vistos = [], set()
    for m in _RE_NORMA.finditer(corpo):
        base = _tipo_base(m["tipo"])
        num = m["num"].replace(".", "")
        if (base.split("|")[0], num) in vistos or (base.split("|")[0], num) in NORMAS_DE_SISTEMA:
            continue
        vistos.add((base.split("|")[0], num))
        padrao = rf"\b(?:{base})\b[^0-9]{{0,40}}?\b{num}\b"
        if not re.search(padrao, voto):
            achados.append(_a("E12", Gravidade.ALTA, "Norma citada na ementa não foi localizada no voto.", m.group(0).strip()))
    return achados


def _e13(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    if not ctx.texto_voto:
        return []
    voto = re.sub(r"\s+", " ", ctx.texto_voto)
    voto_compacto = voto.replace(" ", "")
    corpo = " ".join(s.texto for s in e.secoes)
    achados = []
    for m in _RE_VALOR.finditer(corpo):
        v = m["v"]
        if v not in voto and _sem_milhar(v) not in _sem_milhar(voto):
            achados.append(_a("E13", Gravidade.ALTA, "Valor não localizado no voto.", m.group(0)))
    for m in _RE_PERCENTUAL.finditer(corpo):
        v = m["v"]
        if f"{v}%" not in voto_compacto:
            achados.append(_a("E13", Gravidade.ALTA, "Percentual não localizado no voto.", m.group(0)))
    for m in _RE_DATA.finditer(corpo):
        d, mes, a = int(m["d"]), int(m["m"]), m["a"]
        variantes = {m.group(0), f"{d:02d}/{mes:02d}/{a}", f"{d}/{mes}/{a}"}
        if not any(v in voto for v in variantes):
            achados.append(_a("E13", Gravidade.ALTA, "Data não localizada no voto.", m.group(0)))
    return achados


def _e14_e21(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    if not ctx.termos_cabecalho:
        return []
    achados = []
    segmentos = {s.upper() for s in e.segmentos}
    rotulos = {r.upper() for r in ctx.rotulos_tesauro} if ctx.rotulos_tesauro is not None else None
    for t in ctx.termos_cabecalho:
        if t.fora_do_tesauro:
            if not t.confirmado_pelo_usuario:
                achados.append(_a("E21", Gravidade.MEDIA, "Termo fora do tesauro ainda não confirmado pelo usuário (art. 4º, III).", t.rotulo))
            continue
        if rotulos is not None and t.rotulo.upper() not in rotulos:
            achados.append(_a("E14", Gravidade.ALTA, "Termo marcado como do tesauro não existe no TCN com este rótulo.", t.rotulo))
        if t.rotulo.upper() not in segmentos:
            achados.append(_a("E14", Gravidade.ALTA, "Termo do tesauro não aparece no cabeçalho com o rótulo exato.", t.rotulo))
    return achados


def _e15(e: EmentaAnalisada) -> list[Achado]:
    corpo = " ".join(s.texto for s in e.secoes)
    achados = [
        _a("E15", Gravidade.BAIXA, 'Use "nº" na citação de normas.', m.group(0))
        for m in _RE_NUMERO_MAL_FORMATADO.finditer(corpo)
    ]
    achados += [
        _a("E15", Gravidade.BAIXA, "Ano da norma deve ter quatro dígitos.", m.group(0))
        for m in _RE_ANO_DOIS_DIGITOS.finditer(corpo)
    ]
    return achados


def _e16(e: EmentaAnalisada) -> list[Achado]:
    chave = _chave(e.texto)
    return [
        _a("E16", Gravidade.BAIXA, f'Expressão vetada: "{p}" (use linguagem simples; ex.: "Constituição Federal").', p)
        for p in PALAVRAS_VETADAS
        if re.search(rf"\b{re.escape(p)}\b", chave)
    ]


def _e17(e: EmentaAnalisada, cfg: ConfigLinter) -> list[Achado]:
    n = len(e.segmentos)
    if n > cfg.max_segmentos_cabecalho:
        return [_a("E17", Gravidade.BAIXA, f"Cabeçalho com {n} segmentos (sugestão: até {cfg.max_segmentos_cabecalho}).")]
    return []


def _e18(e: EmentaAnalisada) -> list[Achado]:
    achados = []
    for seg in e.segmentos:
        palavras = set(re.findall(r"[A-Z]+", sem_acento(seg.upper())))
        verbos = palavras & VERBOS_CONJUGADOS
        conectivos = palavras & CONECTIVOS_DE_ORACAO
        if verbos or conectivos:
            achados.append(_a("E18", Gravidade.ALTA, "Segmento do cabeçalho parece conter verbo ou oração; use só termos nominais (art. 4º, II).", seg))
    return achados


def _e19(e: EmentaAnalisada) -> list[Achado]:
    caso = e.secao(TITULO_CASO)
    if not caso:
        return []
    chave = _chave(caso.texto)
    return [
        _a("E19", Gravidade.BAIXA, "Caso em exame com adjetivo valorativo; a redação deve ser impessoal e sem juízo de valor.", radical)
        for radical in ADJETIVOS_VALORATIVOS
        if re.search(rf"\b{radical}", chave)
    ]


def _e20(e: EmentaAnalisada, ctx: ContextoLinter) -> list[Achado]:
    if not ctx.ficha:
        return []
    chave = _chave(e.texto)
    return [
        _a("E20", Gravidade.ALTA, "Nome de pessoa natural na ementa (art. 10, § 2º).", nome)
        for nome in sorted(ctx.ficha.nomes_de_pessoas())
        if re.search(rf"\b{re.escape(_chave(nome))}\b", chave)
    ]


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------

def verificar(texto: str, contexto: ContextoLinter | None = None, config: ConfigLinter | None = None) -> list[Achado]:
    ctx = contexto or ContextoLinter()
    cfg = config or ConfigLinter()
    e = analisar(texto)
    achados: list[Achado] = []
    achados += _e01(e)
    achados += _e02(e)
    achados += _e03(e, ctx)
    achados += _e04(e, cfg)
    achados += _e05(e)
    achados += _e06(e)
    achados += _e07(e, cfg)
    achados += _e08(e, ctx)
    achados += _e09(e, ctx)
    achados += _e10(e, ctx, cfg)
    achados += _e11(e, cfg)
    achados += _e12(e, ctx)
    achados += _e13(e, ctx)
    achados += _e14_e21(e, ctx)
    achados += _e15(e)
    achados += _e16(e)
    achados += _e17(e, cfg)
    achados += _e18(e)
    achados += _e19(e)
    achados += _e20(e, ctx)
    ordem = {Gravidade.ALTA: 0, Gravidade.MEDIA: 1, Gravidade.BAIXA: 2}
    return sorted(achados, key=lambda a: (ordem[a.gravidade], a.codigo))


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: python -m app.verificadores.linter_ementa <ementa.txt>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        achados = verificar(f.read())
    if not achados:
        print("Nenhum ponto a conferir.")
        return 0
    print(f"Confira antes de usar · {len(achados)} pontos")
    for a in achados:
        ref = f"  [{a.referencia}]" if a.referencia else ""
        print(f"{a.codigo} ({a.gravidade}): {a.mensagem}{ref}")
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
