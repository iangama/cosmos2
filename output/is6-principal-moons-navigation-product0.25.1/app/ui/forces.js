'use strict';
const byId = id => document.getElementById(id);
const labels = {gravity:['Gravidade','◎','Campo 3D e órbita'],electromagnetic:['Eletromagnetismo','⊕','Campos e cargas'],strong:['Nuclear forte','◉','Reação e ligação nuclear'],weak:['Nuclear fraca','β','Decaimento e produtos']};
const sceneLabels = {...labels,binary:['Fontes binárias','◍','Campo somado e marés'],dipole:['Dipolo planetário','∿','Partículas e espelhamento'],geomagnetic:['Campo terrestre','⊙','IGRF14 por posição e época'],stellar:['Região estelar','☀','Rede pp-I e energia'],cno:['Ciclo CNO','↻','Catalisadores e neutrinos'],relativity:['Luz e relógios','◌','Geodésicas e curvatura']};
const curveColors=['#74ddd1','#ffcd87','#df96b9','#a2b8ff','#c5e599','#f3a6ed','#ff9b84','#91d5fb'];
sceneLabels.fusion=['Fusão e canais','⇌','Misturas, produtos e energia'];
sceneLabels.decays=['Decaimentos e cadeias','β','Ramos, alimentação e neutrinos'];
const visibleCurves=new Map();
let catalog, config = {scenario:'gravity',controls:{},parameters:{}}, response, pending = false;
let azimuth = .5, elevation = .35, zoom = 1, pointer, dragDistance = 0, projectedArrows = [];
let animating = false, lastFrame = 0;
let selectedNucleus = null;
let selectedEmParticle = false;
let lastForcesExport = null;
const forceColors={strong:'#ffcd87',weak:'#df96b9',electromagnetic:'#a2b8ff'};
const canvas = byId('science-view'), context = canvas.getContext('2d');
const format = n => n == null ? 'Não se aplica' : n === 0 ? '0' : Math.abs(n)>=1e5 || Math.abs(n)<.001 ? n.toExponential(5) : n.toLocaleString('pt-BR',{maximumSignificantDigits:6});
function status(message,error=false){byId('force-status').textContent=message;byId('force-status').classList.toggle('error',error);}
async function post(path,value){const r=await fetch('/api/forces/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const data=await r.json();if(!r.ok||data.ok===false)throw Error(data.error||'Cálculo recusado.');return data;}
function relevantEffects(){const scenario=catalog.scenarios[config.scenario];return config.scenario==='fusion'?scenario.effect_by_mixture[config.parameters.mixture||'dt']:config.scenario==='decays'?scenario.effect_by_case[config.parameters.parent_case||'f18']:scenario.effect_keys;}
function buildControls(){
  byId('scenarios').replaceChildren();byId('controls').replaceChildren();
  for(const [key,[name,symbol,note]] of Object.entries(sceneLabels).filter(([key])=>catalog.scenarios[key])){
    const button=document.createElement('button');button.dataset.scenario=key;button.className=key===config.scenario?'selected':'';
    button.innerHTML=`<span class="symbol">${symbol}</span><span>${name}<small>${note}</small></span>`;
    button.onclick=()=>{if(pending)return;config.scenario=key;config.parameters={};zoom=1;if(key==='relativity'){azimuth=0;elevation=Math.PI/2;}byId('chart-axis').value=['stellar','cno'].includes(key)?'log':'linear';buildControls();buildParameters();calculate();};byId('scenarios').append(button);
  }
  for(const [key,[name]] of Object.entries(labels)){
    if(!config.controls[key])config.controls[key]={acting:true,visible:true};
    const relevant=Object.hasOwn(relevantEffects(),key);
    const row=document.createElement('div');row.className='force-row'+(relevant?' active':'');
    row.innerHTML=`<div><b>${name}</b><small>${relevant?'Atua neste palco':'Palco próprio'}</small></div><div class="toggles"></div>`;
    for(const [property,title] of [['acting','Atuação'],['visible','Referência']]){
      const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=config.controls[key][property];input.dataset.force=key;input.dataset.control=property;input.setAttribute('aria-label',`${name}: ${title}`);
      input.onchange=()=>{config.controls[key][property]=input.checked;calculate();};label.append(input,document.createTextNode(title));row.querySelector('.toggles').append(label);
    }byId('controls').append(row);
  }buildEffects();
}
function buildEffects(){
  byId('effects').replaceChildren();
  for(const [force,availableKeys] of Object.entries(relevantEffects())){
    const keys=config.scenario==='weak'?[catalog.scenarios.weak.effect_by_species[config.parameters.species||'n']]:availableKeys;
    const control=config.controls[force];control.effects??={};
    if(['stellar','cno','dipole'].includes(config.scenario)){const title=document.createElement('small');title.className='effect-group';title.textContent=labels[force][0];byId('effects').append(title);}
    for(const key of keys){const title=catalog.effects[force][key];
    control.effects[key]??=true;
    const label=document.createElement('label'),input=document.createElement('input');
    label.className='effect-control';input.type='checkbox';input.checked=control.effects[key];input.dataset.effect=key;
    input.onchange=()=>{config.controls[force].effects[key]=input.checked;calculate();};label.append(input,document.createTextNode(title));byId('effects').append(label);
    }
  }
}
function buildParameters(){
  byId('parameters').replaceChildren();
  for(const [key,[value,min,max,title]] of Object.entries(catalog.scenarios[config.scenario].parameters)){
    const label=document.createElement('label');label.dataset.parameter=key;label.textContent=title;const choices=catalog.scenarios[config.scenario].choices?.[key];
    const input=document.createElement(choices?'select':'input');
    if(choices){for(const [optionValue,text] of Object.entries(choices)){const option=document.createElement('option');option.value=optionValue;option.textContent=text;input.append(option);}}
    else{input.type='number';input.min=min;input.max=max;input.step=key==='charge_sign'?2:'any';}
    input.required=true;input.value=config.parameters[key]??value;input.name=key;label.append(input);byId('parameters').append(label);
    if(key==='initial_mode')input.onchange=updateInitialMode;
    if(config.scenario==='fusion'&&key==='mixture')input.onchange=()=>{visibleCurves.delete('fusion');updateFusionParameters();calculate();};
    if(config.scenario==='decays'&&key==='parent_case')input.onchange=()=>{visibleCurves.delete('decays');updateDecayParameters();calculate();};
  }
  updateInitialMode();
  updateFusionParameters();
  updateDecayParameters();
}
function updateDecayParameters(){if(config.scenario!=='decays')return;document.querySelector('[data-parameter="initial_daughter_fraction"]').hidden=byId('parameters').elements.parent_case.value!=='sr90';}
function updateFusionParameters(){byId('fusion-conditions').hidden=byId('fusion-conditions-note').hidden=config.scenario!=='fusion';if(config.scenario!=='fusion')return;document.querySelector('[data-parameter="partner_ratio"]').hidden=catalog.scenarios.fusion.identical_fuels.includes(byId('parameters').elements.mixture.value);}
function updateInitialMode(){if(config.scenario!=='binary')return;const custom=byId('parameters').elements.initial_mode.value==='custom';for(const key of ['x','y','z','vx','vy','vz'])document.querySelector(`[data-parameter="${key}"]`).hidden=!custom;}
function lock(value){pending=value;document.querySelectorAll('aside button,aside input,aside select').forEach(b=>b.disabled=value);}
async function calculate(){
  if(pending||!byId('parameters').reportValidity())return;
  byId('restoration-note').hidden=true;
  config.parameters=Object.fromEntries([...byId('parameters').elements].map(input=>[input.name,input.tagName==='SELECT'?input.value:Number(input.value)]));lock(true);status('Calculando a partir das condições informadas…');
  try{response=await post('evaluate',config);config=response.configuration;['fusion','decays'].includes(config.scenario)?buildControls():buildEffects();byId('time-index').value=240;animating=false;byId('animate').textContent='▶';renderResult();status('Cálculo concluído. Cada controle mantém seu estado ao trocar de palco.');}
  catch(error){status(error.message,true);}finally{lock(false);}
}
function renderResult(){
  const r=response.result;
  byId('scene-title').textContent=catalog.scenarios[config.scenario].name;
  byId('regime').textContent=r.geomagnetic?'CAMPO PRINCIPAL TERRESTRE · ÉPOCA E GEODESIA':r.ray?'RELATIVIDADE GERAL · GEOMETRIA ESFÉRICA':r.positions?'ESPAÇO TRIDIMENSIONAL':'PROCESSO NUCLEAR · EVOLUÇÃO QUANTITATIVA';
  byId('mode-badge').textContent=response.counterfactual?'Contribuição suprimida · hipótese':'Atuação física ligada';byId('mode-badge').classList.toggle('counterfactual',response.counterfactual);
  byId('model').textContent=r.model;byId('domain').textContent=[r.domain,r.parameter_note].filter(Boolean).join(' ');
  byId('dependencies').textContent=r.reference.channel_dependencies||'Este palco calcula a interação selecionada. As demais têm seus próprios cenários; não há acoplamento implícito.';
  byId('measurements').replaceChildren();for(const item of r.measurements){const card=document.createElement('div');card.className='measurement';const label=document.createElement('small');label.textContent=item.label;const value=document.createElement('strong');value.textContent=format(item.value);const unit=document.createElement('em');unit.textContent=item.unit;value.append(unit);card.append(label,value);byId('measurements').append(card);}
  byId('sources').replaceChildren();r.sources.forEach((url,i)=>{const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener';a.textContent=`Fonte ${i+1} · ${new URL(url).hostname}`;byId('sources').append(a);});
  byId('view-help').textContent=r.positions?'Orbitar: arraste · zoom: roda · setas normalizadas; clique para medir':'Curvas calculadas · use a linha do tempo para consultar cada instante';
  byId('scale-label').textContent=r.positions?`1 unidade = ${format(r.position_unit_m)} m`: `Eixo vertical: ${r.curve_axis||'fração da população inicial'}`;
  byId('viewport').dataset.mode=r.positions?'spatial':'nuclear';
  byId('axis-control').hidden=Boolean(r.positions);
  byId('framing-control').hidden=!r.ray&&!r.binary;
  byId('binary-control').hidden=!r.binary;
  byId('em-controls').hidden=config.scenario!=='electromagnetic'||!r.particle_readings;
  byId('dipole-controls').hidden=!r.dipole;
  byId('geomagnetic-controls').hidden=!r.geomagnetic;
  byId('probe-panel').hidden=!r.geomagnetic;
  (r.geomagnetic?byId('probe-panel'):byId('viewport')).append(byId('probe'));
  document.querySelector('.timeline').hidden=Boolean(r.geomagnetic);
  if(r.geomagnetic){geomagneticProbe=null;azimuth=Math.PI/2-config.parameters.longitude_deg*Math.PI/180;elevation=config.parameters.latitude_deg*Math.PI/180;}
  byId('network-control').hidden=!r.network?.event_rates_m3_s||!r.reactions;
  selectedNucleus=null;
  selectedEmParticle=false;
  renderChannels(r);
  renderCurveLegend(r);
  buildNetworkProbes();
  byId('probe').textContent='';draw();
}
function renderCurveLegend(r){
  byId('curve-legend').replaceChildren();
  if(!r.curves)return;
  if(!visibleCurves.has(config.scenario))visibleCurves.set(config.scenario,new Set(r.curves.map((_,i)=>i).filter(i=>config.scenario!=='cno'||[0,1,2,5].includes(i))));
  const selected=visibleCurves.get(config.scenario);
  r.curves.forEach((curve,i)=>{const label=document.createElement('label'),input=document.createElement('input'),value=document.createElement('output');input.type='checkbox';input.checked=selected.has(i);input.dataset.curve=i;input.style.accentColor=curveColors[i%curveColors.length];input.onchange=()=>{input.checked?selected.add(i):selected.delete(i);draw();};value.dataset.curveValue=i;label.style.color=curveColors[i%curveColors.length];label.append(input,document.createTextNode(curve.name+' '),value);byId('curve-legend').append(label);});
}
function renderChannels(r){
  byId('channel-readings').replaceChildren();
  if(r.fusion){renderFusionChannels(r);return;}
  if(r.decays){renderDecayChannels(r);return;}
  if(r.geomagnetic){const p=document.createElement('p');p.textContent=`Época ${formatEpoch(r.geomagnetic.year_decimal)} · altitude WGS84 ${format(r.geomagnetic.altitude_m/1000)} km. Comparação: campo completo e grau 1 dos mesmos coeficientes. Cores usam escala comum do completo; mapa amostrado a cada 10°, sem novas medições pela interpolação gráfica. A força é instantânea, sem órbita ou tempestade simulada. `+r.geomagnetic.full.frame_note;byId('channel-readings').append(p);}
  if(r.dipole){const p=document.createElement('p');const outcome={duration:'Duração solicitada calculada',inner_boundary:'Fronteira interna1R atingida',outer_boundary:'Fronteira externa10R atingida'};p.textContent=`${outcome[r.dipole.status]}. Referência completa: ${outcome[r.dipole.reference_status]}. A fronteira encerra este modelo, sem produto de colisão. ${r.dipole.trace_samples.toLocaleString('pt-BR')} amostras resolvem a giro-órbita; marcadores de medição têm241 instantes.${r.dipole.magnetic_applied?'':' Sem atuação magnética, mudanças de sinal de v·B/|B| usam o campo de referência; não comprovam espelhamento.'}`;byId('channel-readings').append(p);if(config.controls.electromagnetic.visible){const note=document.createElement('p');note.className='muted';note.textContent=`Previsão adiabática: espelho a ±${format(r.reference.adiabatic_mirror_latitude_deg)}° de latitude magnética, raio ${format(r.reference.adiabatic_mirror_radius_R)}R${r.reference.mirror_inside_domain?'':', fora do domínio exterior'}. A órbita é integrada pela força de Lorentz. μ é um diagnóstico aproximado, sem obrigação de conservação exata. Referência tracejada: percurso completo com as duas forças ligadas.`;byId('channel-readings').append(note);}}
  if(r.binary){const p=document.createElement('p');p.textContent=(r.binary.status==='model_boundary'?'Evolução terminou na fronteira de 0,02a; não classificada como colisão ou captura.':'Duração solicitada calculada.')+` L4/L5: ${r.binary.linear_triangular_stability?'estabilidade linear no modelo completo':'instabilidade linear no modelo completo'}. Velocidades iniciais informadas são girantes; a vista inercial converte apenas coordenadas.`;byId('channel-readings').append(p);}
  if(r.ray){
    const states={escaped:'Escapou após o desvio',captured:'Entrou na fronteira de captura',angular_limit:'Limite angular atingido: destino não resolvido',affine_limit:'Limite afim atingido: destino não resolvido',near_critical_unresolved:'Impacto crítico: destino não resolvido na precisão adotada',straight_counterfactual:'Linha reta: termo de curvatura suprimido'};
    const outcome=document.createElement('p');outcome.textContent=`Trajetória: ${states[r.ray.status]}. Referência completa: ${states[r.ray.reference_status]}.`;
    byId('channel-readings').append(outcome);
    if(config.controls.gravity.visible){const note=document.createElement('p');note.className='muted';note.textContent=`Horizonte de referência: rₛ; esfera de fótons: 1,5 rₛ; impacto crítico: ${format(r.reference.critical_impact_rs)} rₛ. Pontos nas cascas 3D medem relógios estáticos e curvatura, sem simular uma folha elástica.`;byId('channel-readings').append(note);}
  }
  if(r.reference.binding_nuclei&&config.controls.strong.visible){
    const heading=document.createElement('h3');heading.textContent='Energia de ligação nuclear · AME2020';byId('channel-readings').append(heading);
    const table=document.createElement('table'),head=document.createElement('thead');
    head.innerHTML='<tr><th>Núcleo</th><th>A / Z</th><th>Ligação por núcleon / MeV</th><th>Ligação total / MeV</th></tr>';table.append(head);
    const body=document.createElement('tbody'),names={d:'D',t:'T',he4:'⁴He'};
    for(const nucleus of r.reference.binding_nuclei){const row=document.createElement('tr');for(const value of [names[nucleus.name],`${nucleus.A} / ${nucleus.Z}`,format(nucleus.binding_MeV_per_nucleon),format(nucleus.binding_total_MeV)]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}body.append(row);}
    table.append(body);byId('channel-readings').append(table);
    const note=document.createElement('p');note.className='muted';note.textContent=`Q por diferença de massas atômicas AME2020: ${format(r.reference.Q_atomic_AME_MeV)} MeV. O balanço da reação usa Q = ${format(r.reference.Q_MeV)} MeV da taxa REACLIB, com seu arredondamento; o modelo não resolve quarks/glúons.`;byId('channel-readings').append(note);
  }
  if(!r.network)return;
  const heading=document.createElement('h3');heading.textContent='Reações e energia no modelo';byId('channel-readings').append(heading);
  const reactions=r.reactions?Object.fromEntries(r.reactions.map(item=>[item.key,[item.reaction,item.force]])):{pp:['p + p → D + e⁺ + ν','weak'],dp:['D + p → ³He + γ','electromagnetic'],he3he3:['³He + ³He → ⁴He + 2p','strong']};
  for(const [name,[reaction,force]] of Object.entries(reactions)){
    const item=document.createElement('p');item.textContent=`${reaction} · ${r.network.channels[name]?'canal ligado':'canal suprimido'} · `;
    const rate=document.createElement('span');rate.dataset.channelRate=name;item.append(rate);
    if(config.controls[force].visible)item.append(document.createTextNode(` · Q de referência ${format(r.reference.channels[name].Q_MeV)} MeV`));
    byId('channel-readings').append(item);
  }
  const assumption=document.createElement('p');assumption.className='muted';assumption.textContent='Deposição supõe aniquilação local de pósitrons e retenção de toda energia exceto neutrinos; a temperatura permanece prescrita. A luminosidade da superfície não é calculada.';byId('channel-readings').append(assumption);
}
function isNetworkView(){return Boolean(response.result.network?.event_rates_m3_s&&response.result.reactions&&byId('network-view').value==='reactions');}
function updateNetworkReadings(r,index){
  if(!r.network)return;
  (r.reactions||[]).forEach((reaction,i)=>{const item=document.querySelector(`[data-channel-rate="${reaction.key}"]`);if(item)item.textContent=`${format(r.network.event_rates_m3_s?.[index][i]??r.network.final_event_rates_m3_s[reaction.key])} reações/(m³·s) no instante escolhido`;});
  if(!selectedNucleus)return;
  const i=r.network.species.indexOf(selectedNucleus),n=r.network.number_per_baryon[index][i]*r.network.baryon_density_m3;
  byId('probe').textContent=`${r.curves[i].name}\nFração mássica: ${format(r.network.mass_fractions[index][i])}\nDensidade numérica: ${format(n)} m⁻³`;
}
function buildNetworkProbes(){
  byId('network-probes').replaceChildren();
  if(!isNetworkView())return;
  response.result.network.species.forEach((name,i)=>{const button=document.createElement('button');button.dataset.nucleus=name;button.textContent=response.result.curves[i].name;button.setAttribute('aria-pressed',String(selectedNucleus===name));button.onclick=()=>{selectedNucleus=name;draw();};byId('network-probes').append(button);});
}
function drawNetwork(r,index,w,h){
  const species=r.network.name==='CNO-I'?r.reactions.map(item=>item.from):r.network.species;
  const radius=Math.min(35,h*.065);
  const locations=new Map();
  species.forEach((name,i)=>{let x,y;if(r.network.name==='CNO-I'){const angle=(-150+i*60)*Math.PI/180;x=w*.5+Math.min(w*.30,h*.68)*Math.cos(angle);y=h*.50+h*.27*Math.sin(angle);}else{x=w*(.17+.66*i/(species.length-1));y=h*.47+(i%2?-.07:.07)*h;}locations.set(name,[x,y]);});
  context.font='11px Segoe UI';context.fillStyle='#aebdcd';context.fillText(`${r.network.name} · relações entre canais, sem escala espacial`,18,25);
  r.reactions.forEach((reaction,i)=>{
    const active=r.network.channels[reaction.key],visible=config.controls[reaction.force].visible;
    if(!active&&!visible)return;
    const a=locations.get(reaction.from),b=locations.get(reaction.to),dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),ux=dx/length,uy=dy/length;
    const start=[a[0]+(radius+3)*ux,a[1]+(radius+3)*uy],end=[b[0]-(radius+3)*ux,b[1]-(radius+3)*uy],color=active?forceColors[reaction.force]:'#64788b';
    context.strokeStyle=color;context.lineWidth=active?2.5:1.2;context.setLineDash(active?[]:[5,5]);context.beginPath();context.moveTo(...start);context.lineTo(...end);context.stroke();context.setLineDash([]);
    const angle=Math.atan2(dy,dx);context.beginPath();context.moveTo(...end);context.lineTo(end[0]-8*Math.cos(angle-.5),end[1]-8*Math.sin(angle-.5));context.moveTo(...end);context.lineTo(end[0]-8*Math.cos(angle+.5),end[1]-8*Math.sin(angle+.5));context.stroke();
    const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2,offset=55,normal=[uy,-ux];
    const x=mx+normal[0]*offset,y=my+normal[1]*offset;
    context.fillStyle=color;context.textAlign='center';context.fillText(reaction.products,x,y);
    const rate=r.network.event_rates_m3_s[index][i];context.fillText(active?`${rate===0?'0':rate.toExponential(2)} m⁻³s⁻¹`:'Canal suprimido',x,y+15);
    if(visible){context.fillStyle='#9eacbd';context.fillText(`Q = ${r.reference.channels[reaction.key].Q_MeV.toFixed(3)} MeV`,x,y+29);}
  });
  species.forEach(name=>{const [x,y]=locations.get(name),i=r.network.species.indexOf(name);context.fillStyle=selectedNucleus===name?'#174147':'#112839';context.strokeStyle=selectedNucleus===name?'#74ddd1':'#456174';context.lineWidth=1.5;context.beginPath();context.arc(x,y,radius,0,Math.PI*2);context.fill();context.stroke();context.fillStyle=curveColors[i%curveColors.length];context.textAlign='center';context.font='17px Segoe UI';context.fillText(r.curves[i].name.replace('Fração mássica de ',''),x,y-3);context.font='10px Segoe UI';context.fillStyle='#d4e0e8';context.fillText(r.network.mass_fractions[index][i].toExponential(2),x,y+15);projectedArrows.push({x,y,nucleus:name});});
  context.textAlign='left';
  byId('view-help').textContent='Clique num núcleo ou use os botões para medir · setas mostram canais e taxas calculadas';
  byId('scale-label').textContent='Nós: fração mássica · setas: reações/(m³·s)';
}
function project(v,w,h,center){
  const x=v[0]-center[0],y=v[1]-center[1],z=v[2]-center[2];
  const a=Math.cos(azimuth)*x-Math.sin(azimuth)*y,b=Math.sin(azimuth)*x+Math.cos(azimuth)*y;
  return [w*.5+a*zoom,w? h*.48+(Math.sin(elevation)*b-Math.cos(elevation)*z)*zoom:0,Math.cos(elevation)*b+Math.sin(elevation)*z];
}
function rotateView(v,phase){const c=Math.cos(phase),s=Math.sin(phase);return [c*v[0]-s*v[1],s*v[0]+c*v[1],v[2]];}
function readEmParticle(index){const r=response.result,read=r.particle_readings;if(!read)return;byId('probe').textContent=`Partícula no instante escolhido\nVelocidade: ${format(Math.hypot(...read.velocity_m_s[index]))} m/s\nForça elétrica: ${format(Math.hypot(...read.electric_force_N[index]))} N\nForça magnética: ${format(Math.hypot(...read.magnetic_force_N[index]))} N\nPotência elétrica: ${format(read.electric_power_W[index])} W\nPotência magnética: ${format(read.magnetic_power_W[index])} W\nK − K₀ = ${format(read.kinetic_energy_J[index]-read.kinetic_energy_J[0])} J\nTrabalho elétrico: ${format(read.electric_work_J[index])} J`;}
function readDipoleParticle(index){const r=response.result,p=r.particle_readings;byId('probe').textContent=`Partícula no instante escolhido\nB de referência: ${format(Math.hypot(...p.magnetic_field_T[index]))} T\nVelocidade: ${format(Math.hypot(...p.velocity_m_s[index]))} m/s\nComponente ao longo de B: ${format(p.parallel_velocity_m_s[index])} m/s\nPitch: ${format(p.pitch_deg[index])}°\nForça magnética aplicada: ${format(Math.hypot(...p.magnetic_force_N[index]))} N\nForça gravitacional aplicada: ${format(Math.hypot(...p.gravity_force_N[index]))} N\nPotência magnética: ${format(p.magnetic_power_W[index])} W\nK+U aplicado: ${format(p.total_energy_J[index])} J`;}
function draw(){
  if(!response)return;
  const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);context.setTransform(dpr,0,0,dpr,0,0);
  const w=rect.width,h=rect.height,r=response.result,index=Number(byId('time-index').value);
  if(r.geomagnetic){drawGeomagnetic(r,w,h);return;}
  const control=config.controls[catalog.scenarios[config.scenario].force];
  const showReference=r.influences.some(force=>config.controls[force].visible);
  const timeUnit=r.time_display||{unit:'s',seconds_per_unit:1};
  byId('time-label').textContent=`${timeUnit.symbol||'t'} = ${format(r.time_s[index]/timeUnit.seconds_per_unit)} ${timeUnit.unit}`;
  const networkView=isNetworkView();
  const spatial=Boolean(r.positions)&&!(r.dipole&&byId('dipole-view').value==='curves');
  byId('curve-legend').hidden=Boolean(r.dipole)&&spatial;
  byId('reference-entry').hidden=Boolean(r.dipole)&&!spatial;
  if(r.dipole){byId('scale-label').textContent=spatial?`1 unidade = ${format(r.position_unit_m)} m`:r.curve_axis;if(!spatial)byId('view-help').textContent='Curvas calculadas · selecione medições e use a linha do tempo';}
  byId('viewport').dataset.mode=networkView?'network':spatial?'spatial':'nuclear';
  byId('axis-control').hidden=spatial||networkView;
  if(networkView){projectedArrows=[];drawNetwork(r,index,w,h);}
  else if(spatial){
    const inertial=r.binary&&byId('binary-view').value==='inertial',positions=inertial?r.inertial_positions:r.positions,referencePositions=inertial?r.inertial_reference_positions:r.reference_positions;
    const viewVector=v=>inertial?rotateView(v,r.phase_rad[index]):v;
    const all=positions.concat(referencePositions),mins=[0,1,2].map(k=>Math.min(-2,...all.map(p=>p[k]))),maxs=[0,1,2].map(k=>Math.max(2,...all.map(p=>p[k])));
    const focus=(r.ray||r.binary)&&byId('framing').value==='focus';
    const center=focus?[0,0,0]:mins.map((v,k)=>(v+maxs[k])/2),range=focus?2*(r.view_extent||2.6):Math.max(...maxs.map((v,k)=>v-mins[k]));const userZoom=zoom;zoom=userZoom*Math.min(w,h)*.8/range;
    const p=v=>project(v,w,h,center);projectedArrows=[];
    if(r.dipole?showReference:control.visible){
      let fields=r.field;
      if(r.dipole){const chosen=byId('dipole-field').value;fields=fields.filter(f=>config.controls[f.force].visible&&(chosen==='both'||f.kind===chosen));}
      if(config.scenario==='electromagnetic'&&r.particle_readings){const selected=byId('em-field').value,electric=r.field.map(f=>({position:f.position,vector:r.electric_field_Vm,unit:'V/m',kind:'electric'}));fields=selected==='magnetic'?r.field:selected==='electric'?electric:[...r.field,...electric];}
      for(const field of fields){const position=viewVector(field.position),vector=viewVector(field.vector),a=p(position),m=Math.hypot(...vector);if(m===0)continue;const direction=vector.map(v=>v/m);const b=p(position.map((v,k)=>v+direction[k]*.23));
        context.strokeStyle=field.kind==='electric'?'rgba(255,205,135,.7)':field.kind==='gravity'?'rgba(255,205,135,.55)':'rgba(127,168,213,.5)';context.lineWidth=1;context.beginPath();context.moveTo(a[0],a[1]);context.lineTo(b[0],b[1]);context.stroke();const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);context.beginPath();context.moveTo(b[0],b[1]);context.lineTo(b[0]-5*Math.cos(angle-.5),b[1]-5*Math.sin(angle-.5));context.moveTo(b[0],b[1]);context.lineTo(b[0]-5*Math.cos(angle+.5),b[1]-5*Math.sin(angle+.5));context.stroke();projectedArrows.push({x:a[0],y:a[1],field});
      }
      path(r.dipole?r.dipole.reference_trace:referencePositions,'#b2a1fa',1.5,true);
      for(const probe of r.metric_probes||[]){const a=p(probe.position);context.fillStyle=`hsla(${190+80*probe.static_clock_ratio},65%,70%,.65)`;context.beginPath();context.arc(a[0],a[1],3,0,Math.PI*2);context.fill();projectedArrows.push({x:a[0],y:a[1],metric:probe});}
    }
    if(r.dipole){let lo=0,hi=r.dipole.trace_time_s.length;while(lo<hi){const mid=(lo+hi)>>1;if(r.dipole.trace_time_s[mid]<=r.time_s[index])lo=mid+1;else hi=mid;}path(r.dipole.trace.slice(0,lo),'#74ddd1',2.4,false);if(config.controls.electromagnetic.visible)for(const line of r.dipole.field_lines)path(line,'#688baa55',.8,false);for(const plane of [0,1,2]){const ring=Array.from({length:97},(_,i)=>{const a=i*2*Math.PI/96,v=[Math.cos(a),Math.sin(a),0];return plane===0?v:plane===1?[v[0],0,v[1]]:[0,v[0],v[1]];});path(ring,'#b1c4cc',1.5,false);}context.fillStyle='#adbccc';context.font='11px Segoe UI';context.fillText('Dipolo ideal prescrito · esfera1R em escala física · sem IGRF',18,25);byId('view-help').textContent='Arraste para orbitar · clique num vetor para medir · use as curvas para investigar o espelhamento';}
    else path(positions.slice(0,index+1),'#74ddd1',2.4,false);
    if(r.binary){
      r.binary.source_positions.forEach((v,i)=>{const a=p(viewVector(v));context.fillStyle=i?'#ffbb87':'#ffe1a0';context.beginPath();context.arc(a[0],a[1],i?7:10,0,Math.PI*2);context.fill();context.font='11px Segoe UI';context.fillText(`Fonte ${i+1}`,a[0]+12,a[1]-10);});
      if(control.visible){for(const point of r.binary.lagrange_points){const a=p(viewVector(point.position));context.strokeStyle='#ae9ec9';context.lineWidth=1;context.beginPath();context.moveTo(a[0]-4,a[1]);context.lineTo(a[0]+4,a[1]);context.moveTo(a[0],a[1]-4);context.lineTo(a[0],a[1]+4);context.stroke();context.fillStyle='#b5a4cd';context.font='10px Segoe UI';context.fillText(point.name,a[0]+7,a[1]-6);}const f=r.binary.probe,a=p(viewVector(f.position));context.fillStyle='#a5f4e5';context.beginPath();context.arc(a[0],a[1],5,0,Math.PI*2);context.fill();projectedArrows.push({x:a[0],y:a[1],field:f});}
      context.fillStyle='#adbccc';context.font='11px Segoe UI';context.fillText(inertial?'Baricentro inercial · fontes e campo giram':'Referencial girante · fontes fixas na vista',18,26);
      context.fillText(`Massas nominais: ${format(config.parameters.primary_solar)} e ${format(config.parameters.primary_solar*config.parameters.mass_ratio)} Sol · tamanhos ampliados`,18,43);
    }
    if(config.scenario==='gravity'){const a=p([0,0,0]);const gradient=context.createRadialGradient(a[0],a[1],0,a[0],a[1],25);gradient.addColorStop(0,'#ffe4a7');gradient.addColorStop(.3,'#f3a951');gradient.addColorStop(1,'#d18a3000');context.fillStyle=gradient;context.beginPath();context.arc(a[0],a[1],25,0,Math.PI*2);context.fill();context.fillStyle='#d5bd92';context.font='11px Segoe UI';context.fillText('Fonte · tamanho ampliado',a[0]+17,a[1]-16);}
    if(r.ray){
      for(const plane of [0,1,2]){const ring=(radius)=>Array.from({length:97},(_,i)=>{const angle=2*Math.PI*i/96,v=[radius*Math.cos(angle),radius*Math.sin(angle),0];return plane===0?v:plane===1?[v[0],0,v[1]]:[0,v[0],v[1]];});path(ring(1),'#cfc5eb',1.3,false);if(control.visible)path(ring(1.5),'#a59acb',1,true);}
      context.fillStyle='#c6bcdf';context.font='12px Segoe UI';context.fillText('rₛ: horizonte · 1,5 rₛ: esfera de fótons',18,27);
      byId('view-help').textContent='Arraste para orbitar · clique nas sondas de relógio/curvatura · enquadramento altera apenas a vista';
    }
    const position=p(positions[index]);context.fillStyle='#e4fffa';context.beginPath();context.arc(position[0],position[1],4,0,Math.PI*2);context.fill();
    if(r.binary)byId('view-help').textContent=position[0]<0||position[0]>w||position[1]<0||position[1]>h?'Partícula fora da vista · selecione Trajetória completa para acompanhar':'Arraste para orbitar · clique nas sondas · enquadramento e referencial alteram apenas a vista';
    if(config.scenario==='electromagnetic'&&control.visible){context.fillStyle='#aebee8';context.font='12px Segoe UI';context.fillText(`B = ${format(r.reference.B_T)} T, eixo z · E = ${format(r.reference.E_Vm)} V/m, eixo x`,18,28);}
    zoom=userZoom;
    function path(points,color,width,dashed){context.strokeStyle=color;context.lineWidth=width;context.setLineDash(dashed?[5,5]:[]);context.beginPath();points.forEach((v,i)=>{const q=p(v);i?context.lineTo(q[0],q[1]):context.moveTo(q[0],q[1]);});context.stroke();context.setLineDash([]);}
  }else{
    projectedArrows=[];const left=60,right=w-24,top=44,bottom=h-84;
    const logarithmic=byId('chart-axis').value==='log',floor=config.scenario==='cno'?-28:config.scenario==='stellar'?-22:-6;
    const selected=visibleCurves.get(config.scenario);
    const ceiling=r.dipole?Math.max(1.1,...r.curves.filter((_,i)=>selected.has(i)).flatMap(curve=>curve.values.map(v=>v*1.05))):1;
    const logTop=Math.log10(ceiling);
    const vertical=value=>logarithmic?(Math.log10(value)-floor)/(logTop-floor):value/ceiling;
    byId('scale-label').textContent=`Eixo vertical: ${r.curve_axis||'fração da população inicial'} · ${logarithmic?'log₁₀':'linear'}`;
    byId('view-help').textContent=logarithmic?'Escala logarítmica: zeros e valores abaixo do eixo não são desenhados · os dados exportados são completos':'Curvas calculadas · use a linha do tempo para consultar cada instante';
    context.font='11px Segoe UI';context.lineWidth=1;
    for(let i=0;i<=4;i++){const y=bottom-(bottom-top)*i/4;context.strokeStyle='#283c50';context.beginPath();context.moveTo(left,y);context.lineTo(right,y);context.stroke();context.fillStyle='#9aacbe';context.textAlign='left';context.fillText(logarithmic?`10^${format(floor+(logTop-floor)*i/4)}`:format(ceiling*i/4),12,y+4);const t=r.time_s[240]*i/4/timeUnit.seconds_per_unit;context.textAlign=i===0?'left':i===4?'right':'center';context.fillText(format(t),left+(right-left)*i/4,bottom+24);}context.textAlign='left';
    context.fillText(`tempo / ${timeUnit.unit}`,w/2,bottom+46);
    const graph=(values,color,dashed,limit)=>{context.strokeStyle=color;context.lineWidth=2;context.setLineDash(dashed?[6,4]:[]);context.beginPath();let connected=false;values.slice(0,limit+1).forEach((v,i)=>{const level=vertical(v);if(!Number.isFinite(level)||level<0||level>1){connected=false;return;}const x=left+(right-left)*i/240,y=bottom-level*(bottom-top);connected?context.lineTo(x,y):context.moveTo(x,y);connected=true;});context.stroke();context.setLineDash([]);};
    if(showReference&&r.reference_curve)graph(r.reference_curve,'#b2a1fa',true,240);
    r.curves.forEach((curve,i)=>{if(selected.has(i))graph(curve.values,curveColors[i%curveColors.length],false,index);byId('curve-legend').querySelector(`[data-curve-value="${i}"]`).textContent=format(curve.values[index]);});
    const x=left+(right-left)*index/240;context.strokeStyle='#98b6c455';context.beginPath();context.moveTo(x,top);context.lineTo(x,bottom);context.stroke();
    context.fillStyle='#aebdcd';context.fillText(r.dipole?'Dipolo · razões adimensionais · escolha as curvas abaixo':r.decays?'Pais e filhos · populações esperadas':r.fusion?'Combustíveis e produtos · frações mássicas':r.network?`${r.network.name||'pp-I'} · frações mássicas · escolha as curvas abaixo`:'População restante e produtos · frações iniciais',18,23);
    if(!selectedNucleus)byId('probe').textContent=r.dipole||r.probe_kind==='composition'?'':`Restantes: ${format(r.curves[0].values[index]*100)}% · Produtos: ${format(r.curves[1].values[index]*100)}%`;
  }
  if(r.curves)r.curves.forEach((curve,i)=>{byId('curve-legend').querySelector(`[data-curve-value="${i}"]`).textContent=format(curve.values[index]);});
  updateNetworkReadings(r,index);
  updateFusionReadings(r,index);
  updateDecayReadings(r,index);
  if(selectedEmParticle)r.dipole?readDipoleParticle(index):readEmParticle(index);
  byId('network-probes').querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(selectedNucleus===button.dataset.nucleus)));
}
canvas.onpointerdown=e=>{pointer=[e.clientX,e.clientY];dragDistance=0;canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{if(!pointer||(!response?.result.positions&&!response?.result.geomagnetic))return;if(response.result.geomagnetic&&byId('geomagnetic-view').value==='map')return;const dx=e.clientX-pointer[0],dy=e.clientY-pointer[1];dragDistance+=Math.abs(dx)+Math.abs(dy);azimuth+=dx*.008;elevation=Math.max(-1.4,Math.min(1.4,elevation+dy*.008));pointer=[e.clientX,e.clientY];draw();};
canvas.onpointerup=e=>{pointer=null;if(dragDistance>5)return;const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;const closest=projectedArrows.map(a=>({...a,d:Math.hypot(a.x-x,a.y-y)})).sort((a,b)=>a.d-b.d)[0];if(closest&&closest.d<35){selectedEmParticle=false;if(closest.geomagnetic){geomagneticProbe=closest.geomagnetic;readGeomagneticProbe(geomagneticProbe);}else if(closest.nucleus){selectedNucleus=closest.nucleus;draw();}else if(closest.metric){const m=closest.metric;byId('probe').textContent=`Referência · r = ${format(m.radius_rs)} rₛ\nRelógio estático / infinito: ${format(m.static_clock_ratio)} s/s\nKretschmann: ${format(m.kretschmann_m_minus4)} m⁻⁴`;}else{const f=closest.field;byId('probe').textContent=`Campo de referência: ${format(Math.hypot(...f.vector))} ${f.unit||response.result.field_unit}\nPosição${response.result.binary?' girante':''}: ${f.position.map(v=>format(v*response.result.position_unit_m)).join(', ')} m`;if(f.potential_m2_s2!=null)byId('probe').textContent+=`\nPotencial: ${format(f.potential_m2_s2)} m²/s²\nMaré (autovalores): ${(f.tidal_eigenvalues_s2||[]).map(format).join(', ')||'Não exibida neste palco'} s⁻²\nAceleração aplicada: ${format(Math.hypot(...f.applied_vector))} m/s²`;}}};
canvas.onwheel=e=>{e.preventDefault();zoom=Math.max(.4,Math.min(3,zoom*Math.exp(-e.deltaY*.001)));draw();};
new ResizeObserver(draw).observe(canvas);
byId('parameters').onsubmit=e=>{e.preventDefault();calculate();};byId('calculate').onclick=calculate;
byId('time-index').oninput=()=>{animating=false;byId('animate').textContent='▶';draw();};
byId('chart-axis').onchange=draw;
byId('framing').onchange=draw;
byId('network-view').onchange=()=>{selectedNucleus=null;byId('probe').textContent='';buildNetworkProbes();draw();};
byId('binary-view').onchange=()=>{byId('probe').textContent='';draw();};
byId('em-field').onchange=()=>{selectedEmParticle=false;byId('probe').textContent='';draw();};
byId('dipole-view').onchange=()=>{byId('probe').textContent='';draw();};
byId('dipole-field').onchange=()=>{selectedEmParticle=false;byId('probe').textContent='';draw();};
byId('measure-dipole').onclick=()=>{selectedEmParticle=true;readDipoleParticle(Number(byId('time-index').value));};
for(const id of ['geomagnetic-view','geomagnetic-model','geomagnetic-component'])byId(id).onchange=()=>{geomagneticProbe=null;draw();};
byId('center-geomagnetic').onclick=()=>{const point=geomagneticProbe||response.result.geomagnetic[byId('geomagnetic-model').value];azimuth=Math.PI/2-point.longitude_deg*Math.PI/180;elevation=point.latitude_deg*Math.PI/180;draw();};
byId('measure-particle').onclick=()=>{selectedEmParticle=true;draw();};
byId('animate').onclick=()=>{animating=!animating;if(animating&&Number(byId('time-index').value)===240)byId('time-index').value=0;byId('animate').textContent=animating?'Ⅱ':'▶';};
function frame(time){if(animating&&response&&time-lastFrame>40){let index=Number(byId('time-index').value)+1;byId('time-index').value=index;if(index>=240){animating=false;byId('animate').textContent='▶';}draw();lastFrame=time;}requestAnimationFrame(frame);}requestAnimationFrame(frame);
byId('save-forces').onclick=async()=>{try{await post('save',config);status('Condições, controles, modelo e fontes salvos. Retomar recalcula os resultados e verifica a geração científica.');}catch(e){status(e.message,true);}};
byId('fusion-conditions').onclick=()=>{if(pending||config.scenario!=='fusion')return;const preset=catalog.scenarios.fusion.comparison_conditions[byId('parameters').elements.mixture.value];for(const [key,value] of Object.entries(preset))byId('parameters').elements[key].value=value;calculate();};
byId('load-forces').onclick=async()=>{try{const saved=await post('load',{});config=saved.configuration;buildControls();buildParameters();await calculate();if(byId('force-status').classList.contains('error'))return;const restoration=saved.restoration,note=byId('restoration-note');note.hidden=false;note.dataset.state=restoration?.status||'unknown_generation';if(restoration?.status==='same_generation')note.textContent='Condições retomadas. Modelo, fontes e versões correspondem ao registro salvo; resultados recalculados.';else if(restoration?.status==='changed_generation')note.textContent='Condições retomadas com uma geração científica diferente. '+restoration.differences.map(d=>`${({code:'código',data:'dados',runtime:'ferramenta',model:'modelo'})[d.kind]}: ${d.name}`).join('; ')+'. Os resultados foram recalculados com a versão atual.';else note.textContent='Registro antigo sem geração científica. Condições retomadas e resultados recalculados com o modelo e as fontes atuais.';}catch(e){status(e.message,true);}};
byId('export-forces').onclick=async()=>{if(!response||pending)return;lock(true);try{lastForcesExport=await post('export',config);status('JSON exportado em '+lastForcesExport.export_file);}catch(e){status(e.message,true);}finally{lock(false);}};
window.addEventListener('hashchange',()=>{const key=location.hash.slice(1);if(catalog&&Object.hasOwn(catalog.scenarios,key)&&key!==config.scenario)document.querySelector(`[data-scenario="${key}"]`)?.click();});
(async()=>{try{const r=await fetch('/api/forces/catalog');if(!r.ok)throw Error('O servidor de forças não respondeu.');catalog=await r.json();const initialScenario=location.hash.slice(1);if(Object.hasOwn(catalog.scenarios,initialScenario)){config.scenario=initialScenario;config.parameters={};}buildControls();buildParameters();await calculate();}catch(e){status(e.message,true);}})();
