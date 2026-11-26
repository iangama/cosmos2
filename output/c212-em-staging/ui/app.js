'use strict';
const $=id=>document.getElementById(id),canvas=$('view'),ctx=canvas.getContext('2d');
let state=null,pending=false,map=null,azimuth=.6,elevation=.4,drag=null,arrows=[],trail=[],identity=null,formIdentity=null,lastExport=null,lastArtifact=null;
const number=v=>Number(v).toExponential(6),vector=v=>v.map(number).join(' / ');
const run=action=>Promise.resolve().then(action).catch(e=>{$('status').textContent=e.message;});
function guard(){return {system_id:state.system_id,edit_token:state.edit_token,revision:state.revision,frame:state.frame,expected_time_s:state.time_s};}
async function refresh(){const value=await(await fetch('/api/state')).json();state=value.state;if(state)render();}
async function command(command,args={}){
  if(pending)return;pending=true;render();
  try{const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,...args})});const value=await r.json();if(!r.ok)throw Error(value.error);await refresh();$('status').textContent='Comando confirmado: '+command;return value;}
  catch(e){$('status').textContent=e.message;throw e;}finally{pending=false;render();}
}
function positions(){const p=state.experiment.phase;return state.experiment.mode==='test_particle'?[p.position_m]:p.position_m;}
function render(){
  if(!state)return;const ex=state.experiment,mutual=ex.mode==='mutual_electrostatic',id=state.system_id+state.edit_token;
  if(identity!==id){identity=id;trail=[];map=null;lastExport=null;azimuth=state.editor.visual.azimuth_rad;elevation=state.editor.visual.elevation_rad;$('reading').textContent='Clique numa seta do mapa para medir.';}
  const p=positions()[0];if(!trail.length||trail[trail.length-1].time!==state.time_s){trail.push({p,time:state.time_s});if(trail.length>2048)trail.shift();}
  $('play').textContent=state.paused?'Iniciar':'Pausar';$('time').textContent='t = '+number(state.time_s)+' s';
  $('magnetic-acting-label').hidden=mutual;$('acting-e').checked=mutual?ex.controls.acting:ex.controls.electric_acting;$('acting-b').checked=mutual?false:ex.controls.magnetic_acting;
  $('model-note').textContent=mutual?positions().length+' cargas ativas trocam força elétrica. Sem campo magnético próprio, radiação ou gravidade.':'Partícula de teste em fontes fixas, sem reação nas fontes. Regime não relativístico, v ≤ 0,01c.';
  document.querySelectorAll('button').forEach(e=>e.disabled=pending);
  for(const id of ['acting-e','acting-b'])$(id).disabled=pending||!state.paused;
  for(const [id,key] of [['visible-e','electric_visible'],['visible-b','magnetic_visible']]){if(!pending)$(id).checked=state.editor.visual[key];$(id).disabled=pending;}
  renderEditor();
  const stale=map&&(map.system_id!==state.system_id||map.edit_token!==state.edit_token||map.revision!==state.revision||map.time_s!==state.time_s);
  $('map-state').textContent=map?(stale?'MAPA CONGELADO · estado mudou desde a medição. ':'Mapa do instante confirmado. ')+map.samples.length+' posições; t = '+number(map.time_s)+' s.':'Meça para criar uma casca 3D e um corte de referência.';
  if(state.notice)$('status').textContent=state.notice;draw();
}
function draw(){
  if(!state)return;const box=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);canvas.width=box.width*dpr;canvas.height=box.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);const w=box.width,h=box.height,scale=Math.min(w,h)/11;
  const project=p=>{const x=Math.cos(azimuth)*p[0]-Math.sin(azimuth)*p[1],y=Math.sin(azimuth)*p[0]+Math.cos(azimuth)*p[1];return [w/2+scale*x,h/2-scale*(Math.cos(elevation)*p[2]-Math.sin(elevation)*y)];};
  function line(a,b,color,width=1){const p=project(a),q=project(b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();return [p,q];}
  for(let k=0;k<3;k++){const p=[0,0,0],q=[0,0,0];p[k]=-4;q[k]=4;line(p,q,'#2b4153');}
  for(let i=1;i<trail.length;i++)line(trail[i-1].p,trail[i].p,'#78ddd2',2);
  const ex=state.experiment,sources=ex.mode==='test_particle'?ex.model.sources.map(s=>s.position_m):positions();
  sources.forEach((p,index)=>{const q=project(p),sid=ex.mode==='test_particle'?ex.model.sources[index].id:ex.system.ids[index];ctx.fillStyle='#ffd184';ctx.beginPath();ctx.arc(...q,7,0,2*Math.PI);ctx.fill();if(sid===state.editor.visual.selected_id){ctx.strokeStyle='#ffffff';ctx.beginPath();ctx.arc(...q,11,0,2*Math.PI);ctx.stroke();}});
  for(const p of positions()){const q=project(p);ctx.fillStyle='#78ddd2';ctx.beginPath();ctx.arc(...q,5,0,2*Math.PI);ctx.fill();}
  arrows=[];for(const sample of map?.samples||[]){if(!sample.valid)continue;for(const [id,key,color] of [['visible-e','electric_field_V_m','#ffd184'],['visible-b','magnetic_field_T','#9eacff']]){if(!$(id).checked)continue;const v=sample[key],m=Math.hypot(...v);if(!m)continue;const end=sample.position_m.map((x,k)=>x+.35*v[k]/m),[a,b]=line(sample.position_m,end,color),angle=Math.atan2(b[1]-a[1],b[0]-a[0]);ctx.beginPath();ctx.moveTo(b[0]-5*Math.cos(angle-.5),b[1]-5*Math.sin(angle-.5));ctx.lineTo(...b);ctx.lineTo(b[0]-5*Math.cos(angle+.5),b[1]-5*Math.sin(angle+.5));ctx.stroke();arrows.push({x:a[0],y:a[1],sample});}}
}
$('load-preset').onclick=()=>run(async()=>{await command('pause');await command('load_preset',{...guard(),preset:$('preset').value});});
$('play').onclick=()=>run(()=>command(state.paused?'resume':'pause'));
for(const id of ['acting-e','acting-b'])$(id).onchange=()=>run(()=>command('set_controls',{...guard(),controls:state.experiment.mode==='test_particle'?{electric_acting:$('acting-e').checked,magnetic_acting:$('acting-b').checked}:{acting:$('acting-e').checked}}));
for(const [id,key] of [['visible-e','electric_visible'],['visible-b','magnetic_visible']])$(id).onchange=()=>{const checked=$(id).checked;run(()=>command('set_visual',{...guard(),changes:{[key]:checked}}));};
$('measure').onclick=()=>run(async()=>{
  await command('pause');const points=[];
  const radius=state.editor.visual.map_radius_m,cut=state.editor.visual.map_cut_z_m;
  for(let k=0;k<48;k++){const z=1-2*(k+.5)/48,a=k*Math.PI*(3-Math.sqrt(5)),r=Math.sqrt(1-z*z);points.push([radius*r*Math.cos(a),radius*r*Math.sin(a),radius*z]);}
  for(let i=-3;i<=3;i++)for(let j=-3;j<=3;j++)points.push([i*radius/3,j*radius/3,cut]);
  const result=await command('field_map',{...guard(),points_m:points});if(result){map=result.result;render();}
});
$('save').onclick=()=>run(async()=>{await command('pause');await command('save',{...guard(),file:'ui-phase'});});
$('restore').onclick=()=>run(async()=>{await command('pause');await command('load',{...guard(),file:'ui-phase'});});
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY,0];canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];drag=[e.clientX,e.clientY,drag[2]+Math.abs(dx)+Math.abs(dy)];azimuth+=dx*.008;elevation=Math.max(-1.4,Math.min(1.4,elevation+dy*.008));draw();};
canvas.onpointerup=e=>{const moved=drag?.[2]||0;drag=null;if(moved>5){run(()=>command('set_visual',{...guard(),changes:{azimuth_rad:azimuth,elevation_rad:elevation}}));return;}const box=canvas.getBoundingClientRect(),x=e.clientX-box.left,y=e.clientY-box.top;const a=arrows.map(a=>({...a,d:Math.hypot(a.x-x,a.y-y)})).sort((a,b)=>a.d-b.d)[0];if(a&&a.d<30)showReading(a.sample,map.time_s,'Leitura do mapa');};

