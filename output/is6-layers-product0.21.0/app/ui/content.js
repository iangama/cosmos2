'use strict';
let contentAtlas=null,packageCatalog=null,selectedPackage=null,contentBusy=false,lastContentExport=null;
const $=id=>document.getElementById(id);
const originNames={model_calculated:'Calculado por modelo',model_parameter:'Parâmetro de modelo',inferred_from_model:'Derivado de modelo',adopted_reference_shape:'Forma adotada',illustrative_map:'Mapa ilustrativo',surface_imagery:'Imagem de superfície',unknown:'Desconhecido'};
const fileStates={present_unverified:'Presente · conteúdo não verificado',missing:'Ausente',size_mismatch:'Tamanho diferente',hash_mismatch:'SHA256 diferente',unreadable:'Não foi possível ler',changed_during_read:'Alterado durante a leitura',verified:'SHA256 conferido'};
const contentKinds={evaluated_ephemeris_model:'Efemérides de modelo avaliado',surface_and_sky_images:'Imagens de superfície e céu',simulation_visualization:'Visualização de simulação',catalog_visualization:'Visualização de catálogo',evaluated_nuclear_data:'Dados nucleares avaliados',evaluated_field_coefficients:'Coeficientes de campo avaliado',local_model_definitions:'Definições locais de unidades',extracted_scientific_data:'Recorte científico com fontes por canal'};
function node(tag,text,className){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;return e;}
function size(bytes){return bytes<1024?bytes+' bytes':bytes<1048576?(bytes/1024).toLocaleString('pt-BR',{maximumFractionDigits:2})+' KiB':(bytes/1048576).toLocaleString('pt-BR',{maximumFractionDigits:2})+' MiB';}
function number(value){return Math.abs(value)>=1e7||Math.abs(value)>0&&Math.abs(value)<.001?value.toExponential(10).replace('.',','):value.toLocaleString('pt-BR',{maximumSignificantDigits:12});}
function displayValue(p){
  if(p.value===null)return'Não cadastrado / desconhecido';
  if(p.id==='texture')return p.value.map(v=>v.credit+'\n'+v.path).join('\n\n');
  if(Array.isArray(p.value))return p.value.map((v,k)=>Array.isArray(v)?'L'+(k+1)+' · '+v.map(number).join(' · '):['x','y','z'][k]+' = '+number(v)).join('\n')+' '+p.unit;
  return number(p.value)+' '+p.unit;
}
function mode(view){
  for(const name of ['properties','packages']){$(name+'-view').hidden=name!==view;$(name==='properties'?'property-options':'package-options').hidden=name!==view;$('show-'+name).setAttribute('aria-pressed',String(name===view));}
}
function renderProperties(){
  if(!contentAtlas)return;
  const b=contentAtlas.bodies.find(b=>b.naif_id===$('reference-body').value);if(!b)return;
  $('reference-title').textContent=b.name+' · '+b.id;
  $('reference-epoch').textContent=contentAtlas.epoch.utc+' · TDB '+number(contentAtlas.epoch.et_tdb_s)+' s desde J2000';
  $('reference-properties').replaceChildren();
  for(const p of b.properties){
    const card=node('section',undefined,'property-card');card.dataset.propertyId=p.id;
    card.append(node('h3',p.label),node('span',originNames[p.status]||p.status,'property-origin'),node('div',displayValue(p),'property-value'));
    card.append(node('p',p.uncertainty.value===null?'Incerteza: desconhecida / não fornecida neste recorte.':'Incerteza: '+number(p.uncertainty.value)+' '+p.unit,'muted'));
    if(p.note)card.append(node('p',p.note,'muted'));
    const detail=node('details');detail.append(node('summary','Fonte e convenções'),node('p','Origem: '+p.origin));
    detail.append(node('p','Referencial: '+(p.frame||'não aplicável / ausente')+'\nÉpoca da propriedade: '+(p.epoch?.utc||'não aplicável / desconhecida')));
    if(p.known_uncertainty_contribution_from_G_only_kg)detail.append(node('p','Contribuição de G, isoladamente: '+number(p.known_uncertainty_contribution_from_G_only_kg)+' kg; não representa a incerteza total.'));
    for(const source of p.sources){if(source.url){const a=node('a',source.title+' ↗');a.href=source.url;a.target='_blank';a.rel='noopener';detail.append(a);}else detail.append(node('p',source.title));if(source.file)detail.append(node('code',source.file));if(source.sha256)detail.append(node('code','SHA256 '+source.sha256));if(source.package_id)detail.append(node('p','Pacote: '+source.package_id));}
    card.append(detail);$('reference-properties').append(card);
  }
}
function packageStatus(p){if(p.last_verification&&p.verification_cache_current)return p.last_verification.status==='verified'?'Conteúdo conferido nesta sessão':'Verificação encontrou diferença';return p.files.some(f=>f.local.status!=='present_unverified')?'Presença ou tamanho requer atenção':'Instalado · conferir conteúdo';}
function renderPackageList(){
  if(!packageCatalog)return;
  const filter=$('package-search').value.toLocaleLowerCase('pt-BR');$('package-list').replaceChildren();
  for(const p of packageCatalog.packages.filter(p=>(p.name+' '+p.credits+' '+p.content_kind).toLocaleLowerCase('pt-BR').includes(filter))){const b=node('button',p.name);b.dataset.packageId=p.id;b.setAttribute('aria-pressed',String(p.id===selectedPackage));b.append(node('small',size(p.total_bytes)+' · '+packageStatus(p)));b.onclick=()=>{selectedPackage=p.id;renderPackageList();renderPackage();};$('package-list').append(b);}
  if(!$('package-list').childElementCount)$('package-list').append(node('p','Nenhum pacote encontrado.','muted'));
}
function renderPackage(){
  if(!packageCatalog)return;
  const p=packageCatalog.packages.find(p=>p.id===selectedPackage);if(!p)return;
  $('package-title').textContent=p.name;$('package-summary').textContent=p.id+' · '+p.version+' · '+p.files.length+' arquivos · '+size(p.total_bytes);
  $('package-metadata').replaceChildren();
  const c=p.coverage,coverage=c.application_utc?(c.object_ids?.join(', ')||'Atlas')+' · '+c.application_utc.join(' a '):c.years?c.years.join(' a ')+' · altitude '+c.application_altitude_km.join(' a ')+' km':c.states?c.states.toLocaleString('pt-BR')+' estados; N '+c.N.join('–')+', Z '+c.Z.join('–')+', A '+c.A.join('–'):c.extent||c.objects?.join?.(', ')||c.objects||c.model||'Não cadastrada';
  for(const [name,value]of[['Crédito',p.credits],['Tipo de conteúdo',contentKinds[p.content_kind]||p.content_kind],['Termos e alcance local',p.terms.note],['Cobertura',coverage],['Unidades',p.units.join(' · ')],['Referencial',p.frame]]){const el=node('p',value);el.prepend(node('b',name));$('package-metadata').append(el);}
  const cached=p.last_verification&&p.verification_cache_current,report=cached?p.last_verification:null;
  $('verification-status').textContent=report?(report.status==='verified'?'Conferido':'Diferença encontrada')+' · '+new Date(report.verified_utc).toLocaleString('pt-BR',{timeZone:'UTC'})+' UTC':p.last_verification?'Arquivos mudaram desde a última verificação.':'Conteúdo ainda não verificado nesta sessão.';
  $('package-files').replaceChildren();
  for(const item of p.files){const tr=node('tr'),name=node('td',item.path),detail=node('details');detail.append(node('summary','Hash e origem'),node('code','SHA256 esperado: '+item.sha256));if(item.source_url){const a=node('a','Arquivo de origem ↗');a.href=item.source_url;a.target='_blank';a.rel='noopener';detail.append(a);}detail.append(node('code',item.receipt||'Definição local versionada'));const verified=report?.files.find(f=>f.path===item.path);if(verified?.actual_sha256)detail.append(node('code','SHA256 lido: '+verified.actual_sha256));name.append(detail);tr.append(name,node('td',size(item.bytes)),node('td',fileStates[verified?.status||item.local.status]||item.local.status));$('package-files').append(tr);}
  $('manifest-hash').textContent=packageCatalog.manifest_sha256;
}
async function get(path){const r=await fetch(path),data=await r.json();if(!r.ok||data.ok===false)throw Error(data.error||'Consulta indisponível.');return data;}
async function action(path,request){if(contentBusy)return null;contentBusy=true;document.querySelectorAll('#verify-package,#export-properties,#export-packages,#refresh-properties').forEach(b=>b.disabled=true);try{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}),data=await r.json();if(!r.ok||!data.ok)throw Error(data.error||'Comando recusado.');return data;}catch(error){$('content-status').textContent=error.message;return null;}finally{contentBusy=false;document.querySelectorAll('#verify-package,#export-properties,#export-packages,#refresh-properties').forEach(b=>b.disabled=false);}}
async function exportData(path){const data=await action(path,{});if(!data)return;lastContentExport=data;$('content-status').textContent='JSON com fontes salvo em user/exports.';$('content-export-path').hidden=false;$('content-export-path').textContent=data.export_file;}
$('show-properties').onclick=()=>mode('properties');$('show-packages').onclick=()=>mode('packages');
$('reference-body').onchange=renderProperties;$('package-search').oninput=renderPackageList;
$('refresh-properties').onclick=async()=>{try{contentAtlas=await get('/api/atlas/state');renderProperties();$('content-status').textContent='Estado confirmado do Atlas atualizado.';}catch(error){$('content-status').textContent=error.message;}};
$('verify-package').onclick=async()=>{const requested=selectedPackage;$('content-status').textContent='Lendo e conferindo os arquivos do pacote…';const data=await action('/api/packages/verify',{package_id:requested});if(!data)return;try{packageCatalog=await get('/api/packages/catalog');renderPackageList();renderPackage();$('content-status').textContent=data.verification.status==='verified'?'Todos os arquivos deste pacote conferem com o manifesto.':'Verificação identificou ausências ou diferenças. Consulte cada arquivo.';}catch(error){$('content-status').textContent=error.message;}};
$('export-properties').onclick=()=>exportData('/api/atlas/export');$('export-packages').onclick=()=>exportData('/api/packages/export');
(async()=>{
  const query=new URLSearchParams(location.search),body=query.get('body');if(['10','399','301'].includes(body))$('reference-body').value=body;
  const results=await Promise.allSettled([get('/api/atlas/state'),get('/api/packages/catalog')]);
  if(results[0].status==='fulfilled'){contentAtlas=results[0].value;renderProperties();}
  if(results[1].status==='fulfilled'){packageCatalog=results[1].value;selectedPackage=packageCatalog.packages[0].id;renderPackageList();renderPackage();}
  mode(query.get('view')==='packages'?'packages':'properties');
  $('content-status').textContent=results.every(r=>r.status==='fulfilled')?'Dados locais carregados. Escolha uma propriedade ou um pacote.':results.filter(r=>r.status==='rejected').map(r=>r.reason.message).join(' ');
})();
