# CandidatoJ2, ainda fora do produto

Potencial exterior com eixo de simetria inercial prescrito; tensor analítico
obtido diferenciando o campo vetorial. Gradiente1,334e-9/tensor1,848e-9,
rotação1,402e-15/traço3,648e-16 nos modelos sintéticos. Não dados observados.
Fonte primária pinned: [REBOUNDx5.1.0](https://raw.githubusercontent.com/dtamayo/reboundx/5.1.0/src/gravitational_harmonics.c).
O código de referência aplica reação linear e mantém eixo de spin prescrito;
a documentação explicita que não integra reação do torque no spin.
[Contrato de harmônicos](https://reboundx.readthedocs.io/en/stable/effects.html#gravitational-harmonics).
Não instalar REBOUNDx automaticamente nem transplantar este source de referência.
Próxima implementação deve unificar g/Φ/T e forças, energia quadrupolar,
reação linear, domínio exterior r≥Req, eixo definido sem atribuir por default
ao spin cinematográfico. Balanço L completo não conserva sem spin reagindo;
declarar aproximação e validar componente axial em palco adequado.
IAS15 precisa religar callbacks, invalidar derivadas em edições e selar
parâmetros no checkpoint; _validate_solver atual recusa forças adicionais.
Não remover esse guard para fazer um protótipo passar.

15/10: j2_dynamics.py isolado passou60órbitas: energia1,735e-15,
Pnormalizado4,556e-16,Laxial7,065e-16; Lvetorial mudou5,19% comoesperado
comeixo prescrito. Precessão nodal/pericentro contra secular deprimeiraordem:
erros0,0336%/0,0205%. IAS15eps1e-9/1e-12 contraDOP853:1,391e-13/1,550e-13;
refinar passo máximo doDOP853 difere1,295e-13, no piso float64/oráculo.
Não exigir melhora monotônica de erro abaixo desse piso nemchamar deprecisão
absoluta certificada. Translação/boost/rotação:1,302e-14.
Campo/força/reação usam mesmo kernelSI. Callback captura falhas (ctypes as
engoliria) e interrompe; trial interior recusa seminstalar fase inválida.
Checkpoint religa callback e conserva fase/continuação exatas; leituras não
alteram binário domesmo integrador. Entre instâncias,serialização coincide
após excluir sówalltime medido e ponteiro _sim decada partícula: osderivados,
compensações e todosdemais camposIAS15 são comparados byteabyte.
6corrupções recusadas. Fontebinarydata.c5.2.2 pinned emreference.json.
Prova evidence/j2-dynamics-prototype-check.json. AindaNÃOinstalado; próximas
etapas são integraçãoSession/worker/sondas/mapas/history/UI, guardas deedição,
replaydosparâmetros echeckpoint doproduto. Marés/spin/material pendentes.