function formVector(prefix,suffixes){return suffixes.map(k=>{const input=$(prefix+k);if(input.value.trim()===''||!Number.isFinite(input.valueAsNumber))throw Error('Preencha componentes SI finitas.');return input.valueAsNumber;});}
function setVector(prefix,suffixes,values){suffixes.forEach((k,i)=>$(prefix+k).value=values[i]);}
function renderEditor(){
  const ex=state.experiment,mutual=ex.mode==='mutual_electrostatic',editor=state.editor,selected=editor.visual.selected_id;
  const ids=mutual?ex.system.ids:ex.model.sources.map(s=>s.id),key=identity+'|'+state.revision+'|'+selected+'|'+(state.paused?state.time_s:'running');
  if(formIdentity!==key){
    formIdentity=key;const select=$('source-select');select.replaceChildren(new Option(mutual?'Nova carga ativa':'Nova fonte fixa',''));
    ids.forEach(id=>select.add(new Option(id,id)));select.value=selected||'';
    let s=selected?(mutual?(()=>{const i=ids.indexOf(selected);return {id:selected,position_m:ex.phase.position_m[i],velocity_m_s:ex.phase.velocity_m_s[i],charge_C:ex.system.charge_C[i],mass_kg:ex.system.mass_kg[i],exclusion_radius_m:ex.system.exclusion_radius_m[i]};})():ex.model.sources.find(s=>s.id===selected)):{id:'',position_m:[0,0,0],velocity_m_s:[0,0,0],charge_C:mutual?1e-7:1e-9,mass_kg:1,exclusion_radius_m:.1,magnetic_moment_A_m2:[0,0,0]};
    $('source-id').value=s.id;setVector('source-',['x','y','z'],s.position_m);$('source-charge').value=s.charge_C;$('source-radius').value=s.exclusion_radius_m;
    if(mutual){$('source-mass').value=s.mass_kg;setVector('source-v',['x','y','z'],s.velocity_m_s);}else{setVector('source-m',['x','y','z'],s.magnetic_moment_A_m2);setVector('background-e',['x','y','z'],ex.model.uniform_E_V_m);setVector('background-b',['x','y','z'],ex.model.uniform_B_T);}
    $('map-radius').value=editor.visual.map_radius_m;$('map-cut').value=editor.visual.map_cut_z_m;
  }
  $('dipole-fields').hidden=mutual;$('body-fields').hidden=!mutual;$('background-editor').hidden=mutual;
  $('apply-source').textContent=selected?'Aplicar alteração':mutual?'Criar carga':'Criar fonte';
  $('source-origin').textContent=selected?'Origem: '+(editor.origins[selected]==='user_model'?'modelo do usuário':'preset sintético'):'Nova identidade · modelo do usuário';
  document.querySelectorAll('#editor input,#editor select,#editor button').forEach(e=>e.disabled=pending||!state.paused);
  $('source-id').disabled=pending||!state.paused||selected!==null;$('remove-source').disabled=pending||!state.paused||selected===null;
  $('editor-hint').textContent=state.paused?'Alterações validadas por inteiro antes de aplicar.':'Experimento evoluindo. Pause para editar fontes ou cargas.';
  const d=state.diagnostics;$('diagnostics').textContent='Energia mecânica: '+number(d.mechanical_energy_J)+' J\nCarga total do modelo: '+number(d.total_charge_C)+' C\nMomento linear: '+vector(d.momentum_kg_m_s)+' kg m/s\nMomento angular: '+vector(d.angular_momentum_kg_m2_s)+' kg m²/s';
  const event=editor.interventions.at(-1);$('intervention').textContent=event?'Última intervenção · t = '+number(event.time_s)+' s · revisão '+event.revision_after+'\nΔenergia mecânica: '+number(event.delta.mechanical_energy_J)+' J\nΔcarga: '+number(event.delta.total_charge_C)+' C\nΔmomento linear: '+vector(event.delta.momentum_kg_m_s)+' kg m/s\nΔmomento angular: '+vector(event.delta.angular_momentum_kg_m2_s)+' kg m²/s\nReferência de conservação reiniciada. Histórico: '+editor.interventions.length+'; anteriores fora do limite: '+editor.dropped_interventions: 'Sem intervenções físicas neste experimento.';
}
$('source-select').onchange=()=>{const id=$('source-select').value;run(()=>command('set_visual',{...guard(),changes:{selected_id:id||null}}));};
$('source-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  const mutual=state.experiment.mode==='mutual_electrostatic',selected=state.editor.visual.selected_id;
  const source={id:$('source-id').value,position_m:formVector('source-',['x','y','z']),charge_C:formVector('source-',['charge'])[0],exclusion_radius_m:formVector('source-',['radius'])[0]};
  if(mutual){source.mass_kg=formVector('source-',['mass'])[0];source.velocity_m_s=formVector('source-v',['x','y','z']);}else source.magnetic_moment_A_m2=formVector('source-m',['x','y','z']);
  const changes={...source};delete changes.id;
  await command('edit',{...guard(),edit:selected?{operation:mutual?'update_body':'update_source',id:selected,changes}:{operation:mutual?'create_body':'create_source',[mutual?'body':'source']:source}});
  await command('set_visual',{...guard(),changes:{selected_id:source.id}});
});};
$('remove-source').onclick=()=>run(()=>command('edit',{...guard(),edit:{operation:state.experiment.mode==='mutual_electrostatic'?'remove_body':'remove_source',id:state.editor.visual.selected_id}}));
$('background-form').onsubmit=e=>{e.preventDefault();run(()=>command('edit',{...guard(),edit:{operation:'set_background',changes:{uniform_E_V_m:formVector('background-e',['x','y','z']),uniform_B_T:formVector('background-b',['x','y','z'])}}}));};
$('map-form').onsubmit=e=>{e.preventDefault();run(()=>command('set_visual',{...guard(),changes:{map_radius_m:formVector('map-',['radius'])[0],map_cut_z_m:formVector('map-',['cut'])[0]}}));};
function showReading(s,time,label){$('reading').textContent=s.valid?label+' · t = '+number(time)+' s\nPosição: '+vector(s.position_m)+' m\nE: '+vector(s.electric_field_V_m)+' V/m\nB: '+vector(s.magnetic_field_T)+' T\nPotencial elétrico: '+number(s.electric_potential_V)+' V':label+' fora do domínio: '+s.source_ids.join(', ');}
$('probe').onclick=()=>run(async()=>{await command('pause');const result=await command('probe',{...guard(),position_m:formVector('probe-',['x','y','z'])});if(result)showReading(result.result,state.time_s,'Sonda confirmada');});
$('export').onclick=()=>run(async()=>{await command('pause');const result=await command('export_sample',{...guard(),position_m:formVector('probe-',['x','y','z'])});if(!result)return;lastExport=result.result;lastArtifact=result.artifact;showReading(lastExport.sample,lastExport.time_s,'Leitura exportada');const a=document.createElement('a');a.href=lastArtifact.url;a.download='cosmos2-em-fontes-leitura.json';a.click();$('export-state').textContent='JSON salvo e disponível · t = '+number(lastExport.time_s)+' s · revisão '+lastExport.revision+' · '+lastExport.frame;});
new ResizeObserver(draw).observe(canvas);setInterval(()=>refresh().catch(e=>$('status').textContent=e.message),100);refresh();
