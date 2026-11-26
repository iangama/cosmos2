'use strict';
let navigationState=null,navigationBusy=false,freeBusy=false,freeLast=performance.now(),freeKeys=new Set(),freeLook=[0,0,0],buttonMove=null;
const kindLabels={Earth:'planeta sol terra earth',Moon:'lua satélite sol terra lua moon',Saturn:'planeta gasoso sol saturno saturn',System:'sistema sol terra lua',Galaxy:'galáxia via láctea milky way'};
async function navigate(action,request={}){
  if(navigationBusy||appState?.mode==='experiment')return;
  navigationBusy=true;
  try{
    const r=await fetch('/api/navigation/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}),d=await r.json();
    if(!r.ok||!d.ok)throw Error(d.error||'Comando de navegação recusado.');
    if(d.navigation.navigation)displayNavigation(d.navigation);
    $('notice').textContent=action==='viewpoint'?({overview:'Visão geral no lado iluminado.',terminator:'Terminador · Sol a 75° da direção da câmera.',polar:'Polo norte. A iluminação segue a época do Atlas.',detail:'Órbita próxima · limite do mapa informado na ficha.'}[request.preset]):action==='save'?'Vista e época salvas localmente.':action==='restore'?'Vista e época restauradas e confirmadas no motor.':action==='visit'?(d.navigation.flying?'Viagem em curso. Você pode cancelar.':'Vista confirmada no motor.'):'Comando confirmado no motor.';
    return d.navigation;
  }catch(e){$('notice').textContent=e.message;}finally{navigationBusy=false;}
}
function filterDestinations(){
  const q=$('search').value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,''),kind=$('type-filter').value;
  let buttons=[...document.querySelectorAll('#destinations [data-target]')];
  if($('distance-sort').value==='nearest'&&navigationState){
    const distances=t=>{const a=navigationState.positions[views[t].anchor];return a?Math.hypot(...a.map((v,i)=>v-navigationState.camera.position_render_m[i])):Infinity;};buttons.sort((a,b)=>distances(a.dataset.target)-distances(b.dataset.target));
  }else buttons.sort((a,b)=>['Earth','Moon','System','Saturn','Galaxy'].indexOf(a.dataset.target)-['Earth','Moon','System','Saturn','Galaxy'].indexOf(b.dataset.target));
  let count=0;for(const b of buttons){const t=b.dataset.target,text=(kindLabels[t]+' '+views[t].name).normalize('NFD').replace(/[\u0300-\u036f]/g,''),p=navigationState?.positions[views[t].anchor],distance=p?Math.hypot(...p.map((v,i)=>v-navigationState.camera.position_render_m[i])):Infinity,limit=Number($('nearby-filter').value);b.hidden=!(kind==='all'||b.dataset.kind===kind)||!q.split(/\s+/).every(word=>text.includes(word))||(limit>0&&distance>limit);b.title=Number.isFinite(distance)?'Câmera → centro: '+(distance/1000).toLocaleString('pt-BR',{maximumFractionDigits:0})+' km':'Modelo galáctico';if(!b.hidden)count++;$('destinations').append(b);}
  $('empty').hidden=count>0;
}
function displayNavigation(s){
  if(!navigationState&&views[s.target])selectTarget(s.target,true);
  navigationState=s;
  $('camera-mode').value=s.mode;$('cancel-flight').hidden=!s.flying;$('return-view').disabled=!s.return_available;
  $('save-favorite').disabled=s.flying;
  $('free-controls').hidden=s.mode!=='free';$('free-look').hidden=s.mode!=='free'||appState?.mode==='experiment';
  $('visual-controls').hidden=!['Earth','Moon','Saturn'].includes(selectedTarget);
  const limits={Earth:'Mapa fixo de superfície: 5400 × 2700 pixels; atmosfera de modelo. Sem relevo neste recorte.',Moon:'LRO WAC fixo: 11520 × 5760 pixels. Textura inclui iluminação original. Sem relevo ou atmosfera neste recorte.',Saturn:'Mapa visual fixo: 2880 × 1440 pixels; perfis radiais dos anéis: 1500 amostras. Sem superfície sólida ou dinâmica de partículas.'};$('content-limit').textContent=limits[selectedTarget]||'';
  $('atlas-pause').textContent=s.paused?'Retomar tempo':'Pausar tempo';
  if(document.activeElement!==$('atlas-rate'))$('atlas-rate').value=String(s.rate);
  const body=atlasState?.bodies.find(b=>b.scene_node===views[selectedTarget]?.anchor);
  if(body){const d=Math.hypot(...s.camera.position_render_m.map((v,i)=>v-body.position_render_m[i]));$('camera-distance').textContent='Câmera → centro: '+(d/1000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' km · eixos GALACTIC.';}
  else $('camera-distance').textContent='Câmera em eixos GALACTIC · distâncias físicas preservadas.';
  if(s.boundary)$('notice').textContent=s.boundary;
  renderSceneTargets();if($('nearby-filter').value!=='0'||$('distance-sort').value==='nearest')filterDestinations();
}
function renderSceneTargets(){
  $('scene-targets').replaceChildren();if(!navigationState||appState?.mode==='experiment')return;
  const s=navigationState,p=s.camera.position_render_m,f=s.camera.forward,u=s.camera.up,r=[f[1]*u[2]-f[2]*u[1],f[2]*u[0]-f[0]*u[2],f[0]*u[1]-f[1]*u[0]],dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0),scale=Number($('ui-scale').value);
  for(const target of ['Earth','Moon','Saturn']){
    if(s.occluded_targets?.includes(target))continue;
    const q=s.positions[target].map((v,i)=>v-p[i]),z=dot(q,f);if(z<=0)continue;
    const radius={Earth:6378137,Moon:1737400,Saturn:60268000}[target],pixelRadius=radius/z*innerHeight/(2*Math.tan(47.27*Math.PI/360));
    if(pixelRadius<.75&&target!==selectedTarget&&!(selectedTarget==='System'&&target==='Earth'))continue;
    const x=(1+dot(q,r)/(z*Math.tan(35*Math.PI/180)))*innerWidth/2,y=(1-dot(q,u)/(z*Math.tan(47.27*Math.PI/360)))*innerHeight/2;
    if(x<0||x>innerWidth||y<0||y>innerHeight)continue;
    const b=document.createElement('button');b.className='scene-target';b.dataset.sceneTarget=target;b.textContent='⊙ '+views[target].name;b.style.left=x/scale+'px';b.style.top=y/scale+'px';b.setAttribute('aria-label','Selecionar '+views[target].name+' na cena');b.onclick=()=>selectTarget(target);$('scene-targets').append(b);
  }
}
async function refreshFavorites(){
  try{const r=await fetch('/api/navigation/favorites'),d=await r.json();if(!r.ok)throw Error(d.error);$('favorites-list').replaceChildren();
    for(const row of d.views){const line=document.createElement('div'),b=document.createElement('button'),del=document.createElement('button');line.className='favorite-row';b.textContent=row.name;b.dataset.favoriteId=row.id;b.onclick=async()=>{const s=await navigate('restore',{id:row.id});if(s)selectTarget(s.target,true);};del.textContent='×';del.setAttribute('aria-label','Excluir favorito '+row.name);del.onclick=async()=>{await navigate('delete',{id:row.id});refreshFavorites();};line.append(b,del);$('favorites-list').append(line);}
    if(!d.views.length)$('favorites-list').textContent='Suas vistas salvas aparecerão aqui.';
  }catch(e){$('favorites-list').textContent=e.message;}
}
$('type-filter').onchange=filterDestinations;$('distance-sort').onchange=filterDestinations;$('nearby-filter').onchange=filterDestinations;
document.querySelectorAll('[data-tree-target]').forEach(b=>b.onclick=()=>selectTarget(b.dataset.treeTarget));
$('visit-target').onclick=()=>visit(selectedTarget);
$('return-view').onclick=async()=>{const s=await navigate('restore',{id:'return'});if(s)selectTarget(s.target,true);};
$('cancel-flight').onclick=()=>navigate('cancel');
$('camera-mode').onchange=()=>{clearFree();navigate('mode',{mode:$('camera-mode').value});};
document.querySelectorAll('[data-viewpoint]').forEach(b=>b.onclick=()=>navigate('viewpoint',{target:selectedTarget,preset:b.dataset.viewpoint}));
async function applyDisplay(){const d=await navigate('display',{exposure:Number($('visual-exposure').value),stars:$('visual-sky').checked});if(d)$('exposure-reading').textContent=Number(d.exposure).toFixed(2)+' · ajuste visual, sem fotometria';}
$('visual-exposure').onchange=applyDisplay;$('visual-sky').onchange=applyDisplay;
fetch('/api/navigation/display').then(r=>r.json()).then(d=>{if(typeof d.exposure==='number'){$('visual-exposure').value=d.exposure;$('visual-sky').checked=d.stars;$('exposure-reading').textContent=Number(d.exposure).toFixed(2)+' · ajuste visual, sem fotometria';}}).catch(()=>{});
$('save-favorite').onclick=async()=>{await navigate('save',{name:$('favorite-name').value||views[navigationState?.target||selectedTarget].name});refreshFavorites();};
$('atlas-pause').onclick=()=>navigate('clock',{paused:!navigationState?.paused,rate:Number($('atlas-rate').value)});
$('atlas-rate').onchange=()=>navigate('clock',{paused:navigationState?.paused??true,rate:Number($('atlas-rate').value)});
$('epoch-slider').onchange=()=>{const year=Math.floor(Number($('epoch-slider').value)),start=Date.UTC(year,0,1),end=Date.UTC(year+1,0,1),date=new Date(start+(Number($('epoch-slider').value)-year)*(end-start));$('atlas-epoch').value=date.toISOString().slice(0,19);$('atlas-epoch-form').requestSubmit();};
function scaleInterface(value){document.documentElement.style.setProperty('--ui-scale',value);document.body.classList.toggle('large-ui',Number(value)>1);localStorage.setItem('cosmos2-ui-scale',value);renderSceneTargets();}
$('panel-toggle').onclick=()=>{const open=document.body.classList.toggle('details-open');$('panel-toggle').textContent=open?'Ver catálogo':'Ver ficha';$('panel-toggle').setAttribute('aria-expanded',String(open));};
$('ui-scale').value=localStorage.getItem('cosmos2-ui-scale')||'1';if(!$('ui-scale').value)$('ui-scale').value='1';scaleInterface($('ui-scale').value);$('ui-scale').onchange=()=>scaleInterface($('ui-scale').value);
function editing(e){return !!e.target.closest('input,select,textarea,[contenteditable]');}
function clearFree(){freeKeys.clear();freeLook=[0,0,0];buttonMove=null;}
window.addEventListener('blur',clearFree);document.addEventListener('visibilitychange',clearFree);
document.addEventListener('keydown',e=>{
  if(editing(e)||appState?.mode==='experiment')return;
  const key=e.key.toLowerCase();
  if(key===' '&&e.target.closest('button,summary'))return;
  if(navigationState?.mode==='free'&&['w','a','s','d','q','e'].includes(key)){e.preventDefault();e.stopImmediatePropagation();freeKeys.add(key);return;}
  if(e.repeat)return;
  if(key==='g'){e.preventDefault();visit(selectedTarget);}else if(key==='f'){e.preventDefault();navigate('mode',{mode:navigationState?.mode==='follow'?'orbit':'follow'});}else if(key===' '){e.preventDefault();$('atlas-pause').click();}else if(key==='escape'){e.preventDefault();clearFree();navigate('cancel');}
},true);
document.addEventListener('keyup',e=>freeKeys.delete(e.key.toLowerCase()),true);
document.addEventListener('focusin',clearFree);
for(const b of document.querySelectorAll('[data-move]')){b.onpointerdown=e=>{e.preventDefault();buttonMove=b.dataset.move.split(',').map(Number);b.setPointerCapture(e.pointerId);};b.onpointerup=b.onpointercancel=()=>buttonMove=null;}
let looking=false,lastLook;
$('free-look').onpointerdown=e=>{looking=true;lastLook=[e.clientX,e.clientY];$('free-look').setPointerCapture(e.pointerId);};
$('free-look').onpointermove=e=>{if(looking){freeLook[0]+=Math.max(-.1,Math.min(.1,(e.clientX-lastLook[0])*.002));freeLook[1]-=Math.max(-.1,Math.min(.1,(e.clientY-lastLook[1])*.002));lastLook=[e.clientX,e.clientY];}};
$('free-look').onpointerup=$('free-look').onpointercancel=()=>looking=false;
async function freeStep(){const now=performance.now(),dt=Math.min(.1,(now-freeLast)/1000);freeLast=now;
  if(!freeBusy&&navigationState?.mode==='free'&&appState?.mode!=='experiment'&&document.visibilityState==='visible'){
    const movement=buttonMove||[Number(freeKeys.has('d'))-Number(freeKeys.has('a')),Number(freeKeys.has('e'))-Number(freeKeys.has('q')),Number(freeKeys.has('w'))-Number(freeKeys.has('s'))];
    if(movement.some(Boolean)||freeLook.some(Boolean)){const look=freeLook.map(v=>Math.max(-.3,Math.min(.3,v)));freeLook=[0,0,0];freeBusy=true;
      try{const r=await fetch('/api/navigation/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({translation:movement,look,speed:Number($('free-speed').value),dt})});if(!r.ok){const d=await r.json();throw Error(d.error);}}catch(e){clearFree();$('notice').textContent=e.message;}finally{freeBusy=false;}
    }
  }setTimeout(freeStep,50);
}
async function pollNavigation(){try{if(appState?.mode!=='experiment'){const r=await fetch('/api/navigation/state'),d=await r.json();if(r.ok)displayNavigation(d);}}catch{}setTimeout(pollNavigation,300);}
refreshFavorites();filterDestinations();pollNavigation();freeStep();
