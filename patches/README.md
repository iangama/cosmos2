# Patches locais do runtime

Base OpenSpace8b2778bed19f0c0501eed110c71dd00bd5305c55. Conservar a licença
MIT/copyright nos arquivos upstream. A aplicação é local, sem publicação.

frame-capture.patch, galaxy-point-reader.patch e offline-profile.patch são
independentes entre si. camera-relative-label.patch corrige glifos distantes.
Aplicar stage-tracing.patch **depois de frame-capture.patch**; é diagnóstico
opt-in, desligado por padrão. Aplicar async-script-log.patch **depois de
stage-tracing.patch**: move o log auxiliar para worker com fila limitada.
A ordem alfabética do recibo não é uma ordem de aplicação.

ghoul-utf8-font.patch usa raiz ext/ghoul e commit668586014d24c2aa79b4ebe77f166bd959007155;
não aplicar na raiz OpenSpace. built-runtime.json registra hashes dos patches
e dos binários efetivos. Preservar recibos anteriores nas comparações.
