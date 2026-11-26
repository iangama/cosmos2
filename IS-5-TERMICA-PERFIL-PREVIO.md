# IS5 — perfil próprio do instrumento térmico0.11.0

Contrato antes da medição. Exigir CEF011/visual aprovados. Quatro janelas:
fracaon/off×gráficosvisíveis/ocultos, condições iniciais15MK/rho1,5e5/H0,34/
CNO0,01/N14/1Myr/1m³. EOS/T/U evoluídos calculados antes do perfil;não medir
throughputODE. Fonteorbital idêntica epausada,marcador/rótulo arquivados.

CEF1920×1080/100%,2amostrascalculadas/s,30swarmup+60sSGCTporjanela.
body.inert só duranteaquecer/medir,comUI/render ativos. Mesmos limitesG0:
mediana16,7/p9525/p9950ms/0>100,RAM8GiB/GPUdedicada5,5GiB,ritmo≥.9≤1.05.
Não excluirpicos;somenteprimeirointervalodacaptura descartadopelareceita.

66GPUamostras devem cobrirUTCintegral e processoIS5;ExpectedWorkerpaused
éORBITAL,IS5reproduçãoativa seconfere separado. Em0/20/40/60s guardar fonte,
resumo e sondatérmica,flags/posiçãonativas,RAM/DXGI. Arquivarresultado térmico
completo anteswarmup e exigir queT/P/U/Cv/energia da sonda casemexatamente
com índice do mesmoartefato emtodaleitura. Verificar hashes da ciência,
geração/worker/artifact/token/revision,owner e fontes executadas.

Arquivos próprios/scripts benchmark-is5-thermal-native.py e
audit-is5-thermal-profile.py. ColetorGPU aguarda até60s apóscaptura;erro
preserva brutos e não aprova janela. Auditor separado recalcula percentis,
inventários,cobertura,sondas,resultadosinteiros e identidades. Semaceite
deUI150no perfil100,deintegração emtempo real oudeevoluçãoestelar completa.
