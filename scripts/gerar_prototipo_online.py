"""Gera a versão online do protótipo (sem logotipo oficial, download pela hospedagem).

Uso: python scripts/gerar_prototipo_online.py frontend/prototipo/index.html saida.html
Publicado em https://claude.ai/artifact/58CuCxJuv7zo79EuJzozHC (slug 21661840-3ec0-4d59-af4a-44651f65ad8f).
"""
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()

SOL = '<svg viewBox="0 0 24 24" aria-hidden="true" width="{w}" height="{w}"><polygon fill="#FFB300" points="12,0 13.6,5.9 18,1.6 16.5,7.5 22.4,6 18.1,10.4 24,12 18.1,13.6 22.4,18 16.5,16.5 18,22.4 13.6,18.1 12,24 10.4,18.1 6,22.4 7.5,16.5 1.6,18 5.9,13.6 0,12 5.9,10.4 1.6,6 7.5,7.5 6,1.6 10.4,5.9"/></svg>'
n0 = len(src)
# Logotipo da barra lateral → marca neutra
src, k1 = re.subn(r'<img class="so-claro" src="data:image/png;base64,[^"]+" alt="TCE-PE"><img class="so-escuro" src="data:image/png;base64,[^"]+" alt="TCE-PE">',
                  SOL.format(w=34), src)
# Avatar do assistente nas mensagens
src, k2 = re.subn(r"const SIMB='<span><img class=\"so-claro\"[^']+'</span>';|const SIMB='<span>.*?</span>';",
                  "const SIMB='<span>" + SOL.format(w=22).replace("'", "\\'") + "</span>';", src, count=1, flags=re.S)
src = src.replace(".bot>span img{width:26px;margin-top:5px}", ".bot>span svg{margin-top:5px}")
src = src.replace("Processo TCE-PE nº", "Processo nº").replace("\"TCE-PE nº 99000002-0\"", "\"nº 99000002-0 (fictício)\"")
# Exportar: <a download> é bloqueado na hospedagem → capability downloads
antigo = 'const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([t],{type:"text/plain"}));a.download="ementa-99000002-0.txt";a.click();'
novo = ('(window.claude?claude.use("downloads"):Promise.resolve(null)).then(d=>{if(!d)throw 0;return d.save({filename:"ementa-99000002-0.txt",data:new Blob([t],{type:"text/plain"})})})'
        '.then(()=>reg("escolha","Conversa exportada")).catch(()=>{bot(`<p>O download não está disponível aqui. Use "Copiar a ementa final".</p>`)});')
assert antigo in src, "trecho de exportação não encontrado"
src = src.replace(antigo, novo)
src = src.replace("<title>Assistente de Ementas · protótipo de interface</title>", "<title>Assistente de Ementas · protótipo</title>")
assert k1 == 1 and k2 == 1, (k1, k2)
assert "base64" not in src
open(sys.argv[2], "w", encoding="utf-8").write(src)
print(f"{n0} → {len(src)} bytes")
