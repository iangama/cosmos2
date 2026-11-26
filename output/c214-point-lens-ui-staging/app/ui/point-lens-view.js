'use strict';
function updatePointLensParameters(){
  if(draftConfig.scenario!=='point-lens')return;
  const form=byId('parameters');
  if(form.querySelector('[data-point-position]'))return;
  for(const [kind,title] of [['source','Fonte'],['lens','Lente'],['observer','Observador']]){
    const group=document.createElement('details');group.className='point-lens-position';group.dataset.pointPosition=kind;group.open=kind==='source';
    const summary=document.createElement('summary');summary.textContent=title;group.append(summary);
    for(const label of [...form.querySelectorAll('label[data-parameter]')])if(label.dataset.parameter.startsWith(kind+'_')){
      const input=label.querySelector('input');input.setAttribute('aria-label',label.textContent);
      label.firstChild.textContent=label.firstChild.textContent.replace(title+' · ','');group.append(label);
    }
    form.append(group);
  }
}
document.getElementById('parameters').addEventListener('invalid',event=>{const group=event.target.closest('[data-point-position]');if(group)group.open=true;},true);
function pointLensBasis(g){
  const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0),norm=a=>Math.hypot(...a),n=g.optical_axis_unit;
  let seed=Math.abs(n[0])<.9?[1,0,0]:[0,1,0];
  const k=dot(seed,n),x=seed.map((a,i)=>a-k*n[i]),length=norm(x),ex=x.map(a=>a/length);
  const ey=[n[1]*ex[2]-n[2]*ex[1],n[2]*ex[0]-n[0]*ex[2],n[0]*ex[1]-n[1]*ex[0]];
  return {ex,ey,dot,sky:v=>{const world=g.sky_x_unit.map((a,i)=>a*v[0]+g.sky_y_unit[i]*v[1]);return [dot(world,ex),dot(world,ey)];}};
}
function readPointLensProbe(value){
  const data=response.result.point_lens,g=data.geometry,mas=response.result.units.angular_mas_per_rad;
  if(value.kind==='ring'){
    byId('probe').textContent=`Anel de Einstein · limite da fonte pontual\nRaio angular paraxial: ${format(g.einstein_angle_rad*mas)} mas\nRaio no plano da lente: ${format(g.einstein_radius_m)} m\nAmplificação: indefinida neste limite. Afaste a fonte para obter duas imagens.`;
    return;
  }
  const im=value.image,prefix=value.reference?'Referência completa · ':'',name=im.label==='outer'?'Imagem externa':im.label==='inner'?'Imagem interna':'Imagem direta hipotética';
  const sky=pointLensBasis(g).sky(im.sky_paraxial_rad);
  byId('probe').textContent=`${prefix}${name}\nParidade: ${im.parity>0?'+1':'−1 · imagem invertida'}\nAmplificação absoluta: ${format(im.magnification_abs)}\nPosição paraxial X/Y no céu: ${sky.map(x=>format(x*mas)).join('; ')} mas\nDesvio aplicado no plano: ${format(im.physical_deflection_rad*mas)} mas`+(im.impact_m===undefined?'':`\nImpacto no plano: ${format(im.impact_m)} m · ${format(im.impact_rs)} rₛ`);
}
function drawPointLens(r,w,h){
  const data=r.point_lens,g=data.geometry,a=data.actual,ref=data.reference,control=response.configuration.controls.gravity;
  const basis=pointLensBasis(g),te=g.einstein_angle_rad,mas=r.units.angular_mas_per_rad,show=control.visible;
  const mode=byId('point-lens-view').value;
  projectedArrows=[];
  byId('viewport').dataset.mode='lensing';byId('axis-control').hidden=true;byId('curve-legend').hidden=true;
  byId('reference-entry').hidden=!show;byId('reference-entry').innerHTML='<span class="reference-dot"></span>Lente completa · referência';
  byId('point-lens-geometry').textContent=`Observador → plano da lente: ${format(g.Dl_m/r.units.kpc_m)} kpc\nObservador → plano da fonte: ${format(g.Ds_m/r.units.kpc_m)} kpc · entre planos: ${format(g.Dls_m/r.units.kpc_m)} kpc`;
  const outer=a.images.find(im=>im.label==='outer'||im.label==='direct_intervention'),inner=a.images.find(im=>im.label==='inner');
  byId('point-lens-measure-outer').hidden=!outer;byId('point-lens-measure-outer').textContent=outer?.label==='direct_intervention'?'Medir imagem direta':'Medir imagem externa';
  byId('point-lens-measure-inner').hidden=!inner;byId('point-lens-measure-ring').hidden=!a.ring;
  context.font='12px Segoe UI';context.textAlign='left';
  const line=(points,color,width=1.5,dash=[])=>{context.strokeStyle=color;context.lineWidth=width;context.setLineDash(dash);context.beginPath();points.forEach((p,i)=>i?context.lineTo(...p):context.moveTo(...p));context.stroke();context.setLineDash([]);};
  function marker(p,color,label,value,filled=true){
    if(p[0]<8||p[0]>w-8||p[1]<8||p[1]>h-8)return false;
    context.strokeStyle=color;context.fillStyle=color;context.lineWidth=2;context.beginPath();context.arc(p[0],p[1],5.5,0,2*Math.PI);filled?context.fill():context.stroke();
    if(label){context.fillStyle=color;context.font='12px Segoe UI';context.fillText(label,p[0]+9,p[1]-9);}
    if(value)projectedArrows.push({x:p[0],y:p[1],pointLens:value});return true;
  }
  if(mode==='sky'){
    const visible=[...a.images,...(show?ref.images:[])],source=basis.sky(g.source_paraxial_beta_rad);
    const maximum=Math.max(1.3,...visible.map(im=>Math.hypot(...im.sky_paraxial_rad)/te),Math.hypot(...source)/te);
    const extent=(byId('framing').value==='focus'?2.5:maximum*1.3)/zoom;
    const left=68,right=w-28,top=50,bottom=h-58,cx=(left+right)/2,cy=(top+bottom)/2;
    const scale=Math.min(right-left,bottom-top)/(2*extent),point=v=>[cx+v[0]/te*scale,cy-v[1]/te*scale];
    for(let tick=-2;tick<=2;tick++){
      const v=tick*extent/2,posX=cx+v*scale,posY=cy-v*scale;
      line([[posX,top],[posX,bottom]],'#29404c',.7);line([[left,posY],[right,posY]],'#29404c',.7);
      context.fillStyle='#acc2cc';context.font='10px Segoe UI';context.textAlign='center';context.fillText(format(v*te*mas),posX,bottom+20);
      context.textAlign='right';context.fillText(format(v*te*mas),left-8,posY+3);
    }
    context.textAlign='left';context.fillStyle='#c7dce3';context.font='12px Segoe UI';context.fillText('Céu do observador · ângulos paraxiais / mas',left,25);
    if(show){context.strokeStyle='#b2a1fa88';context.setLineDash([5,5]);context.lineWidth=1;context.beginPath();context.arc(cx,cy,scale,0,2*Math.PI);context.stroke();context.setLineDash([]);
      const q=point(source);marker(q,'#e7abca','Fonte sem desvio',null,false);
      if(!data.acting.ray_bending)for(const im of ref.images)marker(point(basis.sky(im.sky_paraxial_rad)),'#b2a1fa','',{kind:'image',image:im,reference:true},false);
    }
    marker([cx,cy],'#ffcf88','Lente',null);
    if(a.ring){context.strokeStyle='#74ddd1';context.lineWidth=3;context.beginPath();context.arc(cx,cy,scale,0,2*Math.PI);context.stroke();projectedArrows.push({x:cx+scale,y:cy,pointLens:{kind:'ring'}});}
    let offscreen=false;
    for(const im of a.images)if(!marker(point(basis.sky(im.sky_paraxial_rad)),'#74ddd1',im.label==='inner'?'−':im.label==='outer'?'+':'Direta',{kind:'image',image:im},im.label!=='inner'))offscreen=true;
    byId('scale-label').textContent=`Céu: ${format(2*extent*te*mas)} mas na menor dimensão · X do referencial projetado`;
    byId('view-help').textContent=offscreen?'Há uma imagem fora da região. Escolha Todas as imagens ou reduza o zoom.':'Clique nas imagens para medir · roda para zoom · marcadores simbólicos, sem escala de brilho';
  }else{
    const left=65,right=w-45,top=55,bottom=h-60,cy=(top+bottom)/2;
    const beta=g.source_paraxial_beta_rad,betaSize=Math.hypot(...beta),axis=betaSize?beta.map(x=>x/betaSize):[1,0];
    const tangent=g.sky_x_unit.map((v,i)=>v*axis[0]+g.sky_y_unit[i]*axis[1]);
    const xFor=z=>left+(right-left)*z/g.Ds_m;
    const offset=point=>basis.dot(point.map((v,i)=>v-data.configuration.lens_m[i]),tangent);
    const cfg=data.configuration,sourceOffset=offset(cfg.source_m);
    const all=[...a.images,...(show?ref.images:[])];
    const span=Math.max(g.einstein_radius_m*1.5,Math.abs(sourceOffset),...all.map(im=>Math.abs(offset(im.lens_plane_world_m))))*1.25/zoom;
    const yFor=v=>cy-v/span*(bottom-top)*.45,lx=xFor(g.Dl_m);
    line([[left,cy],[right,cy]],'#45616c',1,[4,5]);line([[lx,top],[lx,bottom]],'#b2a1fa55',1,[3,5]);
    const sourceP=[right,yFor(sourceOffset)],observerP=[left,cy];
    context.fillStyle='#c7dce3';context.font='12px Segoe UI';context.fillText('Construção em planos finos · escala transversal ampliada',left,25);
    if(show&&!data.acting.ray_bending)for(const im of ref.images)line([observerP,[lx,yFor(offset(im.lens_plane_world_m))],sourceP],'#b2a1fa',1.5,[5,5]);
    if(a.ring){
      const radius=g.einstein_radius_m;context.fillStyle='#74ddd112';context.beginPath();context.moveTo(...observerP);context.lineTo(lx,yFor(radius));context.lineTo(...sourceP);context.lineTo(lx,yFor(-radius));context.closePath();context.fill();
      for(const sign of [-1,1])line([observerP,[lx,yFor(sign*radius)],sourceP],'#74ddd1',1.5,[4,4]);
      projectedArrows.push({x:lx,y:yFor(radius),pointLens:{kind:'ring'}});
    }
    for(const im of a.images){const p=[lx,yFor(offset(im.lens_plane_world_m))];line([observerP,p,sourceP],'#74ddd1',2);marker(p,'#74ddd1',im.label==='inner'?'−':im.label==='outer'?'+':'Direta',{kind:'image',image:im},im.label!=='inner');}
    marker(observerP,'#87c7ff','Observador',null);marker([lx,cy],'#ffcf88','Lente',null);marker(sourceP,'#e7abca','Fonte',null);
    context.font='11px Segoe UI';context.fillStyle='#bdd1d8';context.fillText(`0 → ${format(g.Ds_m/r.units.kpc_m)} kpc`,left,bottom+30);
    byId('scale-label').textContent=`Longitudinal: ${format(g.Ds_m/r.units.kpc_m)} kpc · escala transversal: ±${format(span/r.units.au_m)} au`;
    byId('view-help').textContent=a.ring?'Corte ilustrativo da família do anel · amplificação pontual indefinida':'Raios aproximados em dois trechos · clique na passagem pelo plano da lente para medir';
  }
  context.textAlign='left';
}
document.getElementById('point-lens-view').onchange=()=>{byId('probe').textContent='';draw();};
document.getElementById('point-lens-align').onclick=()=>{
  if(pending||draftConfig.scenario!=='point-lens')return;
  for(const kind of ['observer','lens','source'])for(const axis of ['x','y'])byId('parameters').elements[kind+'_'+axis+'_au'].value=0;
  calculate();
};
document.getElementById('point-lens-measure-outer').onclick=()=>{const im=response?.result.point_lens?.actual.images.find(im=>im.label==='outer'||im.label==='direct_intervention');if(im)readPointLensProbe({kind:'image',image:im});};
document.getElementById('point-lens-measure-inner').onclick=()=>{const im=response?.result.point_lens?.actual.images.find(im=>im.label==='inner');if(im)readPointLensProbe({kind:'image',image:im});};
document.getElementById('point-lens-measure-ring').onclick=()=>{if(response?.result.point_lens?.actual.ring)readPointLensProbe({kind:'ring'});};
