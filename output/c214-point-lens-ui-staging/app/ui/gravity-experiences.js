'use strict';
let gravityExperienceCatalog=null;
function describeGravityExperience(){
  const model=gravityExperienceCatalog?.models.find(m=>m.id===$('gravity-experience').value);if(!model)return;
  $('gravity-experience-goal').textContent=model.goal+' Horizonte recomendado: '+(model.horizon_model_time*gravityExperienceCatalog.physical_scale.time_unit_s/3600).toLocaleString('pt-BR',{maximumFractionDigits:2})+' h. Pausa uma vez nesse instante; você pode continuar depois.';
}
function updateGravityExperience(p){
  $('load-gravity-experience').disabled=pending||!gravityExperienceCatalog;
  const e=p.experiment,a=e?.analysis;
  $('view-gravity-pair').disabled=pending||!a?.pair||a.pair.length!==2;$('view-gravity-escaper').disabled=pending||!a?.escaper;
  if(!e){$('gravity-experience-result').textContent='';return;}
  const names=ids=>ids.map(id=>p.bodies.find(b=>b.id===id)?.name||'corpo removido').join(' / '),number=v=>v.toExponential(5);
  let text=e.definition.label+' · '+(e.conditions_edited?'CONDIÇÕES MODIFICADAS. ':'condições iniciais preservadas. ');
  if(e.status==='modified_population')text+='A população foi editada. Use o diagnóstico orbital para os pares ativos.';
  else if(e.status==='isolated_flyby'||e.status==='isolated_bound_pair')text+='Par '+names(a.pair)+': energia específica '+number(a.specific_energy_canonical*p.physical_scale.velocity_unit_m_s**2)+' J/kg · '+(a.outward?'afastando':'aproximando')+'.';
  else if(a?.outer){
    text+='Par instantâneo '+names(a.pair)+'. Terceiro: '+names([a.escaper])+'. Energia externa '+number(a.outer.specific_energy_canonical*p.physical_scale.velocity_unit_m_s**2)+' J/kg; distância / semieixo = '+number(a.separation_over_binary_a)+'. ';
    text+=e.status==='hierarchical_outgoing'?'Par ligado e terceiro se afastando com energia externa positiva. ':'Interação em andamento; ainda não há afastamento hierárquico confirmado. ';
    text+='Visitante inicial '+(a.initial_incoming_cluster_energy_canonical>0?'livre':'ligado')+' em relação ao binário. ';
  }else text+='Nenhum par instantâneo ligado identificado. ';
  if(e.horizon_reached)text+='Horizonte recomendado atingido. Resultado é deste intervalo finito.';
  text+=' Erro E relativo: '+(p.energy_error===null?'indefinido':number(p.energy_error))+'.';
  $('gravity-experience-result').textContent=text;
}
$('gravity-experience').onchange=describeGravityExperience;
$('load-gravity-experience').onclick=async()=>{
  if(pending||!gravityExperienceCatalog)return;const scenario=$('gravity-experience').value;
  await command({command:'pause'},'Experimento pausado para carregar o modelo.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({command:'load_experiment',scenario_id:scenario,...editGuard(p)},'Modelo carregado e pausado. Escolha o ritmo e inicie a evolução.');
};
$('view-gravity-pair').onclick=()=>{
  const p=appState?.physics,ids=p?.experiment?.analysis?.pair;if(!ids||ids.length!==2)return;
  const bodies=ids.map(id=>p.bodies.find(b=>b.id===id));if(bodies.some(b=>!b))return;
  const separation=Math.hypot(...bodies[0].position.map((v,k)=>(v-bodies[1].position[k])*p.physical_scale.length_unit_m));
  const distance=Math.max((p.display_min_view_distance_m||3e9),2.5*separation);
  const labels=p.bodies.map(b=>'openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Enabled",'+ids.includes(b.id)+');'+(ids.includes(b.id)?'openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Renderable.Size",'+Math.log10(distance*.001)+');openspace.setPropertyValueSingle("Scene.'+b.label_node+'.Translation.Position",{0,0,'+(distance*.03+1.5*(b.display_marker_radius_m||0))+'});':'')).join('');
  script(labels+'openspace.navigation.setNavigationState({Anchor="LabPairFrame",ReferenceFrame="LabRoot",Position={0,'+(-distance)+','+(distance*.6)+'},Up={0,0,1}})');
};
$('view-gravity-escaper').onclick=()=>{const id=appState?.physics?.experiment?.analysis?.escaper;if(!id)return;$('edit-body').value=id;$('edit-body').dispatchEvent(new Event('change',{bubbles:true}));$('view-edit-body').click();};
fetch('/api/laboratory/experiments').then(async r=>{const c=await r.json();if(!r.ok)throw Error(c.error);gravityExperienceCatalog=c;
  for(const m of c.models){const o=document.createElement('option');o.value=m.id;o.textContent=m.label;$('gravity-experience').append(o);}describeGravityExperience();if(appState?.physics)updateGravityExperience(appState.physics);
}).catch(error=>{$('gravity-experience-goal').textContent=error.message;});
