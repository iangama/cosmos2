'use strict';
let bodyEditSnapshot=null,bodyEditIds='';
function editGuard(p){return {system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,expected_time:p.time,frame:p.contract.frame};}
function clearBodyEditor(){bodyEditSnapshot=null;$('body-edit-fields').disabled=true;$('body-edit-status').textContent='Pause e prepare o estado antes de aplicar.';}
function updateBodyEditor(p){
  const ids=p.system_id+'|'+p.edit_token+'|'+p.bodies.map(b=>b.id).join('|');
  if(ids!==bodyEditIds){
    const selected=$('edit-body').value;bodyEditIds=ids;clearBodyEditor();$('edit-body').replaceChildren();
    for(const b of p.bodies){const o=document.createElement('option');o.value=b.id;o.textContent=b.name;$('edit-body').append(o);}
    if(p.bodies.some(b=>b.id===selected))$('edit-body').value=selected;
  }
  const operation=$('edit-operation').value;
  const stale=bodyEditSnapshot&&(p.time!==bodyEditSnapshot.expected_time||p.revision!==bodyEditSnapshot.revision||p.system_id!==bodyEditSnapshot.system_id||p.edit_token!==bodyEditSnapshot.edit_token);
  $('apply-body-edit').disabled=pending||!bodyEditSnapshot||!p.paused||Boolean(stale)||(operation==='create'&&p.bodies.length>=256);
  $('remove-edit-body').disabled=pending||p.bodies.length<=1||operation!=='edit';
  $('edit-name-field').hidden=operation==='edit';$('edit-name').required=operation!=='edit';
  $('apply-body-edit').textContent=operation==='edit'?'Aplicar estado e pausar':operation==='create'?'Acrescentar corpo e pausar':'Iniciar novo sistema com este corpo';
  if(stale)$('body-edit-status').textContent='O sistema evoluiu, mudou ou foi restaurado. Pause e prepare novamente antes de aplicar.';
  const event=p.interventions.at(-1),supported=['set_body_si','create_body','remove_body'].includes(event?.type);
  $('body-edit-event').hidden=!supported;
  if(supported){
    const vector=v=>v.map((x,i)=>'xyz'[i]+'='+x.toExponential(4)).join(' · ');
    $('body-edit-event').textContent='Intervenção externa · revisão '+event.revision+(event.external_mass_delta_kg!==undefined?'\nΔM = '+event.external_mass_delta_kg.toExponential(6)+' kg':'')+'\nΔE = '+event.external_energy_delta_J.toExponential(6)+' J\nΔP = '+vector(event.external_momentum_delta_kg_m_s)+' kg·m/s\nΔL = '+vector(event.external_angular_momentum_delta_kg_m2_s)+' kg·m²/s';
  }
}
function fillBodyEditor(){
  const p=appState?.physics,b=p?.bodies.find(b=>b.id===$('edit-body').value);if(!b||!p.paused)return;
  const operation=$('edit-operation').value,u=p.physical_scale;
  bodyEditSnapshot={...editGuard(p),body:b.id,operation};
  $('edit-mass-kg').value=(operation==='new'?u.mass_unit_kg:operation==='create'?1e20:b.mass*u.mass_unit_kg).toPrecision(15);
  for(const [key,values,scale] of [['position',b.position,u.length_unit_m],['velocity',b.velocity,u.velocity_unit_m_s]])values.forEach((v,i)=>$('edit-'+key+'-'+i).value=(operation==='new'?0:v*scale+(operation==='create'&&key==='position'&&i===0?1e9:0)).toPrecision(15));
  $('edit-name').value=operation==='new'?'Corpo inicial':'Corpo criado';
  $('body-edit-frame').textContent=operation==='new'?'Novo referencial inercial, sem época absoluta. A posição inicial informada define o sistema; sem recentrar.':'Referencial fixo: '+p.contract.frame+'. Origem inicial preservada; não são coordenadas SSB ou GALACTIC.';
  $('body-edit-status').textContent='Estado preparado: t='+p.time.toPrecision(9)+' u · revisão '+p.revision+'. Corpos pontuais, sem colisões.';
  $('body-edit-fields').disabled=false;updateBodyEditor(p);
}
$('edit-body').onchange=clearBodyEditor;$('edit-operation').onchange=()=>{clearBodyEditor();if(appState?.physics)updateBodyEditor(appState.physics);};
$('view-edit-body').onclick=()=>{
  const p=appState?.physics,b=p?.bodies.find(b=>b.id===$('edit-body').value);if(!b)return;
  const distance=appState.display?.physical_radii&&b.attributes.radius_m>0?Math.max(4*b.attributes.radius_m,1):b.display_marker_radius_m?b.display_marker_radius_m*10:b.reference_id==='sol:naif:10'?4e9:p.atlas_initial?8e8:1.2e9;
  const labels=p.bodies.map(body=>'openspace.setPropertyValueSingle("Scene.'+body.label_node+'.Renderable.Enabled",'+(body.id===b.id)+');').join('');
  const label='openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Size",'+Math.log10(distance*.001)+');openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Translation.Position",{0,0,'+(distance*.03+1.5*(appState.display?.physical_radii?b.attributes.radius_m||0:b.display_marker_radius_m||0))+'});';
  if(script(labels+label+'openspace.navigation.setNavigationState({Anchor="'+b.scene_node+'",ReferenceFrame="LabRoot",Position={0,'+(-distance)+','+(distance*.3)+'},Up={0,0,1}})'))$('notice').textContent=appState.display?.physical_radii?'Corpo selecionado · raio geométrico SI definido; orientação cinemática.':'Corpo selecionado no experimento · marcador ampliado; dimensões físicas não representadas.';
};
$('prepare-body-edit').onclick=async()=>{await command({command:'pause'},'Experimento pausado para edição.');fillBodyEditor();};
$('remove-edit-body').onclick=async()=>{
  if(pending)return;const id=$('edit-body').value;await command({command:'pause'},'Experimento pausado para remoção.');
  const p=appState?.physics;if(!p?.paused||!p.bodies.some(b=>b.id===id))return;
  await command({command:'remove_body',body:id,...editGuard(p)},'Corpo removido; matéria, energia e momentos externos registrados.');
};
$('body-edit-form').onsubmit=async e=>{
  e.preventDefault();if(pending||!bodyEditSnapshot||!$('body-edit-form').reportValidity())return;
  const snapshot={...bodyEditSnapshot},operation=snapshot.operation;
  const request={...snapshot,command:operation==='edit'?'set_body':operation==='create'?'create_body':'new_system',name:$('edit-name').value,mass_kg:Number($('edit-mass-kg').value),position_m:[0,1,2].map(i=>Number($('edit-position-'+i).value)),velocity_m_s:[0,1,2].map(i=>Number($('edit-velocity-'+i).value))};
  await command(request,operation==='edit'?'Estado aplicado e pausado; balanços externos registrados.':operation==='create'?'Corpo criado e pausado; balanços externos registrados.':'Novo sistema iniciado e pausado, sem fonte observacional.');
  const p=appState?.physics;
  if(p?.paused&&(p.revision===snapshot.revision+1||operation==='new'&&p.system_id!==snapshot.system_id)){
    if(operation!=='edit'){$('edit-operation').value='edit';const added=p.interventions.at(-1)?.body;$('edit-body').value=operation==='new'?p.bodies[0].id:added;}
    fillBodyEditor();
  }
};
