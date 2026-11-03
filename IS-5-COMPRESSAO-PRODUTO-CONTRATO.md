# IS5 — instrumento de densidade prescrita,29/10/2026

Construir candidata isolada0.17.0 somente após trabalhador compressão aceito.
Base0.16.0 preserva consultas B23 somente leitura, fonte solar arquivada,
cena e órbita pausadas. Não promover candidata nem reinterpretar arquivos
isocóricos como arquivos de volume variável. Checkpoints próprios em pasta
da candidata; tipos novos recusam tipos antigos. Ciência e worker aceitos
permanecem imutáveis; alterações da ponte/interface pertencem à candidata.

O dono escolhe densidade constante, exponencial ou ciclo e razão0.8..1.2.
Rótulos distinguem densidade e volume INICIAIS de valores de cada instante.
Condições iniciais e configuração aplicada são explícitas antes do cálculo;
criação padrão:15MK,150000kg/m³,H0.34,CNO0.01,N14,1000anos,V0=1m³,
compressão exponencialρfinal/ρinicial=1.05. Um programa constante não mostra
razão editável. Guardas de densidade/temperatura valem para toda trajetória.
Recalcular sempre parte das condições iniciais. B23 não inicializa a zona.

Número bariônico fixo,volume inverso aρ e trabalhoW=−∫PdV externos ao modelo.
A intervenção prescrita aquece/esfria a zona; nenhum rótulo a apresenta como
colapso gravitacional calculado,estrutura estelar ou hidrodinâmica. Gates de
forças e dezoito canais mantidos; EOS/screening separados. Referência completa
usa os mesmos parâmetros,história,EOS e screening,variando somente os gates.

Sonda e exportação distinguem U(J/m³),E=VU(J),Q/Qν/Qretido(J),W(J),potênciasW,
ρ(kg/m³),V(m³),N_b(contagem),eventos e neutrinos totais. Contagens acumuladas
não são números por volume no volume atual. Taxas locais continuam/(m³s).
Balanço ΔE=Qretido+W legível; trabalho negativo na expansão e correlação
Coulomb negativa preservados. Sem migrar unidades por troca de nome.

Gráficos próprios deρ,V e trabalho/ΔE com eixo assinado,além das curvas já
existentes. Não pôr grandezas com unidades diferentes no mesmo eixo. Energia
nuclear retida tem gráfico/escala que permita enxergá-la diante do trabalho.
Neutrinos mostram total produzido; não fluxo espacial.241instantes calculados,
índices0/120/240 e reprodução2/8/24amostras/s; sem integração nuclear realtime.

Espera e cancelamento explícitos. Prazo600s por operação no worker,
transporte660s,ponte720s,CEF750s. Cálculos da ponte devem usar um Client
candidato: somente substituir o Client/artefato anterior após sucesso e
confirmação da cena. Visibilidade/sonda/fonte e último artefato confirmado
permanecem disponíveis se cálculo falhar,expirar ou for cancelado.
Registrar o candidato antes de chamar create/load; liberar em finally.
Cancelamento por rota curta própria,fora do mutex longo de comandos da cena,
identifica a transação em curso,manda quit ao candidato e confirma sua saída.
Não encerrar Client do último artefato confirmado para cancelar outro cálculo.
Publicação tardia de transação cancelada é recusada. Encerrar o app também
cancela o candidato antes de fechar recursos da cena. Sem threads de vigilância
Python nos auxiliares científicos; ownership JobObject já aceito preservado.

Aceite CEF/nativo:criação por formulário,histórias3formas,trabalho comsinal,
config aplicada exata,sondas e curvas,EOS/screening,gates/ν e referência,
busy/recusa≤2s,cancelamento e preservação durante criação/recalculo,corrupção/
tipos/guardas recusados,save/ramos/novo processo/export,retorno à órbita.
Inspecionar capturas100/150%,painéis de trabalho/sonda/controles/limites e
B23 aberta sobre zona pausada. ZeroerroJS,semaceitevisual somente por DOM.

Perfil após aceite funcional/visual:mesmos limites nativos G0 vigentes,
1920×1080,30s aquecimento+60smedição,quatro janelas:fracaon/off×gráficoson/off,
reprodução2amostras/s. Medir quadros,RAM/GPU e ritmo,sem ODE concorrente.
Limites iguais ao auditor0.15.0 aceito:mediana≤16.7ms,p95≤25ms,p99≤50ms,
zero intervalos>100ms,RAM≤8GiB,GPU≤5.5GiB e abaixo do orçamento do adaptador,
razão do ritmo medido/2amostras/s de0.9a1.05. Nenhuma janela é aceita somente
pela média;auditar séries completas e sondas contra o artefato exato.
Recusa de qualquer janela permanece registrada; investigar antes de repetir,
sem retirar picos ou afrouxar limites. Nenhum aceite de promoção inferido.
