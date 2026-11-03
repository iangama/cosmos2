'use strict';
let socket, sequence = 0;
let appState = null, pending = false;
let labIdentity=null;
let massDirty=false;
let atlasState=null,selectedTarget='Earth',atlasPending=false;
const $ = id => document.getElementById(id);
const views = {
  Earth: {anchor:'Earth', position:[17674090.653605793,-1566585.5066504919,18170644.716643292], name:'Terra', radius:'6.378 km', surface:'NASA Blue Marble', description:'Oceanos, continentes e luzes noturnas em um globo com dimensões reais.'},
  Moon: {anchor:'Moon', position:[-4500000,-5000000,3000000], name:'Lua', radius:'1.737 km', surface:'LRO WAC', description:'A paisagem lunar registrada pela câmera da Lunar Reconnaissance Orbiter.'},
  Saturn: {anchor:'Saturn',position:[2e8,-1.5e8,1.6e8],name:'Saturno',radius:'60.268 km',surface:'Mapa visual OpenSpace',description:'Centro planetário SAT441 + DE442s e elipsoide PCK. Mapa e perfis de anéis OpenSpace com época/origem observacional não confirmadas; sem evolução atmosférica ou dinâmica de partículas.'},
  System: {anchor:'Earth', position:[190000000,-600000000,320000000], name:'Terra e Lua', radius:'Consultando…', measure:'SEPARAÇÃO NA ÉPOCA', surface:'NASA / LRO', description:'Posições geométricas JPL DE442s. Tamanhos e distâncias não são ampliados para caber na imagem.'},
  Galaxy: {anchor:'MilkyWayVolume',position:[0,-8e20,9e20],name:'Via Láctea',radius:'8 kpc²',measure:'CENTRO AO SOL',surface:'Modelo NAOJ',description:'Uma representação volumétrica baseada em simulação, com gás, poeira e estrelas. ² Distância adotada por este modelo; não é uma fotografia da nossa galáxia.'}
};
function script(code) {
  if (!socket || socket.readyState !== WebSocket.OPEN) { $('notice').textContent='Aguardando conexão com o renderizador.'; return false; }
  socket.send(JSON.stringify({topic:++sequence,type:'luascript',payload:{script:code,return:false}}));
  return true;
}
function selectTarget(target,quiet=false) {
  const v = views[target];
  if (!v) return;
  selectedTarget=target;
  $('sunlit-view').hidden=!['Earth','Moon','Saturn'].includes(target);
  $('object-name').textContent=v.name; $('radius').textContent=v.radius; $('surface').textContent=v.surface; $('object-description').textContent=v.description;
  $('measure-label').textContent=v.measure||'RAIO DE REFERÊNCIA';
  document.querySelectorAll('[data-target]').forEach(b=>b.classList.toggle('active',b.dataset.target===target));
  if(!quiet)$('notice').textContent='Selecionado: '+v.name+'. Use Visitar para mover a câmera.';
}
async function visit(target){selectTarget(target);await navigate('visit',{target,smooth:$('smooth-flight').checked});}
function connect() {
  socket = new WebSocket('ws://127.0.0.1:4682');
  socket.onopen=()=>{socket.send(JSON.stringify({type:'apiHandshake',apiVersion:{major:1,minor:0,patch:0}}));$('led').classList.add('ready');$('connection').textContent='Motor conectado';};
  socket.onclose=()=>{$('led').classList.remove('ready');$('connection').textContent='Reconectando…';setTimeout(connect,1500);};
  socket.onerror=()=>socket.close();
  socket.onmessage=e=>{try{const data=JSON.parse(e.data);if(data.status==='error'||data.type==='error')$('notice').textContent='O comando não foi aceito. Consulte o registro da sessão.';}catch{}};
}
document.querySelectorAll('[data-target]').forEach(b=>b.onclick=()=>selectTarget(b.dataset.target));
$('home').onclick=()=>visit('Earth');
$('sunlit-view').onclick=()=>{
  if(!atlasState||!['Earth','Moon','Saturn'].includes(selectedTarget))return;
  navigate('visit',{target:selectedTarget,sunlit:true,smooth:false});
};
$('capture').onclick=()=>{if(script('openspace.takeScreenshot()'))$('notice').textContent='Captura solicitada. Pasta: user/screenshots.';};
$('search').oninput=()=>filterDestinations();
connect();

