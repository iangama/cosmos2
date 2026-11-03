'use strict';
const decayModeNames={beta_minus:'β−',beta_plus:'β+',electron_capture:'Captura eletrônica'};
function renderDecayChannels(r){
  const panel=byId('channel-readings'),d=r.decays,visible=config.controls.weak.visible;
  byId('scene-title').textContent=catalog.scenarios.decays.choices.parent_case[config.parameters.parent_case];
  const heading=document.createElement('h3');heading.textContent='Avaliação usada e comparação de fontes';panel.append(heading);
  const note=document.createElement('p');note.className='muted';note.textContent='O cálculo usa ENSDF/LiveChart. NUBASE2020 é outra avaliação, mostrada para comparação. Os valores e as ramificações de uma fonte não substituem parcialmente os da outra. A linha tracejada acompanha '+r.reference.reference_curve_species+' com todos os canais ligados.';panel.append(note);
  const evaluations=document.createElement('div');evaluations.className='decay-evaluations';
  for(const [key,p] of Object.entries(r.reference.parents)){
    const card=document.createElement('section');card.className='decay-evaluation';card.dataset.decayParent=key;
    const title=document.createElement('b');title.textContent=p.label;card.append(title);
    const half=document.createElement('p');half.textContent=`ENSDF: ${format(p.half_life_s)} ± ${format(p.half_life_uncertainty_s)} s.`;card.append(half);
    const comparison=document.createElement('p');comparison.textContent=`NUBASE2020: ${format(p.NUBASE2020_comparison.half_life_s)} ± ${format(p.NUBASE2020_comparison.uncertainty_s)} s.`;card.append(comparison);
    const original=document.createElement('p');original.className='muted';original.textContent=`Original NUBASE: ${p.NUBASE2020_comparison.half_life_raw} ${p.NUBASE2020_comparison.unit_raw}; ${p.NUBASE2020_comparison.modes_raw}. Ano tropical na conversão.`;card.append(original);
    const provenance=document.createElement('p');provenance.className='muted';provenance.textContent=`ENSDF: ${p.ENSDF_ground_state.ENSDFauthors}; cutoff ${p.ENSDF_ground_state['ENSDFpublicationcut-off']}. Extração ${p.ENSDF_ground_state.Extraction_date}; não é data de medição.`;card.append(provenance);
    const norm=document.createElement('p');norm.className='muted';norm.textContent=`Soma dos percentuais impressos: ${p.printed_total_intensity_percent.toLocaleString('pt-BR',{useGrouping:false,maximumFractionDigits:9})}%. Fator de normalização: ${p.branch_normalization_factor.toPrecision(10).replace('.',',')}. Suprimir um canal preserva as larguras dos outros.`;card.append(norm);
    evaluations.append(card);
  }
  panel.append(evaluations);
  const branchTitle=document.createElement('h3');branchTitle.textContent='Ramos, alimentação e produtos';panel.append(branchTitle);
  const branches=document.createElement('div');branches.className='decay-branches';
  for(const key of d.channel_order){
    const c=r.reference.channels[key],card=document.createElement('section');card.className='decay-branch';card.dataset.decayBranch=key;
    const title=document.createElement('b');title.textContent=r.reference.parents[c.parent].label+' → '+c.daughter_label+' · '+decayModeNames[c.mode];card.append(title);
    const level=document.createElement('p');level.className='muted';level.textContent=`Nível filho: ${format(c.daughter_excitation_keV)} keV · ${d.channels[key]?'Canal ligado':'Canal suprimido'}.`;card.append(level);
    const rate=document.createElement('p');rate.dataset.decayRate=key;card.append(rate);
    if(visible){
      const ref=document.createElement('p');ref.className='muted';ref.dataset.decayReferenceRate=key;card.append(ref);
      const probability=document.createElement('p');probability.textContent=`Percentual impresso: ${format(c.printed_intensity_percent)}%; aplicado antes de supressão: ${(100*c.probability).toPrecision(8)}%.`;card.append(probability);
      const energy=document.createElement('p');energy.textContent=`Q atômico: ${format(c.Q.value)} keV · energia ${c.mode==='electron_capture'?'nominal aproximada':'média'} do ${c.mode==='beta_minus'?'antineutrino':'neutrino'}: ${format(c.neutrino_energy.value)} keV.`;card.append(energy);
      const uncertainty=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Incertezas registradas na fonte';uncertainty.append(summary);
      const uncertaintyText=document.createElement('p');uncertaintyText.className='muted';uncertaintyText.textContent=`Intensidade: ${c.intensity_uncertainty_raw||'não informada'} (campo original). Energia ν: ${c.neutrino_energy.uncertainty_raw||'não informada'} (campo original). Incerteza Q: ${c.Q.uncertainty_raw||'não informada'} (notação original ENSDF, sem conversão nesta bancada). Os campos brutos e a linha completa ficam no JSON; não são propagados às curvas nem interpretados como erro numérico.`;uncertainty.append(uncertaintyText);card.append(uncertainty);
      if(c.independent_source_energy_residual_keV!=null){const residual=document.createElement('p');residual.className='muted';residual.textContent=`Resíduo Q − excitação − médias e/ν − par: ${format(c.independent_source_energy_residual_keV)} keV. Valores de referência independentes, sem ajuste para fechar o balanço.`;card.append(residual);}
    }
    const products=document.createElement('p');products.className='muted';products.textContent=c.mode==='beta_minus'?'Produto leptônico: elétron e antineutrino eletrônico.':c.mode==='beta_plus'?'Produto leptônico: pósitron e neutrino eletrônico.':'Um elétron atômico é consumido e um neutrino eletrônico é emitido.';card.append(products);
    branches.append(card);
  }
  panel.append(branches);
  const composition=document.createElement('h3');composition.textContent='Populações no instante escolhido';panel.append(composition);
  const table=document.createElement('table');table.id='decay-populations';table.innerHTML='<thead><tr><th>Espécie</th><th>População esperada</th><th>Atividade / Bq</th></tr></thead>';
  const body=document.createElement('tbody');d.labels.forEach((name,i)=>{const row=document.createElement('tr');row.dataset.decayNode=d.node_ids[i];for(const text of [name,'','']){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}body.append(row);});table.append(body);panel.append(table);
  const readings=document.createElement('div');readings.id='decay-readings';readings.setAttribute('aria-live','polite');panel.append(readings);
  const warning=document.createElement('p');warning.className='muted';warning.textContent='Q = energia de neutrinos + restante disponível é a contabilidade deste modelo. O restante não é calor depositado nem somente energia do elétron. Filhos são agregados por A/Z; relaxação gamma e aniquilação não são evoluídas. Médias beta e Q da fonte podem apresentar discrepâncias, preservadas nos ramos.';panel.append(warning);
}
function updateDecayReadings(r,index){
  if(!r.decays)return;
  const d=r.decays,full=r.reference.full_evolution;
  d.channel_order.forEach((key,j)=>{
    const element=document.querySelector(`[data-decay-rate="${key}"]`);
    if(element)element.textContent=`Aplicada: ${format(d.event_rates_s[index][j])} eventos/s · acumulado ${format(d.channel_event_counts[index][j])}.`;
    const reference=document.querySelector(`[data-decay-reference-rate="${key}"]`);
    if(reference)reference.textContent=`Referência completa: ${format(full.event_rates_s[index][j])} eventos/s.`;
  });
  for(const [i,row] of [...document.querySelectorAll('#decay-populations tbody tr')].entries()){
    row.children[1].textContent=format(d.populations[index][i]);
    const parent=d.parents.findIndex(k=>r.reference.parents[k].node_id===d.node_ids[i]);
    row.children[2].textContent=parent<0?'Terminal no modelo':format(d.activity_s[index][parent]);
  }
  const panel=byId('decay-readings');if(!panel)return;panel.replaceChildren();
  for(const [name,value,unit] of [['Neutrinos eletrônicos',d.electron_neutrino_count[index],'partículas esperadas'],['Antineutrinos eletrônicos',d.electron_antineutrino_count[index],'partículas esperadas'],['Elétrons emitidos',d.electron_count[index],'partículas esperadas'],['Pósitrons emitidos',d.positron_count[index],'partículas esperadas'],['Elétrons capturados',d.captured_electron_count[index],'partículas esperadas'],['Energia disponível Q',d.energy_available_J[index],'J'],['Energia de neutrinos',d.energy_neutrino_J[index],'J'],['Restante disponível',d.energy_non_neutrino_available_J[index],'J']]){
    const card=document.createElement('div'),label=document.createElement('small'),reading=document.createElement('strong'),suffix=document.createElement('small');label.textContent=name;reading.textContent=format(value);suffix.textContent=unit;card.append(label,reading,suffix);panel.append(card);
  }
}
