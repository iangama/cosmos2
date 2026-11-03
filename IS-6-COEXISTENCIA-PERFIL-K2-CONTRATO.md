# K2 — perfil próprio do protótipo de camadas simultâneas

Executar somente depois dos recibos funcional e visual K1C aceitos, com suas
fontes preservadas. Host 0.18.5 isolado, sem promoção sobre 3.13. Este perfil
avalia o protótipo dirigido pelo verificador; não aceita interface de produto,
persistência composta, migração ou integração GR–EM.

Quatro janelas: Terra com ambas as camadas estáticas, Júpiter com ambas
estáticas, Terra com quatro combinações de visibilidade a 2 Hz e Júpiter
com as mesmas combinações a 2 Hz. Cada janela tem 30 s de aquecimento e
60 s medidos, em 1920×1080 e UI 100%. Mesma fase orbital pausada, malha
65×96, domínio 1–3 Rref e ampliação 200; IGRF14 e JRM33 grau 13 conforme K1C.
Preparar os quatro artefatos, leituras e receitas antes da primeira captura.
Não mudar modelos, fonte, geometria ou câmera dentro da janela.

Limites prévios conservados: mediana ≤16,7 ms, p95 ≤25 ms, p99 ≤50 ms,
zero quadros >100 ms, RAM do produto ≤8 GiB e GPU dedicada+compartilhada
≤5,5 GiB. Exigir mais de 1.000 deltas válidos, sem overflow, resolução
1920×1080, intervalo medido 60±0,5 s depois de remover apenas o primeiro
delta da borda. Guardar todos os deltas e recalcular as estatísticas.

Nas janelas de visibilidade executar 120 comandos, espaçados por 0,5 s:
ambas ocultas, somente magnética, somente espacial e ambas visíveis,
repetidos 30 vezes. Exigir 120 respostas sem erro, ≥90% concluídas dentro
de 60 s, p95 de confirmação ≤0,5 s e máximo ≤1 s. Conferir os flags de
ambas as camadas em cada resposta nativa, posição científica e selo das
malhas; a fase orbital, artefato e leitura não podem mudar. As chamadas Lua
compartilham uma conexão persistente serializada para evitar concorrência
no transporte e pausas de fechamento por comando.

Registrar fase, câmera, flags, RAM e métricas do motor aos 0/20/40/60 s.
Coletar 66 amostras GPU schema3 com caminhos restritos ao produto e
inventários antes/depois, abrangendo toda a captura; nenhum status inválido,
instância própria nova/ausente ou contador faltante será convertido em zero.
Registrar identidades dos processos e hashes do motor, fontes e dono.

Arquivar fontes, contratos, artefatos, leituras e receitas antes das janelas.
Auditor separado deve conferir ZIP, hashes, modelos recalculados, fase e
visibilidades, deltas e recursos brutos. Confirmar remoção de todos os nós,
restauração exata dos flags e câmera (Up ≤10⁻¹²), saída normal app/server
e ausência de processos próprios antes de consolidar o resultado.