function mode(value) {
  const lab = value === 'experiment';
  $('scene-targets').hidden=lab;
  if(lab){$('scene-targets').replaceChildren();$('free-look').hidden=true;if(window.clearFree)clearFree();}
  for (const id of ['atlas-panel','atlas-details']) $(id).hidden=lab;
  for (const id of ['lab-panel','lab-details']) $(id).hidden=!lab;
  $('atlas').classList.toggle('selected',!lab);$('experiment').classList.toggle('selected',lab);
}
async function command(request, success, path='/api/command') {
  if (pending) return;
  pending=true;$('lab-controls').disabled=true;$('experiment').disabled=true;$('atlas').disabled=true;$('copy-atlas').disabled=true;$('apply-atlas-epoch').disabled=true;
  $('notice').textContent='Aplicando comando…';
  try {
    const response = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Não foi possível aplicar o comando.');
    if(['load_experiment','set_mass','set_body','create_body','remove_body','new_system','restart_seed','reset','load','restart_atlas'].includes(request.command)||path==='/api/atlas/experiment')massDirty=false;
    $('notice').textContent=success;
    await updateState();
    return result;
  } catch(error) { $('notice').textContent=error.message; }
  finally {pending=false;$('lab-controls').disabled=false;$('experiment').disabled=false;$('atlas').disabled=false;$('copy-atlas').disabled=!atlasState||atlasPending;$('apply-atlas-epoch').disabled=atlasPending;if(appState?.physics){if(window.updateBodyEditor)updateBodyEditor(appState.physics);if(window.updateBodyAttributes)updateBodyAttributes(appState.physics,appState.display);if(window.updateOrbitEditor)updateOrbitEditor(appState.physics,appState.orbit_preview);if(window.updateGravityExperience)updateGravityExperience(appState.physics);if(window.updateGravityProbe)updateGravityProbe(appState.physics,appState.probe_preview);if(window.updateGravityInstruments)updateGravityInstruments(appState.physics,appState.instruments_preview);}}
}
async function updateState() {
  const response=await fetch('/api/state');
  if(!response.ok)throw new Error('Servidor local indisponível.');
  appState=await response.json();mode(appState.mode);
  const p=appState.physics;
  $('load').disabled=!appState.checkpoint_available;
  if (!p) return;
  const initial=p.atlas_initial,identity=p.system_id,custom=p.origin_kind==='user_system';
  if(labIdentity!==identity){labIdentity=identity;massDirty=false;$('atlas-fixture-option').hidden=!initial;$('atlas-fixture-option').disabled=!initial;$('user-fixture-option').hidden=!custom;$('user-fixture-option').disabled=!custom;$('fixture').value=initial?'atlas':custom?'user':String(p.fixture_count);}
  $('lab-origin').hidden=!initial;$('lab-epoch').hidden=!initial;$('lab-earth-moon').hidden=!p.bodies.some(b=>b.reference_id==='sol:naif:399')||!p.bodies.some(b=>b.reference_id==='sol:naif:301');
  $('lab-intro').textContent=(p.experiment?'Modelo definido: '+p.experiment.definition.label+'. ':initial?'Origem: cópia Sol/Terra/Lua do Atlas. ':custom?'Sistema definido por você, sem época absoluta. ':'Origem: cenário de teste determinístico. ')+p.bodies.length+' corpos ativos; todos interagem pela gravitação newtoniana. Criações e remoções são intervenções externas.';
  $('mass-label').textContent='Massa de '+p.bodies[0].name+' / massa solar nominal';
  $('lab-grid-note').textContent=(initial?'Referencial fixo: baricentro inicial dos três corpos, eixos J2000. ':custom?'Referencial inercial definido pelo usuário, sem recentrar. ':'Referencial do baricentro inicial do cenário. ')+(appState.display?.physical_radii?'Esferas com raio SI definido; orientação cinemática.':'Marcadores ampliados; grade apenas visual.');
  if(initial){
    const e=initial.source.epoch;
    $('lab-epoch').textContent=`Época inicial UTC: ${e.utc}. Duração do experimento começa em zero.`;
    $('lab-origin-reading').textContent=`JPL DE442s · ${e.utc}\nTDB inicial: ${e.et_tdb_s.toLocaleString('pt-BR',{maximumFractionDigits:3})} s desde J2000.\nFonte SSB/J2000 → baricentro inicial dos três corpos. A referência JPL permanece independente.\nRamificação: ${initial.branch_id}`;
    $('lab-exclusions').textContent='Influências excluídas: '+p.contract.excluded_influences.join('; ')+'.';
    $('lab-source-GM').replaceChildren();for(const b of initial.bodies){const row=document.createElement('p');row.textContent=`${b.name} · ${b.reference_id}\nGM de origem: ${b.source_GM.raw_value_km3_s2} km³/s²`;row.dataset.referenceId=b.reference_id;$('lab-source-GM').append(row);}
  }else $('lab-source-GM').replaceChildren();
  $('lab-restoration').hidden=!p.restoration;
  if(p.restoration)$('lab-restoration').textContent=p.restoration.status==='same_generation'?'Checkpoint retomado com a mesma geração científica.':'Checkpoint retomado com geração científica diferente. As condições de origem foram preservadas.';
  $('play').textContent=p.paused?'Iniciar':'Pausar';
  $('lab-state').textContent=p.integration_notice?'PAUSADO NO LIMITE DO MODELO':p.experiment_horizon_reached?'HORIZONTE RECOMENDADO ATINGIDO':p.paused?'EXPERIMENTO PAUSADO':'GRAVITAÇÃO EM MOVIMENTO';
  $('body-count').textContent=p.bodies.length;
  const time=p.physical_scale?p.time*p.physical_scale.time_unit_s/3600:p.time;
  $('sim-time').textContent=time.toLocaleString('pt-BR',{minimumFractionDigits:3,maximumFractionDigits:3})+(p.physical_scale?' h':' u');
  const physicalRate=p.physical_scale?p.effective_rate*p.physical_scale.time_unit_s/3600:p.effective_rate;
  $('effective-rate').textContent=physicalRate.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})+(p.physical_scale?' h/s':' u/s');
  if(p.physical_scale)for(const option of $('rate').options)option.textContent=(Number(option.value)*p.physical_scale.time_unit_s/3600).toLocaleString('pt-BR',{maximumFractionDigits:3})+' h/s';
  if(p.physical_scale)$('unit-note').textContent=`1 unidade de distância = ${(p.physical_scale.length_unit_m/1000).toLocaleString('pt-BR')} km; de tempo = ${p.physical_scale.time_unit_s.toLocaleString('pt-BR',{maximumFractionDigits:2})} s. Massa por GM solar nominal. Gravidade pontual, sem colisões; ${appState.display?.physical_radii?"esferas geométricas com raio SI definido":"marcadores ampliados"}.`;
  $('energy-error').textContent=p.energy_error===null?'ΔE '+p.energy_error_absolute.toExponential(2)+' u':p.energy_error.toExponential(2);
  if(window.updateBodyEditor)updateBodyEditor(p);
  if(window.updateBodyAttributes)updateBodyAttributes(p,appState.display);
  if(window.updateOrbitEditor)updateOrbitEditor(p,appState.orbit_preview);
  if(window.updateGravityExperience)updateGravityExperience(p);
  if(window.updateGravityProbe)updateGravityProbe(p,appState.probe_preview);
  if(window.updateGravityInstruments)updateGravityInstruments(p,appState.instruments_preview);
  $('revision').textContent=p.revision;
  $('ack-latency').textContent=appState.command_latency_ms===null?'—':appState.command_latency_ms.toFixed(1)+' ms';
  if(!massDirty&&document.activeElement!==$('mass'))$('mass').value=p.bodies[0].mass;
  if(document.activeElement!==$('rate'))$('rate').value=p.requested_rate;
  if(appState.error)$('notice').textContent=appState.error;
  else if(p.integration_notice)$('notice').textContent=p.integration_notice;
}
$('experiment').onclick=()=>command({command:'enter'},'Experimento pronto. Inicie a evolução ou altere a massa.');
$('atlas').onclick=()=>command({command:'atlas'},'Atlas restaurado. O experimento foi pausado.');
$('play').onclick=()=>command({command:appState?.physics?.paused?'resume':'pause'},'Comando confirmado pelo processo físico.');
$('reset').onclick=()=>command(['atlas','user'].includes($('fixture').value)?{command:'restart_seed'}:{command:'reset',count:Number($('fixture').value)},'Cenário reiniciado e pausado.');
$('rate').onchange=()=>command({command:'rate',value:Number($('rate').value)},'Ritmo solicitado atualizado; confira o ritmo efetivo.');
$('apply-mass').onclick=()=>{
  if(!$('mass').reportValidity())return;
  command({command:'set_mass',body:appState?.physics?.bodies[0]?.id||'p0',mass:Number($('mass').value)},'Massa alterada. Intervenção registrada; experimento pausado.');
};
$('save').onclick=()=>command({command:'save'},'Sessão salva em user/sessions.');
$('mass').oninput=()=>{massDirty=true;};
$('load').onclick=()=>command({command:'load'},'Sessão restaurada e pausada.');
function frameLab(region){
  const p=appState?.physics;if(!p)return;
  const u=p.physical_scale.length_unit_m,matrix=p.atlas_initial?.j2000_to_render_frame;
  const positions=p.bodies.map(b=>matrix?matrix.map(row=>row.reduce((sum,x,k)=>sum+x*b.position[k]*u,0)):b.position.map(v=>v*u));
  const earth=p.bodies.findIndex(b=>b.reference_id==='sol:naif:399'),moon=p.bodies.findIndex(b=>b.reference_id==='sol:naif:301');
  let labels=p.bodies.map(b=>'openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Size",'+(region==='earth-moon'?6:9)+');openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Text",'+JSON.stringify(Array.from(b.name).length<=24?b.name:Array.from(b.name).slice(0,23).join('')+'…')+');openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Enabled",'+false+');').join('');
  if(region==='earth-moon'&&earth>=0&&moon>=0){
    const delta=positions[moon].map((v,k)=>v-positions[earth][k]),distance=Math.hypot(...delta);if(distance===0)return;
    const direction=delta.map(v=>v/distance);let side=[-direction[1],direction[0],0],norm=Math.hypot(...side);if(norm<1e-8){side=[1,0,0];norm=1;}
    const camera=direction.map((v,k)=>distance*3*(.3*v+.954*side[k]/norm));
    labels+=[earth,moon].map(i=>'openspace.setPropertyValueSingle("Scene.'+p.bodies[i].label_node+'.Renderable.Enabled",true);').join('');
    script(labels+'openspace.navigation.setNavigationState({Anchor="'+p.bodies[earth].scene_node+'",ReferenceFrame="LabRoot",Position={'+camera.join(',')+'},Up={0,0,1}})');
  }else{
    const center=[0,1,2].map(k=>(Math.min(...positions.map(v=>v[k]))+Math.max(...positions.map(v=>v[k])))/2);
    const distance=Math.max(p.display_min_view_distance_m||3e9,2.2*Math.max(...positions.map(v=>Math.hypot(...v.map((x,k)=>x-center[k])))));
    if(p.bodies[0].origin.kind!=='deterministic_fixture')labels+='openspace.setPropertyValueSingle("Scene.'+p.bodies[0].label_node+'.Renderable.Enabled",true);';
    script(labels+'openspace.navigation.setNavigationState({Anchor="LabFrame",ReferenceFrame="LabRoot",Position={0,'+(-distance)+','+(distance*.6)+'},Up={0,0,1}})');
  }
}
$('lab-home').onclick=()=>frameLab('system');$('lab-earth-moon').onclick=()=>frameLab('earth-moon');
$('copy-atlas').onclick=()=>{if(!atlasState||atlasPending||pending)return;command({utc:atlasState.epoch.utc},'Cópia Sol/Terra/Lua pronta e pausada. Origem e influências excluídas estão registradas.','/api/atlas/experiment');};
$('forces').onclick=async()=>{
  if(pending)return;
  if(appState?.mode==='experiment'){
    const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'pause'})});
    if(!r.ok){$('notice').textContent='Não foi possível pausar o laboratório.';return;}
  }
  location.href='/forces.html';
};
$('open-content').onclick=async()=>{
  if(pending)return;
  if(appState?.mode==='experiment'){
    const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'pause'})});
    if(!r.ok){$('notice').textContent='Não foi possível pausar o laboratório.';return;}
  }
  location.href=selectedTarget==='Galaxy'?'/content.html?view=packages':'/content.html?body='+({Moon:'301',Saturn:'699'}[selectedTarget]||'399');
};
async function poll(){try{await updateState();}catch{if(!pending)$('notice').textContent='Aguardando o servidor local do Cosmos2…';}setTimeout(poll,250);}
poll();

