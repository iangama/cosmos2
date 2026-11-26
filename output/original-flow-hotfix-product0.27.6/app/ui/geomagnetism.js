// Projection and colour presentation only; all field/force readings come from backend.
let geomagneticProbe=null;
function formatEpoch(year){return year.toLocaleString('pt-BR',{useGrouping:false,maximumFractionDigits:6});}
const geomagneticTexture=new Image();
geomagneticTexture.onload=()=>{if(response?.result?.geomagnetic)draw();};
function geomagneticScalar(point,key){return key==='X_nT'?point.field_ned_nT[0]:key==='Y_nT'?point.field_ned_nT[1]:key==='Z_nT'?point.field_ned_nT[2]:point[key];}
function geomagneticColour(value,min,max){
  if(value==null)return '#65717c';
  const t=Math.max(0,Math.min(1,(value-min)/(max-min||1)));
  const stops=[[45,67,130],[57,154,169],[139,218,163],[255,205,117]],scaled=t*3,i=Math.min(2,Math.floor(scaled)),f=scaled-i;
  return `rgb(${stops[i].map((x,k)=>Math.round(x+(stops[i+1][k]-x)*f)).join(',')})`;
}
function geomagneticCellValue(corners,key){
  const values=corners.map(p=>geomagneticScalar(p,key)).filter(v=>v!=null);
  if(!values.length)return null;
  if(key==='D_deg'){const x=values.reduce((s,v)=>s+Math.cos(v*Math.PI/180),0),y=values.reduce((s,v)=>s+Math.sin(v*Math.PI/180),0);return Math.hypot(x,y)<1e-10?null:Math.atan2(y,x)*180/Math.PI;}
  return values.reduce((s,v)=>s+v,0)/values.length;
}
function readGeomagneticProbe(point){
  const full=byId('geomagnetic-model').value==='full';
  const mode=full?'IGRF14 completo':'Comparação dipolar · grau 1';
  const panel=byId('probe');panel.replaceChildren();
  const heading=document.createElement('b');heading.className='probe-heading';
  heading.textContent=`${mode} · ${format(point.latitude_deg)}°, ${format(point.longitude_deg)}° · época ${formatEpoch(point.year_decimal)} · altitude WGS84 ${format(point.altitude_m/1000)} km`;panel.append(heading);
  const values=[['Norte X',`${format(point.field_ned_nT[0])} nT`],['Leste Y',`${format(point.field_ned_nT[1])} nT`],['Para baixo Z',`${format(point.field_ned_nT[2])} nT`],['Intensidade F',`${format(point.F_nT)} nT`],['Declinação / inclinação',`${format(point.D_deg)}° / ${format(point.I_deg)}°`],['Potência magnética',`${format(point.magnetic_power_W)} W`],['Força'+(full?' aplicada':' comparativa')+' N/L/baixo',`${point.magnetic_force_ned_N.map(format).join(', ')} N`]];
  for(const [label,value] of values){const cell=document.createElement('span'),title=document.createElement('small'),reading=document.createElement('strong');title.textContent=label;reading.textContent=value;cell.append(title,reading);panel.append(cell);}
  const note=document.createElement('small');note.className='probe-note';note.textContent=point.frame_note;panel.append(note);
}
function drawGeomagnetic(r,w,h){
  const g=r.geomagnetic,mode=byId('geomagnetic-model').value,key=byId('geomagnetic-component').value;
  const grid=g.grid.map(entry=>entry[mode]),primary=g[mode],visible=config.controls.electromagnetic.visible;
  const values=g.grid.map(entry=>geomagneticScalar(entry.full,key)).filter(v=>v!=null),min=Math.min(...values),max=Math.max(...values);
  byId('viewport').dataset.mode='geomagnetic';byId('axis-control').hidden=true;
  byId('curve-legend').hidden=true;byId('reference-entry').hidden=true;
  byId('scale-label').textContent=`${mode==='full'?'IGRF14 completo':'Grau 1 dos mesmos coeficientes'} · ${formatEpoch(g.year_decimal)} · ${format(g.altitude_m/1000)} km WGS84`;
  projectedArrows=[];context.font='11px Segoe UI';context.fillStyle='#b9cad8';
  const title=byId('geomagnetic-component').selectedOptions[0].textContent;
  context.fillText(`${title} · cores da referência completa, escala comum`,18,24);
  if(byId('geomagnetic-view').value==='map'){
    const left=52,top=52,width=w-80,height=h-155;
    const point=p=>[left+(p.longitude_deg+180)/360*width,top+(90-p.latitude_deg)/180*height];
    if(!geomagneticTexture.src)geomagneticTexture.src='/api/geomagnetism/texture';
    if(geomagneticTexture.complete&&geomagneticTexture.naturalWidth){context.globalAlpha=.7;context.drawImage(geomagneticTexture,left,top,width,height);context.globalAlpha=1;}
    if(visible){context.save();context.beginPath();context.rect(left,top,width,height);context.clip();context.globalAlpha=.64;
      for(const p of grid){const a=point(p);context.fillStyle=geomagneticColour(geomagneticScalar(p,key),min,max);context.fillRect(a[0]-width/72,a[1]-height/36,width/36+.5,height/18+.5);projectedArrows.push({x:a[0],y:a[1],geomagnetic:p});}
      context.restore();}
    context.strokeStyle='#a4bfcb55';context.lineWidth=1;
    for(let lat=-90;lat<=90;lat+=30){const y=point({longitude_deg:-180,latitude_deg:lat})[1];context.beginPath();context.moveTo(left,y);context.lineTo(left+width,y);context.stroke();context.fillStyle='#c0cdd7';context.fillText(lat+'°',9,y+4);}
    for(let lon=-180;lon<=180;lon+=60){const x=point({longitude_deg:lon,latitude_deg:0})[0];context.beginPath();context.moveTo(x,top);context.lineTo(x,top+height);context.stroke();context.fillText(lon+'°',Math.min(left+width-24,x-12),top+height+20);}
    const a=point(primary);context.strokeStyle='#fff';context.lineWidth=2;context.beginPath();context.arc(a[0],a[1],6,0,2*Math.PI);context.stroke();projectedArrows.push({x:a[0],y:a[1],geomagnetic:primary});
    byId('view-help').textContent='Longitude leste e latitude geodética · clique numa amostra para medir · base NASA, cores IGRF calculadas';
  }else{
    const originalZoom=zoom;zoom=originalZoom*Math.min(w,h)*.32;
    const radius=6371200,projectPoint=p=>project(p.position_ecef_m.map(v=>v/radius),w,h,[0,0,0]);
    if(visible){
      const cells=[];
      for(let i=0;i<18;i++)for(let j=0;j<36;j++){const corners=[grid[i*37+j],grid[i*37+j+1],grid[(i+1)*37+j+1],grid[(i+1)*37+j]];const projected=corners.map(projectPoint),depth=projected.reduce((a,p)=>a+p[2],0)/4;if(depth>0)cells.push({projected,depth,value:geomagneticCellValue(corners,key)});}
      cells.sort((a,b)=>a.depth-b.depth);context.globalAlpha=.45;
      for(const cell of cells){context.fillStyle=geomagneticColour(cell.value,min,max);context.beginPath();cell.projected.forEach((p,i)=>i?context.lineTo(p[0],p[1]):context.moveTo(p[0],p[1]));context.closePath();context.fill();}
      context.globalAlpha=1;
    }
    function line(points){context.strokeStyle='#94b9cb55';context.lineWidth=.8;context.beginPath();let begun=false;for(const p of points){const q=projectPoint(p);if(q[2]<0){begun=false;continue;}begun?context.lineTo(q[0],q[1]):context.moveTo(q[0],q[1]);begun=true;}context.stroke();}
    function surface(lat,lon){const phi=lat*Math.PI/180,lam=lon*Math.PI/180,e2=1/298.257223563*(2-1/298.257223563),n=6378137/Math.sqrt(1-e2*Math.sin(phi)**2);return {position_ecef_m:[n*Math.cos(phi)*Math.cos(lam),n*Math.cos(phi)*Math.sin(lam),n*(1-e2)*Math.sin(phi)]};}
    for(let lon=-180;lon<180;lon+=30)line(Array.from({length:73},(_,i)=>surface(-90+i*2.5,lon)));
    for(let lat=-60;lat<=60;lat+=30)line(Array.from({length:145},(_,i)=>surface(lat,-180+i*2.5)));
    if(visible)for(const p of grid){if(Math.abs(p.latitude_deg)===90&&p.longitude_deg!==-180)continue;const a=projectPoint(p);if(a[2]<0)continue;const b=p.field_ecef_T,m=Math.hypot(...b),position=p.position_ecef_m.map(v=>v/radius);const end=project(position.map((v,k)=>v+.14*b[k]/m),w,h,[0,0,0]);context.strokeStyle=geomagneticColour(geomagneticScalar(p,key),min,max);context.lineWidth=1.1;context.beginPath();context.moveTo(a[0],a[1]);context.lineTo(end[0],end[1]);context.stroke();const angle=Math.atan2(end[1]-a[1],end[0]-a[0]);context.beginPath();context.moveTo(end[0],end[1]);context.lineTo(end[0]-5*Math.cos(angle-.5),end[1]-5*Math.sin(angle-.5));context.moveTo(end[0],end[1]);context.lineTo(end[0]-5*Math.cos(angle+.5),end[1]-5*Math.sin(angle+.5));context.stroke();projectedArrows.push({x:a[0],y:a[1],geomagnetic:p});}
    const a=projectPoint(primary);if(a[2]>0){context.fillStyle='#fff';context.beginPath();context.arc(a[0],a[1],5,0,Math.PI*2);context.fill();projectedArrows.push({x:a[0],y:a[1],geomagnetic:primary});}
    zoom=originalZoom;byId('view-help').textContent='Arraste para orbitar · setas de B normalizadas para exibição · campo exterior na altitude escolhida';
  }
  if(visible){const x=60,y=h-66,width=Math.min(260,w*.35);for(let i=0;i<100;i++){context.fillStyle=geomagneticColour(min+(max-min)*i/99,min,max);context.fillRect(x+i*width/100,y,width/100+1,8);}context.fillStyle='#c6d6df';context.fillText(format(min),x,y+23);context.fillText(format(max),x+width-55,y+23);context.fillText(key.endsWith('deg')?'graus':'nT',x+width+12,y+9);}
  if(geomagneticProbe)readGeomagneticProbe(geomagneticProbe);else readGeomagneticProbe(primary);
}
