'use strict';
let bodyAttributesSnapshot=null,bodyAttributesIdentity='';
function clearBodyAttributes(){bodyAttributesSnapshot=null;$('body-attributes-fields').disabled=true;$('body-attributes-status').textContent='Pause e carregue os atributos do corpo selecionado.';}
function updateBodyAttributes(p,display){
  const body=p.bodies.find(b=>b.id===$('edit-body').value);if(!body)return;
  const identity=p.system_id+'|'+p.edit_token+'|'+body.id;
  if(identity!==bodyAttributesIdentity){bodyAttributesIdentity=identity;clearBodyAttributes();}
  const stale=bodyAttributesSnapshot&&(p.revision!==bodyAttributesSnapshot.revision||p.time!==bodyAttributesSnapshot.expected_time);
  $('apply-body-attributes').disabled=pending||!bodyAttributesSnapshot||!p.paused||Boolean(stale);
  if(stale)$('body-attributes-status').textContent='O sistema evoluiu ou mudou. Pause e carregue novamente antes de aplicar.';
  $('body-radius-mode').disabled=pending;$('body-show-axes').disabled=pending;
  if(display){$('body-radius-mode').value=display.physical_radii?'physical':'markers';$('body-show-axes').checked=display.axes_body!==null;}
  $('body-display-note').textContent=display?.physical_radii?'Esferas com raios SI definidos e orientação cinemática. Texturas da referência não definem a rotação IAU. Sem raio definido ou com raio zero, o corpo não tem esfera visível; sua gravidade permanece ativa.':'Tamanhos ampliados para localização; eixos de orientação também ampliados. Use raios físicos para comparar dimensões.';
}
function fillBodyAttributes(){
  const p=appState?.physics,b=p?.bodies.find(b=>b.id===$('edit-body').value);if(!p?.paused||!b)return;
  const a=b.attributes;bodyAttributesSnapshot={...editGuard(p),body:b.id};
  $('body-radius-m').value=a.radius_m===null?'':a.radius_m.toPrecision(16);
  $('body-spin-defined').checked=a.angular_velocity_rad_s!==null;$('body-spin-fields').disabled=!$('body-spin-defined').checked;
  (a.angular_velocity_rad_s||[0,0,0]).forEach((v,i)=>$('body-spin-'+i).value=v.toPrecision(16));
  const origins={unknown:'não definido',user_model:'parâmetro definido pelo usuário',reference_volume_equivalent_sphere:'esfera equivalente por volume, derivada dos semieixos de referência',adopted_reference_sphere:'esfera de referência adotada'};
  $('body-attributes-origin').textContent=b.name+' · raio: '+origins[a.radius_origin.kind]+'. Spin: '+origins[a.spin_origin.kind]+'. Eixos inerciais: '+p.contract.frame+'.';
  $('body-attributes-status').textContent='Atributos carregados · revisão '+p.revision+'. Alterar spin mantém a orientação atual. Energia interna de rotação não avaliada.';
  $('body-attributes-fields').disabled=false;updateBodyAttributes(p,appState.display);
}
async function applyBodyDisplay(){
  if(pending||appState?.mode!=='experiment')return;
  await command({command:'display',physical_radii:$('body-radius-mode').value==='physical',axes_body:$('body-show-axes').checked?$('edit-body').value:null},'Exibição atualizada; dinâmica e relógio preservados.');
}
$('edit-body').addEventListener('change',()=>{clearBodyAttributes();if($('body-show-axes').checked)applyBodyDisplay();});
$('body-radius-mode').onchange=applyBodyDisplay;$('body-show-axes').onchange=applyBodyDisplay;
$('body-spin-defined').onchange=()=>{$('body-spin-fields').disabled=!$('body-spin-defined').checked;};
$('prepare-body-attributes').onclick=async()=>{await command({command:'pause'},'Experimento pausado para editar raio/spin.');fillBodyAttributes();};
$('body-attributes-form').onsubmit=async e=>{
  e.preventDefault();if(pending||!bodyAttributesSnapshot||!$('body-attributes-form').reportValidity())return;
  const revision=bodyAttributesSnapshot.revision;
  await command({...bodyAttributesSnapshot,command:'set_attributes',radius_m:$('body-radius-m').value===''?null:Number($('body-radius-m').value),angular_velocity_rad_s:$('body-spin-defined').checked?[0,1,2].map(i=>Number($('body-spin-'+i).value)):null},'Raio/spin aplicados e pausados; fase orbital e erro numérico preservados.');
  if(appState?.physics.revision===revision+1)fillBodyAttributes();
};
