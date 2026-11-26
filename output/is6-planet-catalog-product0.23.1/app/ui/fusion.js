'use strict';
function renderFusionChannels(r){
  const panel=byId('channel-readings'),f=r.fusion,visible=r.influences.some(force=>config.controls[force].visible);
  byId('scene-title').textContent=catalog.scenarios.fusion.choices.mixture[f.mixture];
  const heading=document.createElement('h3');heading.textContent='Canais de reação · taxas e energia';panel.append(heading);
  const note=document.createElement('p');note.className='muted';note.textContent='A curva tracejada acompanha '+r.reference.reference_curve_species+' com todos os canais ligados. Os produtos não reagem novamente neste modelo. A energia liberada fica contabilizada, sem supor deposição local.';panel.append(note);
  const cards=document.createElement('div');cards.className='fusion-channels';
  for(const key of f.channel_order){
    const c=r.reference.channels[key],card=document.createElement('section');card.className='fusion-channel';card.dataset.fusionChannel=key;
    const title=document.createElement('b');title.textContent=c.label;card.append(title);
    const state=document.createElement('span');state.className='fusion-state';state.textContent=f.channels[key]?'Canal ligado':'Canal suprimido';card.append(state);
    const actual=document.createElement('p');actual.dataset.fusionRate=key;card.append(actual);
    if(visible){
      const ref=document.createElement('p');ref.className='muted';ref.dataset.fusionReferenceRate=key;card.append(ref);
      const q=document.createElement('p');q.textContent=`Q do fit: ${format(c.Q_MeV)} MeV · fator de contagem de pares: ${format(c.prefactor)}.`;card.append(q);
      const am=document.createElement('p');am.className='muted';am.textContent=`Q AME2020: ${format(c.Q_AME_keV.value/1000)} MeV; σ independente = ${format(c.Q_AME_keV.standard_uncertainty_independent)} keV. Covariâncias ausentes.`;card.append(am);
      const source=document.createElement('a');source.href=c.source.URL;source.target='_blank';source.rel='noopener noreferrer';source.textContent=`${c.source.Author} · ${c.source.Year} · ${c.fit_label}`;card.append(source);
    }
    const energy=document.createElement('a');energy.href='/nuclear-energy.html?preset='+({ddn:'dd-n',ddp:'dd-p'}[key]||key);energy.textContent='Consultar massas e limiar ↗';energy.className='fusion-mass-link';card.append(energy);cards.append(card);
  }
  panel.append(cards);
  const read=document.createElement('div');read.id='fusion-energy-reading';read.className='fusion-energy-reading';read.setAttribute('aria-live','polite');panel.append(read);
  const title=document.createElement('h3');title.textContent='Composição no instante escolhido';panel.append(title);
  const table=document.createElement('table');table.id='fusion-composition';table.innerHTML='<thead><tr><th>Espécie</th><th>Densidade / m⁻³</th><th>Fração mássica</th></tr></thead>';
  const body=document.createElement('tbody');f.species_labels.forEach((label,i)=>{const row=document.createElement('tr');row.dataset.fusionSpecies=f.species[i];for(const text of [label,'','']){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}body.append(row);});table.append(body);panel.append(table);
  if(visible){
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Ligação por núcleon · referência AME2020';details.append(summary);
    for(const nucleus of f.binding_AME){const q=nucleus.binding_per_nucleon,p=document.createElement('p');p.textContent=`${nucleus.label}: ${format(q.value)} ± ${format(q.uncertainty)} keV/núcleon${q.estimated?' · Estimativa (#)':''}.`;details.append(p);}panel.append(details);
  }
}
function updateFusionReadings(r,index){
  if(!r.fusion)return;
  const f=r.fusion,ref=r.reference.composition,total=f.event_rates_m3_s[index].reduce((a,b)=>a+b,0);
  f.channel_order.forEach((key,i)=>{
    const element=document.querySelector(`[data-fusion-rate="${key}"]`);
    if(element)element.textContent=`Aplicada: ${format(f.event_rates_m3_s[index][i])} reações/(m³·s)${f.channel_order.length>1?` · ${total?format(100*f.event_rates_m3_s[index][i]/total):'0'}% dos eventos ativos`:''}`;
    const reference=document.querySelector(`[data-fusion-reference-rate="${key}"]`);
    if(reference)reference.textContent=`Referência completa: ${format(ref.event_rates_m3_s[index][i])} reações/(m³·s) · Nₐ⟨σv⟩ = ${format(r.reference.channels[key].rate_cm3_mol_s)} cm³/(mol·s).`;
  });
  for(const [i,row] of [...document.querySelectorAll('#fusion-composition tbody tr')].entries()){
    row.children[1].textContent=format(f.number_density_m3[index][i]);row.children[2].textContent=format(f.mass_fractions[index][i]);
  }
  const e=byId('fusion-energy-reading');if(e)e.textContent=`Energia disponível: ${format(f.energy_available_J_m3[index])} J/m³ · Fótons produzidos: ${format(f.photon_count_m3[index])} m⁻³. Deposição não calculada.`;
}
