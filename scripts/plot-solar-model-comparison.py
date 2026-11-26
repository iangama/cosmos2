"""Plot preserved model discrepancy separately from the numerical solver error."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
receipt = ROOT / 'evidence/is2-jpl-model-20261023b.json'
record = json.loads(receipt.read_text(encoding='utf-8'))
source = ROOT / record['series_file']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert record['completed'] and sha(source) == record['result_sha256']
data = json.loads(source.read_text(encoding='utf-8'))
seconds = np.array(data['seconds'])
delta = np.array(data['evolved_minus_reference_SI'])
folder = ROOT / 'output/is2-jpl-figures-20261023'
folder.mkdir(exist_ok=False)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
figure, axes = plt.subplots(1, 2, figsize=(11, 4.7), constrained_layout=True)
for i, name in enumerate(['Sol', 'Terra', 'Lua', 'Júpiter']):
    axes[0].plot(seconds/86400, np.linalg.norm(delta[:, i, :3], axis=1)/1000, label=name,
                 linestyle=['-', '-', '--', '-'][i])
axes[0].set(xlabel='Duração simulada (dias)', ylabel='Diferença de posição (km)',
            title='Quatro centros: diferença para a JPL em SSB')
axes[0].legend(); axes[0].grid(alpha=.25)
relative = np.array(data['evolved_SSB_SI'])[:, 2, :3]-np.array(data['evolved_SSB_SI'])[:, 1, :3]
reference = np.array(data['reference_SSB_SI'])[:, 2, :3]-np.array(data['reference_SSB_SI'])[:, 1, :3]
axes[1].plot(seconds/86400, np.linalg.norm(relative-reference, axis=1)/1000, color='#7c3a91')
axes[1].set(xlabel='Duração simulada (dias)', ylabel='Diferença de separação vetorial (km)',
            title='Lua em relação à Terra: origem comum removida')
axes[1].grid(alpha=.25)
figure.suptitle('Modelo newtoniano reduzido × efemérides geométricas fixadas', fontsize=13)
figure.supxlabel('121 amostras; 11/10/2026 12h UTC + duração em TDB. Diferença de modelo, sem limite de aceite observacional.\n'
                   'Erro numérico IAS15 × DOP853 medido separadamente: máximo por componente de 0,682 mm.', fontsize=9)
for extension in ['png', 'pdf', 'svg']:
    figure.savefig(folder / ('discrepancia-modelo-jpl.'+extension), dpi=180)
plt.close(figure)
report = {'schema': 1, 'script_sha256': sha(Path(__file__)), 'receipt_sha256': sha(receipt),
          'data_sha256': sha(source), 'matplotlib_version': matplotlib.__version__,
          'artifacts': {p.relative_to(ROOT).as_posix(): sha(p) for p in folder.iterdir()}}
(folder / 'plot-provenance.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps({'folder': folder.relative_to(ROOT).as_posix(), 'artifacts': list(report['artifacts'])}))
