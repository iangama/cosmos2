# C2-12 — protótipo eletromagnético isolado

18/10/2026, versão experimental0.2. Produto instalado permanece3.13, sem mudanças emapp. Toda a
implementação desta pasta é experimental e ainda não foi promovida.

O que passou:
- em_fields.py: fontes pontuais, dipolos e fundos E/B em SI, até128fontes
  estáticas;4120direções e referências/gradientes/rotação/exclusões.
- em_particles.py: Boris sincronizado,10períodos de B/E×B, refinamento de
  ordem2, energia B5.908e-15 e caso nãouniforme vsDOP853 independente.
- em_mutual.py: Coulomb com reação, VelocityVerlet,10períodos elípticos e=.4;
  energia5.044e-7 da escalaK+absU no passoT/4000;128forças conferidas contra
  avaliadorE. Isto NÃO mede128cargas evoluindo em tempo real.
- em_experiment.py: checkpointselado, geração, fase sincronizada, continuação
  exata123+777passos nosdoisregimes;14corrupções/domínios recusados.
- em_worker.py +em_presets.py: processo isolado, fila32comandos, quanta32passos/
  20ms,5cenários sintéticos, sondas/controles/save/load/20pausas; última prova
  ≤2.140ms para estas pequenaspopulações, não perfil128.
- ui/: servidor temporário4716, canvas3D no CEF real;5cenários,97amostras,
  E/B independentes, sonda, evolução/mapaantigo, save/restore e zeroJS.
  em-native-ui-check.json e captura cosmos2-em-prototype-fields.png.

Recibos em evidence/em-{field-kernel,particle-dynamics,mutual-dynamics,
checkpoint,worker,native-ui}-check.json. Captura revista em
em-native-ui-visual-review.json. A versão atual do servidor ganhou shutdown;
reiniciar e repetir a prova CEF para assegurar bytes iguais ao processo.

Editor0.2 validado: fontes fixas/cargas ativas criar/editar/remover, fundosE/B,
origemuser_model, seleçãoestável, Δenergia mecânica/carga/momentos, referências
reiniciadas e64intervenções com contagem explícita das antigas descartadas.
Schema2 salva histórico/visual/seleção. Migrador explícito EM0.1 fixado porhash,
original preservado; futuros777passos exatos vsprocesso do código congelado.
Não converte Session gravitacional. em-editor-check.json:17intervenções,
26recusas,2futuros editados777exatos; em-editor-worker-check.json:guardas,
exportaçãoSI evisibilidade durante evolução sem pausa. em-editor-native-ui-check.json:
percurso realCEF criar/editar/remover/fontes±/dipolo/fundos/cargas mútuas,
save-evolve-restore/histórico eJSON13542bytes conferido porsha256;zeroJS,
82arquivosapp eownerintactos. Captura cosmos2-em-source-editor.png revista.
Mapa antigo permanece marcado congelado. Medições têm instante/revisão/frame.

Próximo: integrar camadas à cena/navegação de produto em candidata própria;
medir128 cargas mútuas e10mil testes EM separadamente. Linhas integrais,
exportações de linhas/mapas, corpo/época/dados (C2-13) e perfis são pendências.

Modelos: fontesfixas não recebem reação nem geram ondas/radiação; Coulomb
mútuo é outro modo, sem Bpróprio, Maxwell, gravidade ou órbitas atômicas reais.
Dados do dipolo são sintéticos. Posição/velocidade saem no MESMOtempo inteiro,
semmeio-passo oculto. Capv0.01c/gyro0.1rad/passo; exclusões param naúltimafase
válida, inclusive cruzamentos entre endpoints. Válido noexterior declarado.

Constantes CODATA2022transcritas doNIST, com incertezas emconstants.json.
DownloadoriginalHTTP403; nãoháhashinventado deoriginal. Referências:
https://physics.nist.gov/cuu/pdf/RevModPhys.97.025002.pdf
https://farside.ph.utexas.edu/teaching/jk1/Electromagnetism/node52.html
https://docs.plasmapy.org/en/stable/api/plasmapy.simulation.particle_integrators.BorisIntegrator.html

Comoabrir:PythonWindows -Xutf8 ui/server.py;precisamotor-Built -InspectCEF.
FerramentaCEF scripts/cef_page.py:Page.navigate para http://127.0.0.1:4716/ e
voltarexatamenteaoURLanteriornofinal. Não usarconnect_over_cdp. Paraencerrar:
POST http://127.0.0.1:4716/api/shutdown comJSON{},aguardarworkerquit normal.
Storageobrigatórioisolado em output/c212-em-worker, nuncauser/sessions.
