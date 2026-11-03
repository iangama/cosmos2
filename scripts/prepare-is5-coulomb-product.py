"""Prepare0.15.0 only after the exact worker sources pass; preserve0.14.0."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-cno2-zone-product0.14.0/app'
WORKER=ROOT/'output/is5-coulomb-worker-v2-staging'
TARGET=ROOT/'output/is5-coulomb-zone-product0.15.0'
receipt=ROOT/'evidence/is5-coulomb-worker-artifact-20261029b.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Expected unique product template: '+old[:80])
    return text.replace(old,new)


def main():
    accepted=json.loads(receipt.read_text(encoding='utf-8'))
    if not accepted.get('accepted') or not accepted.get('completed'):raise ValueError('Await complete worker acceptance')
    if not all(sha(ROOT/n)==h for n,h in accepted['source_sha256'].items()):raise ValueError('Accepted worker/source differs')
    if TARGET.exists():raise FileExistsError('Preserve product candidate')
    originals={p.relative_to(ROOT).as_posix():sha(p) for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    shutil.copytree(BASE,TARGET/'app',ignore=shutil.ignore_patterns('__pycache__'))
    app=TARGET/'app'
    for p in WORKER.glob('*.py'):shutil.copy2(p,app/p.name)
    text=(app/'is5_laboratory.py').read_text(encoding='utf-8')
    text=text.replace('is5_cno2_client','is5_coulomb_client').replace('is5_cno2_artifact','is5_coulomb_artifact')
    text=text.replace("'isochoric_ideal'","'isochoric'")
    text=replace(text,"        self.topic = 0","        self._command_admitted = False\n        self.topic = 0")
    text=replace(text,"            return copy.deepcopy(self.public)","            result = copy.deepcopy(self.public)\n            result['busy'] = bool(result.get('busy') or self._command_admitted)\n            return result")
    start=text.index('    def command(self, request):')
    end=text.index('    def _publish(',start)
    text=text[:start]+'''    def command(self, request):
        if not isinstance(request, dict):
            raise ValueError('Comando da zona solar deve ser um objeto.')
        closing = request.get('command') == '_close'
        with self.lock:
            if not closing and (self._command_admitted or self.public.get('busy')):
                raise ValueError('Aguarde a confirmação do cálculo em andamento.')
            if not closing:
                self._command_admitted = True
        future = Future()
        try:
            self.actions.put_nowait((copy.deepcopy(request), future))
        except queue.Full:
            with self.lock:
                if not closing:self._command_admitted = False
            raise ValueError('Aguarde os comandos da zona solar em andamento.')
        return future.result(timeout=360)

''' +text[end:]
    text=replace(text,"                future.set_exception(error)\n\n    def close", "                future.set_exception(error)\n            finally:\n                with self.lock:self._command_admitted = False\n\n    def close")
    (app/'is5_laboratory.py').write_text(text,encoding='utf-8')
    server=(app/'server.py').read_text(encoding='utf-8')
    server=replace(server,"    def do_POST(self):\n        with SOURCE_COMMANDS:\n            return self._post()",'''    def do_POST(self):
        # Keep source transactions serial, and reject queued late zone commands.
        if self.path == '/api/shutdown':
            return self._post()
        if self.path == '/api/solar-zone/command':
            if not SOURCE_COMMANDS.acquire(blocking=False):
                return self.json_response({'ok':False,'error':'Aguarde a alteração da cena em andamento.'},400)
            try:
                return self._post()
            finally:
                SOURCE_COMMANDS.release()
        if SOLAR_ZONE.status().get('busy'):
            return self.json_response({'ok':False,'error':'Aguarde a confirmação da zona solar.'},400)
        with SOURCE_COMMANDS:
            return self._post()''')
    (app/'server.py').write_text(server,encoding='utf-8')
    panel=(app/'ui/is5-zone-panel.html').read_text(encoding='utf-8')
    panel=panel.replace('SOL ARQUIVADO · CADEIAS PP E CICLOS CNO-I / CNO-II','SOL ARQUIVADO · COULOMB E SCREENING · PP/CNO')
    panel=panel.replace('Fusão solar · cadeias pp e ciclos CNO','Fusão solar · plasma com Coulomb')
    panel=replace(panel,'<p id="zone-source" class="zone-reading"></p>','<p id="zone-source" class="zone-reading"></p><p id="zone-model-reading" class="zone-reading"></p>')
    panel=replace(panel,'<p id="zone-reference-reading" class="zone-reading"></p></details>',
        '<p id="zone-screening-reading" class="zone-reading"></p><details><summary>Fatores adicionais por canal</summary><p class="field-help">Multiplicadores das taxas nuas. EC e decaimentos mantêm fator1; a lei de plasma da captura eletrônica permanece.</p><div id="zone-screening-table"></div></details><p id="zone-reference-reading" class="zone-reading"></p></details>')
    panel=panel.replace('A referência conserva todas as atuações e canais ligados.','A referência conserva todos os canais ligados, com as mesmas condições e opções de Coulomb/screening.')
    old='<label class="field">Avaliação dos decaimentos β⁺<select id="zone-decay"><option value="nubase2020">NUBASE2020</option><option value="reaclib_wc12">REACLIB wc12</option></select></label>'
    new='''<fieldset><legend>Propriedades do plasma</legend><label class="compact-check"><input id="zone-coulomb" type="checkbox" checked> Coulomb na equação de estado</label><label class="compact-check"><input id="zone-screening" type="checkbox" checked> Screening das fusões</label><p class="field-help">Screening exige a mesma energia livre de Coulomb. Os controles de forças acima atuam nos canais nucleares. Decaimentos β⁺: NUBASE2020 fixo neste modelo.</p></fieldset>'''
    panel=replace(panel,old,new)
    panel=panel.replace('NUBASE2020 ou wc12 para β⁺.','NUBASE2020 fixo para β⁺.')
    panel=panel.replace('Íons ideais, elétrons Fermi–Dirac não relativísticos e radiação LTE confinada.',
        'Íons clássicos com correlações de Coulomb PC, polarização e troca/correlação eletrônica EXCOR7. Elétrons Fermi–Dirac não relativísticos no termo ideal e radiação LTE confinada.')
    panel=panel.replace('Sem estrutura estelar, transporte, Coulomb, screening das fusões ou pep/hep/CNO-III/hot-CNO.',
        'O screening estático de fusões deriva dos potenciais químicos da mesma energia livre usada no reservatório; não é aplicado novamente à EC de Be-7 ou aos decaimentos. Sem estrutura estelar, transporte, ionização parcial, correções quânticas dos íons, campos magnéticos na EOS ou pep/hep/CNO-III/hot-CNO. A mistura polarizável é uma aproximação para degenerescência parcial; precisão numérica não determina precisão física.')
    marker='<div id="zone-energy-chart">'
    panel=replace(panel,marker,'<div id="zone-coulomb-chart"><h3>Correlação de Coulomb no reservatório · J/m³</h3><canvas id="zone-coulomb-canvas" width="660" height="180" aria-label="Energia interna de Coulomb atual e referência, com valores negativos"></canvas><p>Contribuição de interação ao reservatório. O sinal e a escala adaptativa são preservados; não é um novo Q nuclear.</p></div>\n'+marker)
    (app/'ui/is5-zone-panel.html').write_text(panel,encoding='utf-8')
    index=app/'ui/index.html'
    html=replace(index.read_text(encoding='utf-8'),(BASE/'ui/is5-zone-panel.html').read_text(encoding='utf-8').strip(),panel.strip())
    index.write_text(html.replace('Cadeias pp e CNO-II · zona térmica','Cadeias pp e CNO-II · Coulomb e screening'),encoding='utf-8')
    js=(app/'ui/is5-zone.js').read_text(encoding='utf-8')
    js=replace(js,"decay_basis:$('zone-decay').value,mode:'isochoric_ideal'","mode:'isochoric',include_coulomb:$('zone-coulomb').checked,include_screening:$('zone-screening').checked")
    js=replace(js,"$('zone-decay').value=c.decay_basis;solarZoneFormId=w.artifact_id;", "$('zone-coulomb').checked=c.include_coulomb;$('zone-screening').checked=c.include_screening;zonePhysicsOptions();solarZoneFormId=w.artifact_id;")
    insert='''const zoneFactorValues={};
function zonePhysicsOptions(){if(!$('zone-coulomb').checked)$('zone-screening').checked=false;$('zone-screening').disabled=!$('zone-coulomb').checked;}
$('zone-coulomb').onchange=zonePhysicsOptions;
zoneChannels.forEach((c,i)=>{const row=document.createElement('div');row.className='zone-factor-row';const name=document.createElement('span');name.textContent=zoneChannelLabels[i];const value=document.createElement('span');value.className='zone-factor-value';row.append(name,value);$('zone-screening-table').append(row);zoneFactorValues[c]=value;});
function zoneDrawSigned(canvas,series,index){
  const ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=92,R=20,T=20,B=30;
  ctx.clearRect(0,0,W,H);const values=series.flatMap(s=>s.values).filter(Number.isFinite);let lo=Math.min(...values),hi=Math.max(...values);
  const pad=hi===lo?Math.max(Math.abs(lo)*.05,1):(hi-lo)*.07;lo-=pad;hi+=pad;
  const y=v=>H-B-(H-T-B)*(v-lo)/(hi-lo);ctx.font='12px Segoe UI';ctx.lineWidth=1;ctx.fillStyle='#9eb9ca';ctx.strokeStyle='#24404e';
  for(let j=0;j<=2;j++){const v=lo+(hi-lo)*j/2,yy=y(v);ctx.beginPath();ctx.moveTo(L,yy);ctx.lineTo(W-R,yy);ctx.stroke();ctx.fillText(zoneNumber(v),4,yy+4);}
  if(lo<=0&&hi>=0){ctx.strokeStyle='#526879';ctx.beginPath();ctx.moveTo(L,y(0));ctx.lineTo(W-R,y(0));ctx.stroke();}
  for(const i of [0,120,240])ctx.fillText(String(i),L+(W-L-R)*i/240-7,H-9);
  for(const s of series){ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.reference?1.4:2.2;ctx.setLineDash(s.reference?[6,4]:[]);s.values.forEach((v,i)=>{const x=L+(W-L-R)*i/240;if(i===0)ctx.moveTo(x,y(v));else ctx.lineTo(x,y(v));});ctx.stroke();}
  ctx.setLineDash([]);const x=L+(W-L-R)*index/240;ctx.strokeStyle='#dfedf2';ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,H-B);ctx.stroke();
  for(const s of series.filter(s=>!s.reference)){ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(x,y(s.values[index]),3.2,0,2*Math.PI);ctx.fill();}
}
'''
    js=replace(js,'function zoneGuard()',insert+'function zoneGuard()')
    js=replace(js,"$('zone-temperature-chart').hidden=!view.energy;","$('zone-temperature-chart').hidden=!view.energy;$('zone-coulomb-chart').hidden=!view.energy;")
    js=replace(js,"['composition','branch-composition','b8','cno','temperature','energy','neutrinos']","['composition','branch-composition','b8','cno','temperature','coulomb','energy','neutrinos']")
    js=replace(js,"  if(view.energy)zoneDraw($('zone-energy-canvas')", "  if(view.energy)zoneDrawSigned($('zone-coulomb-canvas'),series([['Coulomb_internal_energy_J_m3','#d8adff']]),i);\n  if(view.energy)zoneDraw($('zone-energy-canvas')")
    js=replace(js,"$('zone-setup-status').textContent=!active?solarZoneError||solarZoneState?.error||'':'';", "$('zone-setup-status').textContent=!active?(busy?'Calculando a zona… O sistema solar continua pausado.':solarZoneError||solarZoneState?.error||''):'';")
    js=replace(js,"  const s=w.sample.actual,r=w.sample.reference,i=w.view.selected_index;", "  const s=w.sample.actual,r=w.sample.reference,i=w.view.selected_index;\n  $('zone-model-reading').textContent='EOS: '+(w.configuration.include_coulomb?'Coulomb PC · íons clássicos':'Mistura ideal FD')+' · Screening: '+(w.configuration.include_screening?'ativo':'desligado');\n  $('zone-screening-reading').textContent='Fatores adicionais de fusão:\\np + p: ×'+zoneNumber(s.screening_factors.pp)+' · N14 + p: ×'+zoneNumber(s.screening_factors.n14pg)+'\\nO16 + p: ×'+zoneNumber(s.screening_factors.o16pg)+'\\nEC Be7 e quatro decaimentos: ×1; lei de plasma EC preservada.';\n  for(const c of zoneChannels)zoneFactorValues[c].textContent='×'+zoneNumber(s.screening_factors[c]);")
    js=replace(js,"+' J/m³\\nCapacidade térmica: '", "+' J/m³\\nCorrelação de Coulomb: '+zoneNumber(s.Coulomb_internal_energy_J_m3)+' J/m³\\nCapacidade térmica: '")
    js=replace(js,"  $('zone-config-fields').disabled=busy;$('zone-visual').disabled=busy;", "  $('zone-config-fields').disabled=busy;$('zone-visual').disabled=busy;$('zone-screening').disabled=busy||!$('zone-coulomb').checked;")
    (app/'ui/is5-zone.js').write_text(js,encoding='utf-8')
    css=app/'ui/is5-zone.css'
    css.write_text(css.read_text(encoding='utf-8')+'\n.zone-factor-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;padding:8px 0;border-bottom:1px solid #29404f;font-size:12px;line-height:1.5}.zone-factor-value{white-space:nowrap;color:#edba79;font-variant-numeric:tabular-nums}#zone-model-reading{color:#c8b1ea}\n',encoding='utf-8')
    (TARGET/'base-manifest.json').write_text(json.dumps(dict(base_source_sha256=originals,
        worker_acceptance_sha256=sha(receipt),scientific_acceptance='is5-coulomb-science-20261028a',
        scope='Unpromoted isolated candidate0.15.0; source models and installed3.13 preserved'),indent=2)+'\n',encoding='utf-8')
    assert all(sha(ROOT/n)==h for n,h in originals.items())
    print(json.dumps(dict(prepared=True,candidate=str(TARGET),base_files=len(originals))))


if __name__=='__main__':main()
