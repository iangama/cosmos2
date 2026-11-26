# Cosmos2 — fontes publicadas em 26/11/2026

Repositório público: https://github.com/iangama/cosmos2

Snapshot das fontes e evidências selecionadas até a candidata local 0.29.0,
com os contratos e a passagem técnica de 21/11. O estado científico e o
próximo passo estão em LEIA-PRIMEIRO.md; esta publicação não representa
conclusão de C2-14 ou aceite da integração visual final.

Inclui fontes, scripts de preparação e validação, configurações, planos,
créditos, dados selecionados e evidências técnicas. snapshot-inventory.json
registra tamanho e SHA-256 dos arquivos selecionados. As evidências antigas
preservam seus resultados, inclusive falhas e referências ao histórico anterior.

Exclui executáveis, ambientes Python, builds do motor, caches, sessões
pessoais, credenciais e parte dos dados/artefatos. Não é instalador nem pacote
totalmente reproduzível. Os atalhos .cmd exigem o ambiente Windows local;
o repositório não é uma versão do simulador acessível pelo navegador.
Os componentes e dados de terceiros conservam seus próprios créditos e termos.

O histórico remoto foi reiniciado depois de o dono excluir o repositório
anterior. O novo primeiro commit usa Ian como autor e committer, com
113548582+iangama@users.noreply.github.com, endereço da conta iangama.
O histórico antigo fica preservado em backup local separado.

A configuração Git local fixa essa identidade. Os hooks em .githooks verificam
a identidade ao criar commits e todo o histórico enviado antes de um push.
Em um clone novo, ative-os com:

```sh
git config user.name Ian
git config user.email 113548582+iangama@users.noreply.github.com
git config user.useConfigOnly true
git config core.hooksPath .githooks
python3 scripts/verify-github-authorship.py --history
```

Não restaurar o histórico antigo como ancestral da branch main publicada.
