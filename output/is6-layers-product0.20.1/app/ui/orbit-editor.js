'use strict';
let orbitIdentity='',orbitResultIdentity='';
const orbitalNumber=v=>v===null||v===undefined?'indefinido':v.toExponential(4);
function updateOrbitEditor(p,preview){
  const body=$('edit-body').value,ids=p.system_id+'|'+body+'|'+p.bodies.map(b=>b.id).join('|');
  if(ids!==orbitIdentity){
    orbitIdentity=ids;const old=$('orbit-primary').value;$('orbit-primary').replaceChildren();
    for(const b of p.bodies.filter(b=>b.id!==body)){const o=document.createElement('option');o.value=b.id;o.textContent=b.name;$('orbit-primary').append(o);}
    if(p.bodies.some(b=>b.id===old&&b.id!==body))$('orbit-primary').value=old;
  }
  $('calculate-orbit').disabled=pending||p.bodies.length<2;
  const fresh=bodyEditSnapshot&&bodyEditSnapshot.operation==='edit'&&bodyEditSnapshot.body===body&&bodyEditSnapshot.system_id===p.system_id&&bodyEditSnapshot.edit_token===p.edit_token&&bodyEditSnapshot.revision===p.revision&&bodyEditSnapshot.expected_time===p.time&&p.paused;
  $('compare-orbit').disabled=pending||p.bodies.length<2||!fresh;
  $('view-orbit').disabled=pending||!preview?.render.nodes.length;$('clear-orbit').disabled=pending||!preview;
  if(p.bodies.length<2)$('orbit-status').textContent='Acrescente outro corpo para definir um par orbital.';
  else if(preview){
    const stale=preview.system_id!==p.system_id||preview.edit_token!==p.edit_token||preview.time!==p.time||preview.revision!==p.revision;
    $('orbit-status').textContent=preview.names.body+' em relação a '+preview.names.primary+' · t='+(preview.time*p.physical_scale.time_unit_s/3600).toPrecision(7)+' h · revisão '+preview.revision+(stale?' · PRÉVIA FIXA: o estado atual mudou.':' · estado atual confirmado.');
  }else $('orbit-status').textContent='Escolha corpo e primário e calcule uma prévia.';
  const key=preview?preview.render.id:'none';
  if(key!==orbitResultIdentity){orbitResultIdentity=key;renderOrbitTable(preview);}
  const c=p.conservation,s=c.SI,vector=v=>v.map(x=>x.toExponential(3)).join(' / ');
  $('conservation-reading').textContent='Massa total: '+orbitalNumber(s.total_mass_kg)+' kg\nCOM x/y/z: '+vector(s.barycenter_m)+' m\nVelocidade COM: '+vector(s.barycenter_velocity_m_s)+' m/s\nDesvio COM esperado: '+orbitalNumber(s.barycenter_drift_norm_m)+' m\nErro P normalizado: '+orbitalNumber(c.momentum_error_normalized)+(Object.keys(p.gravity_effects||{}).length?'\nMudança L orbital normalizada: '+orbitalNumber(c.orbital_angular_change_normalized)+' (torque de eixo prescrito)\nErro L axial: '+orbitalNumber(c.J2_axial_angular?.normalized_error):'\nErro L normalizado: '+orbitalNumber(c.angular_momentum_error_normalized))+'\nReferência P/L: t='+(c.reference.time*p.physical_scale.time_unit_s/3600).toPrecision(7)+' h'+(c.reference.policy==='legacy_checkpoint_new_momentum_reference'?' (definida na carga do checkpoint antigo)':' (condição inicial/última intervenção física)');
}
function renderOrbitTable(preview){
  const table=$('orbit-table');table.replaceChildren();table.hidden=!preview;
  if(!preview){$('orbit-model-note').textContent='';return;}
  const classes={elliptic:'elíptica',hyperbolic:'hiperbólica',near_parabolic:'próxima de parábola',radial_degenerate:'radial; plano indefinido'};
  const columns=[preview.before,...(preview.after?[preview.after]:[])];
  const header=document.createElement('tr');for(const value of ['Par isolado','Atual',...(preview.after?['Proposto']:[])]){const th=document.createElement('th');th.textContent=value;header.append(th);}table.append(header);
  for(const [label,key,scale] of [['Tipo da cônica','classification',0],['Distância (km)','distance_m',1e-3],['Excentricidade','eccentricity',1],['Semieixo (km)','semimajor_axis_m',1e-3],['Periastro (km)','periapsis_m',1e-3],['Apoastro (km)','apoapsis_m',1e-3],['Período (h)','period_s',1/3600],['Velocidade (km/s)','relative_speed_m_s',1e-3],['Escape do par (km/s)','escape_speed_pair_m_s',1e-3],['Energia específica (J/kg)','specific_energy_J_kg',1],['Perturbação relativa','perturbation_relative_acceleration_ratio',1]]){
    const row=document.createElement('tr'),name=document.createElement('td');name.textContent=label;row.append(name);
    for(const d of columns){const cell=document.createElement('td');cell.textContent=key==='classification'?classes[d[key]]:orbitalNumber(d[key]===null?null:d[key]*scale);row.append(cell);}table.append(row);
  }
  const frozen=preview.before_escape.escape_speed_m_s/1000;
  $('orbit-model-note').textContent='Ciano: atual'+(preview.after?' · laranja: proposta':'')+'. Primário congelado; cônicas sem parametrização temporal. Arco limitado a 8× a distância atual'+(columns.some(c=>c.preview.clipped)?'; curva recortada.':'.')+(preview.before.model.includes('material tide')?' Cônica osculante sob maré material; órbita e spin continuam evoluindo juntos.':preview.before.model.includes('J2')?' Cônica osculante de monopolos sob perturbação J2; não prevê a trajetória real.':'')+' Escape de partícula-teste no conjunto instantâneo congelado: '+orbitalNumber(frozen)+' km/s. Esses valores não garantem escape/captura no sistema de massas em movimento. '+(columns.some(c=>c.undefined_reason)?'Elementos singulares estão indefinidos.':'')+(columns.some(c=>c.classification==='radial_degenerate')?' Estado radial sem plano orbital: nenhuma curva é desenhada para esse estado.':'');
}
async function calculateOrbit(compare){
  if(pending)return;
  if(!compare)await command({command:'pause'},'Experimento pausado para calcular a prévia.');
  const p=appState?.physics,body=$('edit-body').value;if(!p?.paused)return;
  const request={...editGuard(p),command:'orbit',body,primary:$('orbit-primary').value};
  if(compare){
    if(!bodyEditSnapshot||bodyEditSnapshot.expected_time!==p.time||bodyEditSnapshot.revision!==p.revision||!$('body-edit-form').reportValidity())return;
    request.proposed={mass_kg:Number($('edit-mass-kg').value),position_m:[0,1,2].map(i=>Number($('edit-position-'+i).value)),velocity_m_s:[0,1,2].map(i=>Number($('edit-velocity-'+i).value))};
  }
  await command(request,'Prévia calculada; condições físicas e checkpoint preservados.');
}
$('calculate-orbit').onclick=()=>calculateOrbit(false);$('compare-orbit').onclick=()=>calculateOrbit(true);
$('edit-body').addEventListener('change',()=>{if(appState?.physics)updateOrbitEditor(appState.physics,appState.orbit_preview);});
$('view-orbit').onclick=()=>{const r=appState?.orbit_preview?.render;if(!r?.nodes.length)return;script('openspace.navigation.setNavigationState({Anchor="LabOrbitFrame",ReferenceFrame="LabRoot",Position={0,'+(-r.view_distance_m)+','+(r.view_distance_m*.6)+'},Up={0,0,1}})');};
$('clear-orbit').onclick=()=>command({command:'clear_orbit'},'Curvas removidas; física preservada.');
$('view-barycenter').onclick=()=>{
  const p=appState?.physics;if(!p)return;const center=p.conservation.current.barycenter;
  const d=Math.max(3e9,2.5*Math.max(...p.bodies.map(b=>Math.hypot(...b.position.map((v,k)=>(v-center[k])*p.physical_scale.length_unit_m)))));
  script('openspace.setPropertyValueSingle("Scene.LabBarycenter.Renderable.Enabled",true);openspace.navigation.setNavigationState({Anchor="LabBarycenter",ReferenceFrame="LabRoot",Position={0,'+(-d)+','+(d*.6)+'},Up={0,0,1}})');
};
