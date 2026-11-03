# C2-00/G0 — base viável aprovada

Decisão em12/10/2026: continuar a construção sobre OpenSpace0.22, build próprio
EXEa37f248eb9ed59983b6f230cb47475ac9c662e4929b4f104e97fc33a9115efd2.
Aceite local do perfil pequeno na RX7600/Windows11; não é aceite da v1 ampliada.

| Critério | Resultado e evidência |
| --- | --- |
| Compilação própria | MSVC19.44/SDK10.0.26100/CMake4.1, fontes/componentes/patches e binários em built-runtime.json; oficial preservado |
| Hardware e janela | Radeon física/OpenGL4.6,1920×1080/75Hz/VSync, sem renderização por software |
| Atlas e worker | Terra–Lua–Via Láctea, Atlas+P32 e P32:3×60s cada, aquecimento30s; nove coletas completas |
| Frames | Mediana mínima74.424FPS; p95 máximo15.661ms; p99 máximo16.540ms; zero>100ms |
| Memória do produto | Soma residente máxima1.00232GiB; soma WDDM dedicada por processo máxima2.99185GiB; metas8/5.5GiB atendidas pelo método declarado |
| Abertura | Cache do aplicativo novo: API12.200s, CEF13.299s, PNG útil14.878s; progresso e fonteUTF8 corretos |
| Interface real | Busca e cliques em três destinos no CEF nativo; câmeras conferidas, imagens revistas, sem errosJS |
| Worker |32/128corpos, edição de massa, pausa e checkpoint exato; pausaHTTP em128corpos9.249ms |
| Offline | HTTP externo recusado antes da conexão, proxyCEF recusa externo e mantém loopback; controles científicos funcionam |

Evidências principais: native-benchmark-g0bulk.json e seu review, nove arquivos
gpu-memory-g0bulk-*.json, cold-start-bulk-20261012.json,
native-g0bulk-ui-review.json, laboratory-check.json, native-cef-check.json,
built-runtime.json, native-readers-check.json. Capturas g0bulk-earth/moon/galaxy
e cold-bulk-20261012-loading/ready foram inspecionadas.

A soma WDDM inclui recursos compartilhados entre processos e pode repeti-los;
é uma contabilização conservadora do produto, não VRAM exclusiva. O mínimo
de orçamentoDXGI observado7.19014GiB pertence ao motor, não ao conjuntoCEF.
Os totais por adaptador com outros aplicativos não aprovaram o produto.
KB4490156Windows10 considerado; nenhum defeito de crescimento falso foi
estabelecido nesta coletaWindows11. Os contadores não são uma nova auditoria
independente do gerenciamento de memória do driver.

Abertura medida com cacheSO quente/desconhecido, sem limpeza do cache de disco.
O PNG é limite superior do primeiro quadro útil, sem timestamp de apresentação.
A janela medida não equivale a instalação limpa/disco frio ou outras máquinas.

Não houve redução de cena:3.269.410pontosCOFF preservados bit a bit. O leitor
por blocos e decodificaçãoUTF8 reduziram o gargalo, com patches rastreados.
A escala galáctica upstreamParsec*100 foi preservada. Fonte fora doBMP tem
fallback definido pela APIwchar_tWindows; isso não promete tipografia universal.

Próximo: C2-01 e fatias científicas prioritárias das quatro forças. Permanecem
efemérides/épocas reais, contratos gerais, pacotes/cobertura, navegação final,
qualidade visual C2-03 e todos os aceites científicos ampliados. Atlas ainda
usa posições locais ilustrativas declaradas. LicençaAMNH pessoal/local impede
republicação automática desse dataset. Não repetir estes nove percursos sem
novo build, regressão ou alteração relevante do perfil.
