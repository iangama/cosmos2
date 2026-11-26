# Correção do referencial de evolução —29/10/2026

TentativaA calculou o primeiro caso Radau completo,mas falhou ao iniciar BDF:
o tempo NumPy fornecido por SciPy fez a expressãoρ0 ratio^(t/τ) devolver um
numpy.float64. A API científica aceita exige escalares Python e recusou o
tipo antes da comparação. Não é evidência de erro da trajetória Radau.

Converter explicitamenteρ, dlnρ/dt e V do adaptador BDF para float. Não
alterar solver/EOS/redes,limites,referências físicas ou tolerâncias. A API
continua recusando valores inválidos e não finitos. Não editar fontes aceitas.

Repetir o conjunto completo com label20261029b,sem reutilizar o RadauA.
A/ZIP/recibo/primeiroJSON permanecem preservados e reprovados. B precisa
concluir todos os casos,refinamentos,controles e recusas antes de aceite.
