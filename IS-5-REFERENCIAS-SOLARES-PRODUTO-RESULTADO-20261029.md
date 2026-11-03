# IS5/C2-20 — perfis solares B23 na interface,29/10/2026

Candidata local 0.16.0 aprovada no recorte de consulta B23, com dados,
interface, visual e perfil próprio B aceitos. O perfil A permanece reprovado. Sem promoção;0.15.0,ciência/worker e instalado3.13
preservados. A consulta é somente leitura sobre resultados já auditados.

Seis modelos B23v1.2,2001amostras por modelo,curvas de temperatura/densidade/
pressão contra r/Rsun,sonda em SI com ne livre/velocidade do som e abundâncias
originais. Sonda lê a linha selecionada,sem interpolação ou renormalização.
Flags centrais e falta de comparação ficam explícitas. GS98/AGSS09 mostram
os713intervalos ideais A≥1 auditados; não são intervalos de confiança nem
uma comparação com a EOS Coulomb da zona. Composição/ionização incompletas
impedem essa extensão sem novo modelo científico validado.

Loader is5-solar-reference-browser-20261029a ACEITO:12006linhas exatas,
713intervalos/23recusas,incluindo arquivo alterado/ausente,tipos,índices,
modelos/parâmetros inválidos e duplicados. Dados/metadata/ReadMe/procedência
preservados; CC BY4.0,Herrera/Serenelli,GarStEC,DOI10.5281/zenodo.10822316.
GET não integra ODE nem depende de rede. Contrato de produto anterior ao código.

CEF is5-native-reference-20261029b ACEITO:3grupos/6recusas/9PNG/zeroJS.
Seis seletores e sondas conferidos,navegação por teclado/Escape,faixa de
índices,EOSideal/centro excluído/modelos sem comparação. Consulta de fato
aberta com zonaCoulomb ativa preserva artefato,fonte,view e faseorbital.
Host encerrou normalmente,engine_exit0. Fontes e ZIPs próprios preservados.

Visual is5-reference-visual-review-20261029b ACEITO:9PNG originais100/150%,
curvasT/rho/P/unidades/log10,sondas/flags/intervalos legíveis com rolagem.
Painel opaco evita texto da vista de fundo; botão de consulta permanece
acessível com zona ativa. São modelos externos de referência,sem Sol
calibrado/evoluído pelo Cosmos2 ou inicialização automática da zona.

TentativaA:CEF marcoutrue,mas revisão VISUAL A reprovou a última captura,
que mostrava só a zona. CSSbase bloqueava navbutton com zona ativa,e teste
não exigia painel aberto. A/ZIP/visualfalse preservados. RevisãoB alterou
somenteCSS0160 e reforçou teste de abertura antes da consulta/captura;
CSS/manifest anteriores arquivados emis5-reference-navigation-revision-
20261029b. B repetiu o percurso completo. Fontes0150/loader intactas.

Perfil próprio:IS-5-REFERENCIAS-SOLARES-PERFIL-PREVIO.md,quatrojanelas
zonaausente/ativapausada×consultaaberta/fechada,2seleçõesradiais/s quando
aberta,30swarm+60sSGCT/1920×1080. Não inferir desempenho da0150.
IS5/C2-20 permanecem parciais;sem transporte,hidrostática,luminosidade
calculada ouaceiteintegral do projeto por este instrumento isolado.

PerfilA completou4janelas;auditoris5-reference-profile-audit-20261029afalse:
1intervalo124,367699ms najanela4(zonaativa,consultafechada),p99=14,453280ms.
Primeiras3janelas dentro doslimites,ritmopublicação/solicitado≈0,9974–0,9977.
Causa nãoestabelecida;GPUestável e nenhum lognoinstante. A permanece reprovada.
ContratoIS-5-REFERENCIAS-SOLARES-PERFIL-REPRODUCAO-20261029.md autoriza uma
reproduçãoB completa sem alterar fontes/limites ou aproveitar janelasA.

Perfil B is5-reference-profile-20261029b ACEITO pelo auditor independente:
quatro janelas completas, fontes e limites idênticos, sem reutilizar janelas A.
Conferidos 24 estados da consulta, amostras e intervalos exatos, contadores,
artefato nuclear/fonte/fase orbital constantes, inventários RAM/GPU e UTC.

| Medida | Pior resultado B | Limite prévio |
| --- | ---: | ---: |
| Mediana | 13,342150ms | 16,7ms |
| p95 | 14,102180ms | 25ms |
| p99 | 14,734040ms | 50ms |
| Intervalos >100ms | 0 | 0 |
| RAM do produto | 1,203022GiB | 8GiB |
| GPU dedicada do produto | 3,036804GiB | 5,5GiB |
| Publicações/ritmo solicitado | 0,997544–1,005743 | 0,9–1,05 |

Aceite delimitado à medição B. O pico de 124,367699ms de A continua sem
causa estabelecida; B não demonstra impossibilidade de novos picos. Nenhuma
promoção ou aceite integral de IS5/C2-20. Próximo ciclo: derivadas da EOS
para trabalho mecânico prescrito, conforme IS-5-COMPRESSAO-CONTRATO-PREVIO.md.
