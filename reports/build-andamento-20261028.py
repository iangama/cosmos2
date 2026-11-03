from pathlib import Path
import json
from collections import Counter
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
# Estado consolidado dos aceites e relatórios existentes; não é estimativa percentual.
rows=[
(0,'Base técnica e motor','accepted','Build Windows/OpenSpace, interface, worker, modo offline e prova G0 na RX7600.','Recorte-base aceito; novos recursos exigem regressões próprias.','Instalado','G0-DECISAO.md'),
(1,'Dados, unidades e procedência','accepted','IDs, SI, épocas/referenciais, fontes verificáveis e cópia Atlas → experimento.','Ampliar cobertura nos marcos de conteúdo e integração.','Instalado','C2-01-DECISAO.md'),
(2,'Navegação e interface','accepted','Busca, seleção, câmeras, viagens canceláveis, favoritos, tempo e interface 100–150%.','Expansão do catálogo e jornadas gerais pertencem aos marcos seguintes.','Instalado','C2-02-DECISAO.md'),
(3,'Qualidade visual inicial','accepted','Terra, Lua e Saturno; atmosfera, iluminação, anéis e sombras no recorte aprovado.','Relevo contínuo e demais mundos continuam em C2-05/16.','Instalado','C2-03-DECISAO.md'),
(4,'Atlas entre escalas','partial','Catálogo estelar, Via Láctea volumétrica e navegação inicial.','Completar viagens entre sistemas/galáxias, catálogo progressivo e retorno coerente.','Base inicial instalada','ROADMAP-GERAL.md'),
(5,'Superfícies e geração procedural','planned','Há mapas/texturas e geometrias de referência; não equivalem a terreno contínuo.','Lua/Marte, quatro famílias rochosas, 20 sementes e transição de superfícies.','Planejado','ROADMAP-GERAL.md'),
(6,'Editor gravitacional','accepted','Criar/remover/editar 1–128 massas; estados SI, órbitas, conservação e encontros.','Recorte aceito; colisões e instrumentos avançados têm marcos próprios.','Instalado','C2-06-DECISAO.md'),
(7,'Colisões, spin e energia','planned','Raio geométrico e spin cinemático no editor.','Contato contínuo, fusão de corpos, torques, calor e balanços dinâmicos.','Planejado','ROADMAP-GERAL.md'),
(8,'Histórico e recuperação integrada','partial','Checkpoints, ramos, exportação e retomada, inclusive em novos workers.','Unificar histórico/comparação/portabilidade entre todos os modelos e jornadas.','Instalado + candidatas','ROADMAP-GERAL.md'),
(9,'Desempenho e pacote base','partial','Executável local, inicialização, modo offline e perfis próprios de vários recortes.','Pacote integrado, instalação limpa e regressão de todos os recursos em conjunto.','Instalado + perfis de candidatas','ROADMAP-GERAL.md'),
(10,'Entrega intermediária','planned','Protótipo local executável já existe.','Fechar dependências, empacotar e aceitar formalmente a entrega C2-10.','Sem aceite deste marco','ROADMAP-GERAL.md'),
(11,'Instrumentos e gravidade avançada','partial','Sondas, campo/maré, cortes, J2 e ressonâncias; ensaios de 256 massas e 10 mil partículas.','Consolidar o conjunto, ampliar instrumentos/jornadas e fechar o aceite do marco.','Base 3.13 instalada; marco aberto','ROADMAP-GERAL.md'),
(12,'Laboratório eletromagnético','partial','E/B, Lorentz, editor de fontes/cargas, linhas, sondas e persistência em recortes.','Fechar integração e aceites conjuntos; perfis isolados não encerram o marco.','Bancadas + candidatas isoladas','PLANO-INTEGRACAO-SISTEMA-SOLAR.md'),
(13,'Magnetismo planetário','partial','IGRF14 na Terra, JRM33 em Júpiter; vetores, linhas/mapas e partículas-teste.','Expandir corpos e ambientes externos; concluir as jornadas planetárias integradas.','Bancadas + candidatas IS-3/4','IS-3-MAPAS-LOTES-RESULTADO-20261024.md'),
(14,'Relatividade em campo fraco','partial','Bancadas de relógios, luz/geodésicas e referências de curvatura.','Precessão, lentes/observador e a malha espaço-temporal solicitada.','Bancadas; integração pendente','CAMADAS-QUATRO-FORCAS.md'),
(15,'Buracos negros e luz','partial','Experimentos limitados de luz no modelo Schwarzschild.','Kerr, spin/arrasto, observador e imagem relativística calculada/validada.','Bancada parcial','ROADMAP-GERAL.md'),
(16,'Acervo e observatório','partial','Acervo nuclear/estelar inicial, mundos de referência e bancadas científicas.','12 mundos em destaque, 30 sistemas exoplanetários, 30 objetos profundos e 32 experiências completas.','Conteúdo inicial instalado','ROADMAP-GERAL.md'),
(17,'Integração e candidata final v1','planned','Componentes e diversos recortes possuem evidências próprias.','Jornadas J1–J15, quatro forças/camadas, saves, pacote offline e aceite conjunto.','Versão final não entregue','ROADMAP-GERAL.md'),
(18,'Núcleos e interação forte','accepted','AME2020: 3.558 estados; carta nuclear, ligação, Q/limiares e fusão manipulável.','Recorte aceito; evolução estelar e aprofundamento quântico têm outras etapas.','Instalado','C2-18-DECISAO.md'),
(19,'Decaimentos e interação fraca','accepted','Dez pais/19 canais avaliados, beta−/beta+/captura e cadeia Sr90 → Y90 → Zr90.','Recorte aceito; espectros/transporte/oscilação avançados seguem C2-22.','Instalado','C2-19-DECISAO.md'),
(20,'Quatro forças e região estelar','partial','Candidata 0.14.0: pp-I/II/III efetivo + CNO-I/II, 16 espécies/18 canais e resposta térmica ideal.','EOS Coulomb/screening; depois estrutura/transporte/hidrostática/luminosidade e integração completa.','Foco atual · candidata não promovida','IS-5-CNO-II-RESULTADO-20261027.md'),
(21,'Matéria quântica','proposal','Escopo de aprofundamento definido.','Hidrogênio quântico, espectros, barreira/tunelamento e modelo nuclear reduzido.','Expansão após a v1','ROADMAP-GERAL.md'),
(22,'Neutrinos e fraca avançada','proposal','Produção e energias de neutrinos já aparecem em recortes anteriores.','Espectros beta e oscilação de três sabores nos regimes contratados.','Expansão após a v1','ROADMAP-GERAL.md'),
(23,'Plasma coletivo','proposal','Há partículas-teste e vento solar prescrito em candidatas; não são plasma coletivo.','PIC eletrostático 1D, modos coletivos e produtos MHD identificados.','Expansão após a v1','ROADMAP-GERAL.md'),
(24,'Dinâmica galáctica','proposal','Via Láctea visual disponível como ponto de partida.','Potenciais disco/bojo/halo, órbitas, curvas de rotação e comparação de hipóteses.','Expansão após a v1','ROADMAP-GERAL.md'),
(25,'Cosmologia e universo observado','proposal','Planejamento e referências registrados.','FLRW, distâncias/redshift, produtos CMB e teia cósmica identificados e validados.','Expansão após a v1','ROADMAP-GERAL.md'),
(26,'Integração científica ampliada','proposal','Integração posterior planejada; nenhum aceite próprio.','Unir C2-21–25, mais 24 experiências e 56 no total, com pacote e jornadas próprios.','Expansão após a v1','ROADMAP-GERAL.md'),
]
labels={'accepted':'Aceito localmente','partial':'Parcial','planned':'Planejado','proposal':'Expansão proposta'}
data=[dict(id=f'C2-{i:02}',name=n,status=s,statusLabel=labels[s],ready=r,pending=p,where=w,source=f,scope='v1' if i<=20 else 'expansion') for i,n,s,r,p,w,f in rows]
assert len(data)==27 and len({r['id'] for r in data})==27
assert Counter(r['status'] for r in data)=={'accepted':7,'partial':10,'planned':4,'proposal':6}
assert all((ROOT/r['source']).is_file() for r in data)
meta={'analysisDate':'2026-10-28','latestScientificEvidenceDate':'2026-10-27','milestonesV1':21,'locallyAccepted':7,'partialV1':10,'plannedV1':4,'proposedExpansion':6,'installedGeneration':'3.13','installedRuntime':'cloud','installedRuntimeCheck':'approved-C211-engine-and-app-hashes','latestIsolatedCandidate':'0.14.0','deadline':'2026-11-12','calendarDaysUntilDeadline':(date(2026,11,12)-date(2026,10,28)).days,'newScientificTestsRun':False,'globalCompletionPercent':None}
(OUT/'andamento-20261028.json').write_text(json.dumps({'meta':meta,'milestones':data},ensure_ascii=False,indent=2)+'\n')
intro='''# Cosmos2 — andamento geral em 28/10/2026

A v1 tem 21 marcos: **7 aceitos localmente, 10 parciais e 4 planejados**.
Outras seis etapas são propostas de expansão. Essa contagem não mede percentual
de esforço, código ou qualidade total. Aceite local não é aprovação estética
do dono nem aceite da versão final.

O seletor normal confirmou a variante cloud da base 3.13, com hashes aprovados
do motor e aplicação. As candidatas mais recentes chegam a 0.14.0, sem promoção
sobre a base instalada. A análise leu planos, decisões, relatórios e seis
recibos recentes; não reexecutou suítes científicas nem benchmarks antigos.

'''
header='| Marco | Frente | Estado | O que já existe | Falta para fechar | Disponibilidade |\n|---|---|---|---|---|---|\n'
md=intro+header+'\n'.join('| '+' | '.join([r['id'],r['name'],r['statusLabel'],r['ready'],r['pending'],r['where']])+' |' for r in data)
md+='''

O avanço recente na integração do Sistema Solar foi:

| Frente | Resultado registrado | Limite atual |
|---|---|---|
| IS-1/2 | Sol/Terra/Lua/Júpiter, estados e gravidade conjunta; referências e perfil próprios | Recorte reduzido; não é todo o Sistema Solar nem aceite da v1 |
| IS-3 | IGRF/JRM33, orientação, vetores, linhas, mapas/cortes e persistência | Campos e amostras nos domínios declarados; integração total pendente |
| IS-4 | Cargas-teste 0.8.1 e vento Parker 0.9.0/0.9.1, com perfis e revisão visual | Cenário prescrito; não resolve MHD/magnetosfera/plasma coletivo |
| IS-5 | Rede estelar 0.14.0 e resposta térmica; referências solares B23 auditadas | EOS ideal, densidade/volume fixos; estrutura, transporte e luminosidade pendentes |
| IS-6 | Percurso completo e expansão definidos | Ainda sem aceite conjunto |

A candidata CNO-II possui recibos de ciência, worker, interface, imagem e perfil
aprovados. Seu perfil próprio de quatro janelas registrou p95 máximo 13,917 ms,
p99 máximo 14,405 ms e zero quadros acima de 100 ms; RAM 1,208 GiB / GPU 2,990 GiB.
São resultados dessa cena/UI/IPC, não throughput do solver ou desempenho de
qualquer combinação do produto. O pico de 401 ms da primeira coleta pp-III continua
registrado como falha, sem causa estabelecida; a coleta B passou.

Próximo passo técnico registrado: contrato de EOS Coulomb/screening a partir
de energia livre e derivadas termodinâmicas, antes de alterar solver/modelo.
Comparações com B23 encontraram pressão ideal acima das referências em cerca
de 1,74–2,28% no recorte avaliado; isso não identifica uma causa única.

Minha avaliação: a base gravitacional/nuclear e a validação por recortes
avançaram bastante. O maior risco de produto é acumular candidatas sem fechar
uma experiência integrada instalada. Também faltam superfícies, colisões,
expansão do conteúdo e a malha relativística solicitada. O próximo bloco deve
preservar o rigor do contrato científico e reservar integração/consolidação
para que os recursos aceitos cheguem à versão normalmente iniciada.

A meta continua 12/11/2026: 15 dias de calendário a partir desta análise. Com 14
marcos da v1 ainda sem aceite completo, não há base medida para garantir todo
o escopo nessa data. As antigas previsões em horas/meses foram retiradas e
não foram usadas aqui; não se alterou o prazo silenciosamente.

Fontes principais: ROADMAP-GERAL.md; PLANO-UM-MES.md;
PLANO-INTEGRACAO-SISTEMA-SOLAR.md; CAMADAS-QUATRO-FORCAS.md;
as sete decisões locais; IS-3-MAPAS-LOTES-RESULTADO-20261024.md;
IS-4-PARTICULAS-RESULTADO-20261025.md; IS-4-VENTO-SOLAR-RESULTADO-20261026.md;
IS-5-CNO-II-RESULTADO-20261027.md; IS-5-REFERENCIAS-SOLARES-RESULTADO-20261027.md.
'''
(OUT/'ANDAMENTO-GERAL-20261028.md').write_text(md)
html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cosmos2 — andamento geral</title>
<style>
:root{color-scheme:dark;font-family:Segoe UI,Arial,sans-serif;background:#0b1020;color:#e6ecf5}*{box-sizing:border-box}body{margin:0}header{padding:16px 22px 12px;background:#111a2e;border-bottom:1px solid #2b3c58}h1{font-size:25px;margin:0 0 4px;letter-spacing:-.4px}p{margin:5px 0;color:#b4c4d9;font-size:13px}strong{color:#f0f6ff}.top{display:flex;justify-content:space-between;gap:15px;align-items:center}.actions{display:flex;gap:8px}button,input{font:inherit;color:inherit;background:#18263f;border:1px solid #344b6a;border-radius:5px;padding:8px 11px}button{cursor:pointer}button:hover,button[aria-pressed=true]{background:#294367;border-color:#64c9f0}.counts{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.count{padding:7px 13px;border-radius:5px;background:#18243b;font-size:13px}.count b{font-size:20px;margin-right:7px}.green{color:#7ee0ae}.amber{color:#ffd080}.blue{color:#8cbbff}.filters{position:sticky;top:0;z-index:3;background:#10192c;padding:9px 20px;display:flex;gap:7px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #2b3c58}.filters button{font-size:12px;padding:6px 9px}.filters input{margin-left:auto;min-width:220px;font-size:12px;padding:7px}#shown{font-size:12px;color:#9bb1cf;white-space:nowrap}main{width:100%;min-height:calc(100vh - 180px);overflow:auto}table{width:100%;border-collapse:collapse;table-layout:fixed}thead{position:sticky;top:51px;z-index:2;background:#1a2a44}th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#b5d6ef;padding:10px}td{padding:10px;vertical-align:top;font-size:13px;line-height:1.4;border-bottom:1px solid #24324a;overflow-wrap:anywhere}tbody tr:nth-child(even){background:#0f182b}tbody tr:hover{background:#192a43}tr.current{background:#142d45!important;box-shadow:inset 4px 0 #65d9ff}.id{font-family:Consolas,monospace;color:#84b6db;font-weight:bold}.badge{font-size:11px;display:inline-block;border:1px solid #52637b;border-radius:4px;padding:3px 5px;line-height:1.2}.accepted{color:#82e3af;background:#15372e;border-color:#2c7354}.partial{color:#ffd180;background:#3c2c19;border-color:#876539}.planned{color:#c3ccda;background:#263143}.proposal{color:#adbdff;background:#252d51;border-color:#495c8b}a{color:#86ceee}td:nth-child(2){font-weight:600}td:nth-child(6){color:#a9bfd6}footer{padding:15px 22px;font-size:13px;color:#b0c3da;background:#111b2e;line-height:1.6}.compact td{padding:5px 8px;font-size:11.5px;line-height:1.25}.compact th{padding:7px 8px;font-size:11px}.compact .badge{font-size:10px;padding:2px 4px}.note{color:#f3cf89}details{padding:8px 0}summary{cursor:pointer;color:#88d3f5}@media(max-width:1100px){table{min-width:1100px}.filters{position:relative}thead{top:0}.top{align-items:flex-start}header{padding:12px}}@media print{body{background:white;color:black}.filters,.actions{display:none}header,footer{background:white}thead{position:static;background:#eee}td,th{color:black!important;font-size:10px!important}tbody tr{background:white!important}.badge{color:black!important;background:white!important}@page{size:A3 landscape;margin:8mm}}
</style><body class="compact"><header><div class="top"><div><h1>Cosmos2 · andamento completo</h1><p>Análise de 28/10/2026 · evidências recentes até 27/10 · aceites locais nos respectivos recortes</p></div><div class="actions"><button id="density">Modo confortável</button><button id="fullscreen">Tela cheia</button></div></div><div class="counts"><span class="count green"><b>7</b>marcos aceitos da v1</span><span class="count amber"><b>10</b>marcos parciais</span><span class="count"><b>4</b>marcos planejados da v1</span><span class="count blue"><b>6</b>expansões propostas</span></div><p><strong>Instalado: base 3.13, hashes aprovados.</strong> Avanço recente: candidata 0.14.0, ainda não promovida. Contagem de marcos não é percentual de trabalho.</p></header>
<nav class="filters" aria-label="Filtros"><button data-filter="all" aria-pressed="true">Tudo · 27</button><button data-filter="v1">V1 · 21</button><button data-filter="accepted">Aceitos · 7</button><button data-filter="partial">Parciais · 10</button><button data-filter="planned">Planejados · 4</button><button data-filter="proposal">Expansão · 6</button><input id="search" type="search" placeholder="Buscar recurso, marco ou pendência" aria-label="Buscar"><span id="shown"></span></nav>
<main><table><colgroup><col style="width:5%"><col style="width:15%"><col style="width:10%"><col style="width:27%"><col style="width:28%"><col style="width:11%"><col style="width:4%"></colgroup><thead><tr><th>Marco</th><th>Frente</th><th>Estado</th><th>O que já existe</th><th>Falta para fechar</th><th>Disponibilidade</th><th>Fonte</th></tr></thead><tbody id="rows"></tbody></table></main>
<footer><strong>Foco atual: IS-5 / C2-20.</strong> Próximo passo registrado: contratar EOS Coulomb/screening antes de novo modelo/solver. A zona estelar já tem rede e resposta térmica ideal; estrutura, transporte e luminosidade superficial ainda estão pendentes.<br><span class="note">Meta mantida: 12/11/2026 · 15 dias de calendário nesta análise. Não há garantia medida de fechar os 14 marcos abertos da v1 até essa data.</span><details><summary>Resultados recentes e limites da análise</summary>CNO-II 0.14.0: ciência, worker, interface e imagem aprovados; quatro janelas de perfil, p95 máximo 13,917ms, p99 14,405ms e zero quadros acima de 100ms. RAM 1,208GiB / GPU 2,990GiB, no método e cena declarados. Isso mede cena/UI/IPC e não throughput do solver. O pico de 401ms no primeiro perfil pp-III permanece registrado como falha sem causa estabelecida. A análise não reexecutou suites ou benchmarks: leu documentos/recibos e verificou a seleção instalada por hashes.</details><a href="ANDAMENTO-GERAL-20261028.md">Relatório completo</a> · <a href="andamento-20261028.json">Dados da tabela</a> · <a href="../ROADMAP-GERAL.md">Roadmap</a></footer>
<script id="dataset" type="application/json">__DATA__</script><script>
const rows=JSON.parse(document.getElementById('dataset').textContent);let filter='all';const body=document.getElementById('rows');function norm(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}function render(){body.replaceChildren();const query=norm(document.getElementById('search').value);let count=0;for(const r of rows){if(filter!=='all'&&(filter==='v1'?r.scope!=='v1':r.status!==filter))continue;if(query&&!norm(Object.values(r).join(' ')).includes(query))continue;count++;const tr=document.createElement('tr');if(r.id==='C2-20')tr.className='current';for(const key of ['id','name','statusLabel','ready','pending','where','source']){const td=document.createElement('td');if(key==='statusLabel'){const badge=document.createElement('span');badge.className='badge '+r.status;badge.textContent=r[key];td.append(badge)}else if(key==='source'){const a=document.createElement('a');a.href='../'+r.source;a.textContent='Ver';a.title=r.source;td.append(a)}else{td.textContent=r[key];if(key==='id')td.className='id'}tr.append(td)}body.append(tr)}document.getElementById('shown').textContent=count+' de 27'}document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));render()}));document.getElementById('search').addEventListener('input',render);document.getElementById('density').onclick=()=>{const compact=document.body.classList.toggle('compact');document.getElementById('density').textContent=compact?'Modo confortável':'Modo compacto'};document.getElementById('fullscreen').onclick=()=>{if(document.fullscreenElement){document.exitFullscreen()}else if(document.documentElement.requestFullscreen){document.documentElement.requestFullscreen().catch(()=>{document.getElementById('fullscreen').textContent='Use F11 no navegador'})}else{document.getElementById('fullscreen').textContent='Use F11 no navegador'}};render();
</script></body></html>'''
html=html.replace('</style>', 'body{display:flex;flex-direction:column;height:100dvh;overflow:hidden}header,.filters{flex:none}main{flex:1;min-height:0}thead{top:0}footer{flex:none;max-height:150px;overflow:auto}@media print{body{display:block;height:auto;overflow:visible}main{overflow:visible}footer{max-height:none;overflow:visible}}</style>')
html=html.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
(OUT/'ANDAMENTO-GERAL-20261028.html').write_text(html)
(ROOT/'ABRIR-ANDAMENTO-COSMOS2.cmd').write_text('@echo off\r\nstart "" "%~dp0reports\\ANDAMENTO-GERAL-20261028.html"\r\n')
print(json.dumps({'rows':len(data),'counts':dict(Counter(r['status'] for r in data)),'html':str(OUT/'ANDAMENTO-GERAL-20261028.html'),'markdown':str(OUT/'ANDAMENTO-GERAL-20261028.md')},ensure_ascii=False))
