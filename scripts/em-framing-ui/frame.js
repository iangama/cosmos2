'use strict';
let canvasFrameScope='layers',canvasZoom=1,canvasProjectionState=null;
function canvasContentPoints(scope=canvasFrameScope){
  if(!state)return [];
  const ex=state.experiment,matter=positions(),fixed=ex.mode==='test_particle'?ex.model.sources.map(s=>s.position_m):[];
  let points=[...matter,...fixed,...trail.map(s=>s.p)];
  if(scope==='layers'){
    for(const curve of fieldLines?.curves||[]){
      if(state.editor.visual[curve.quantity+'_visible'])points.push(...curve.points_m);
    }
    for(const sample of map?.samples||[]){
      if(!sample.valid)continue;
      for(const [term,key] of [['electric','electric_field_V_m'],['magnetic','magnetic_field_T']]){
        const v=sample[key],m=Math.hypot(...v);
        if(state.editor.visual[term+'_visible']&&m){points.push(sample.position_m,sample.position_m.map((x,k)=>x+.35*v[k]/m));}
      }
    }
    if(nativeState?.potential?.settings.visible)for(const segment of potentialLayer?.geometry.segments||[])points.push(...segment.points_m);
  }
  if(!points.length)points=[[0,0,0]];
  return points;
}
function syncCanvasPreferences(){
  const view=nativeState?.canvas_view;if(!view)return;canvasFrameScope=view.scope;canvasZoom=view.zoom;$('canvas-zoom').value=String(canvasZoom);
}
function makeCanvasProjection(width,height){
  syncCanvasPreferences();
  const points=canvasContentPoints(),ca=Math.cos(azimuth),sa=Math.sin(azimuth),ce=Math.cos(elevation),se=Math.sin(elevation);
  const raw=p=>[ca*p[0]-sa*p[1],ce*p[2]-se*(sa*p[0]+ca*p[1])];
  let low=[Infinity,Infinity],high=[-Infinity,-Infinity];
  for(const p of points){const q=raw(p);for(let k=0;k<2;k++){low[k]=Math.min(low[k],q[k]);high[k]=Math.max(high[k],q[k]);}}
  const spans=high.map((v,k)=>v-low[k]),minimum=Math.max(1e-12,state.editor.visual.map_radius_m*.25);
  const scale=.84*Math.min(width/Math.max(spans[0],minimum),height/Math.max(spans[1],minimum))*canvasZoom;
  const center=high.map((v,k)=>low[k]+(v-low[k])/2);
  canvasProjectionState={width,height,scale_px_per_m:scale,projected_center_m:center,projected_extent_m:spans,scope:canvasFrameScope,zoom:canvasZoom,points:points.length};
  return p=>{const q=raw(p);return [width/2+scale*(q[0]-center[0]),height/2-scale*(q[1]-center[1])];};
}
async function frameCurrentEMView(layers=false){
  if(nativeMode){await nativeRequest('frame',{include_layers:layers});return;}
  await command('configure_canvas_view',{...guard(),changes:{scope:layers?'layers':'matter',zoom:1}});draw();
  $('status').textContent=layers?'Mapa enquadrado pelas camadas visíveis e posições observadas.':'Mapa enquadrado pela matéria e sua trajetória observada.';
}
$('native-frame').onclick=()=>run(()=>frameCurrentEMView(false));
$('frame-layers').onclick=()=>run(()=>frameCurrentEMView(true));
$('orient-cut').onclick=()=>run(async()=>{
  const a=0,e=1.4;
  await command('set_visual',{...guard(),changes:{azimuth_rad:a,elevation_rad:e}});
  azimuth=a;elevation=e;await frameCurrentEMView(true);
});
$('canvas-zoom').onchange=()=>{const zoom=Number($('canvas-zoom').value);run(()=>command('configure_canvas_view',{...guard(),changes:{zoom}}));};
const previousNativeRender=window.renderNativeEM;
window.renderNativeEM=()=>{
  syncCanvasPreferences();previousNativeRender();
  $('native-frame').textContent=nativeMode?'Enquadrar matéria':'Enquadrar matéria no mapa';
  $('frame-layers').textContent=nativeMode?'Enquadrar camadas':'Enquadrar camadas no mapa';
  const tracked=state?.experiment.mode==='mutual_electrostatic'?'carga '+state.experiment.system.ids[0]:'partícula de teste';
  $('trajectory-state').textContent=nativeMode?'Trajetória observada da '+tracked+' disponível no mapa interativo.':trail.length+' posições observadas da '+tracked+(trail.length?' · t = '+number(trail[0].time)+' a '+number(trail.at(-1).time)+' s':'')+'. Os segmentos unem essas posições; linhas E/B representam campos.';
};
window.makeCanvasProjection=makeCanvasProjection;
window.renderNativeEM();