function displayAtlas(data){
  atlasState=data;
  $('copy-atlas').disabled=pending||atlasPending;
  const distance=(data.earth_moon_separation_m/1000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' km';
  $('moon-distance').textContent=distance+' da Terra nesta época';views.System.radius=distance;
  if(selectedTarget==='System')$('radius').textContent=distance;
  if(document.activeElement!==$('atlas-epoch'))$('atlas-epoch').value=data.epoch.utc.replace('Z','').split('.')[0];
  $('atlas-time-reading').textContent=`${data.renderer.paused?'Pausado':'Em movimento'} · ${data.epoch.utc}\nTDB: ${data.epoch.et_tdb_s.toLocaleString('pt-BR',{maximumFractionDigits:3})} s desde J2000. UTC conforme LSK fixo; segundos intercalares futuros desconhecidos.`;
}
$('atlas-epoch-form').onsubmit=async e=>{
  e.preventDefault();if(atlasPending||pending||!$('atlas-epoch').reportValidity())return;
  atlasPending=true;$('apply-atlas-epoch').disabled=true;$('copy-atlas').disabled=true;$('notice').textContent='Calculando e confirmando a época no motor…';
  try{let utc=$('atlas-epoch').value;if(utc.length===16)utc+=':00';const r=await fetch('/api/atlas/epoch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({utc})});const data=await r.json();if(!r.ok||!data.ok)throw Error(data.error||'Não foi possível alterar a época.');displayAtlas(data.atlas);$('notice').textContent='Época confirmada. Atlas pausado; posições e iluminação atualizadas.';}
  catch(error){$('notice').textContent=error.message;}finally{atlasPending=false;$('apply-atlas-epoch').disabled=false;$('copy-atlas').disabled=pending||!atlasState;}
};
$('export-atlas').onclick=async()=>{
  if(pending||!atlasState)return;$('export-atlas').disabled=true;
  try{const r=await fetch('/api/atlas/export',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}),data=await r.json();if(!r.ok||!data.ok)throw Error(data.error||'Exportação recusada.');$('notice').textContent='Estado e fontes salvos: '+data.export_file;}
  catch(error){$('notice').textContent=error.message;}finally{$('export-atlas').disabled=false;}
};
async function pollAtlas(){
  try{if(!atlasPending&&(!appState||appState.mode==='atlas')){const r=await fetch('/api/atlas/state'),data=await r.json();if(!r.ok)throw Error(data.error);displayAtlas(data);}}
  catch(error){$('atlas-time-reading').textContent='Estado do Atlas indisponível: '+error.message;}
  setTimeout(pollAtlas,1000);
}pollAtlas();
