# C2-01 — contratos e conteúdo inicial: decisão local

13/10/2026. **Aprovado localmente pelo agente**, no recorte inicial descrito
no ROADMAP-GERAL.md: contratos, propriedades/fontes, manifestos verificáveis
e cópia Sol/Terra/Lua. Não é aceite do dono, da versão final ou dos demais
marcos. Runtime próprio a37f248e… do G0 preservado, Windows/RX7600 e CEFreal.

| Critério | Resultado e evidência |
| --- | --- |
| IDs, unidades, referenciais e tempo | Sol10/Terra399/Lua301 com IDs sol:naif; 3558estados nucleus:ame2020; dez modelos científicos versionados. UnidadeSI/canônica, UTC/TDB e J2000/GALACTIC explícitos. canonical-units-check, science-contracts-check, nuclei-check, atlas-check/native-atlas-check |
| Procedência por propriedade | 21registros solares: posição, velocidade, GM, massaGM/G, forma, orientação e imagem. Status/fonte/época/ref/unidade e ausência de erro preservados. AME conserva flags/incertezas por campo. packages-properties-check |
| Observador onde aplicável | Estado geométrico simultâneo na origemSSB; câmera não é observador físico. Sem tempo de luz aplicado; emissão/recepção null. Não oferecer observação aparente. packages-properties-check/native-content-check |
| Manifestos verificáveis | Dez pacotes/34arquivos/894541883bytes. Todos os dados científicos locais atuais registrados; expectativas vêm dos recibos/recortes preservados ou definição/extracção local fixada. SHA256 conferidos. Ausente, corrupção de mesmo tamanho, tamanho alterado e caminhos inválidos detectados. Symlink externo recusado em fixtureLinux. packages-properties-check/packages-symlink-check |
| Transição Atlas→experimento | Cópia pausada, GMDE442 verdadeiro, subconjuntoCOMinercialJ2000, IDs ramificados, origem/vetores/época preservados. Inversa≤1,526e-5m e3,638e-12m/s; DOP853independente24h≤0,0002442m. atlas-import-check/native-atlas-import-check |
| Persistência e incompatibilidade | Checkpoint binário+metadados+escala, geração identificada, cópia retomada exata e movida entre pastas com espaços. Nove condições iniciais incompatíveis e quatro propriedades/observador incoerentes recusados sem mutação. Testes de configuração dos dez palcos preservados. atlas-import-check/packages-properties-check/force-persistence-check |
| Uso no produto e imagem | CEFreal: consultar corpos/fontes, pacotes/filtros, verificar/exporJSONlocal, voltarAtlas, copiar/editar/salvar/retomar/reiniciar; P32/P128 preservados. Imagens corrigidas/revistas, Edge720semoverflow e zeroJS. native-content-check/content-ui-check/native-atlas-import-check e reviews |

Limites: efemérides solares iniciais somente três corpos/1950–2050. Forma do
Sol desconhecida no recorte; textura/época de aquisição não inventadas.
Rotação IAU geral, sem ITRF/lunar binário preciso. Experimento reduzido com
massas pontuais newtonianas; exclui outros corpos/GR/J2/maré/radiação/colisões.
Concordância numérica não é precisão observacional. Fonte não publica erro
local dos vetores/GM; GM/G tem contribuição conhecida deG, não erro total.

Inventário verifica dados instalados e registra a última leitura; não é um
instalador geral, atualização de pacotes ou monitoramento contínuo. Termos e
créditos preservados, inclusive AMNH pessoal/local; nenhum pacote publicado.
Os marcos posteriores continuam responsáveis por acervo geral, observador
aparente, editor livre, instalação/recuperação e integração final. G0 não foi
repetido nem reatribuído à expansão. Próxima etapa: C2-18 Q/limiares/canais,
depois C2-19 decaimentos/capturas ampliados, com quatro forças independentes.
