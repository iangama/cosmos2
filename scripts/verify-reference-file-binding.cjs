'use strict';
// Isolated regression for the File-wrapper replacement observed in native CEF.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),opts=Object.fromEntries(process.argv.slice(2).map(v=>{const i=v.indexOf('=');return[v.slice(0,i),v.slice(i+1)];}));
const label=opts['--label'];assert(/^[a-z0-9-]+$/.test(label||''));
const base=path.join(root,'output/original-flow-hotfix-product0.27.5/app/ui'),overrides=opts['--ui-overrides']&&path.resolve(root,opts['--ui-overrides']);
const out=path.join(root,'evidence',`reference-file-binding-${label}.json`);assert(!fs.existsSync(out));
const fileFor=name=>overrides&&fs.existsSync(path.join(overrides,name))?path.join(overrides,name):path.join(base,name);
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),sha=file=>hash(fs.readFileSync(file));
const proof={accepted:false,completed:false,native_user_flow_accepted:false,checks:[],scope:'Isolated existing panel HTML/JS with an in-memory adapter. Replace a selected File by a byte-identical new wrapper without change event, as observed natively; verify real change invalidation and exact source-text rejection. No scientific model, real branch storage, renderer or native journey acceptance.',source_sha256:Object.fromEntries([__filename,...['index.html','is6-spatial.js','is6-layers.js','reference-panels.js'].map(fileFor)].map(p=>[path.relative(root,p),sha(p)]))};
let fixture;
const fresh=()=>({active:false,error:null,recovery_required:false,busy:false,guard:{session_id:'fixture-session',artifact_id:null,revision:0},artifact:null,scene:null,checkpoint_available:false,branches:[],import_preview:null,transaction:null});
const reset=()=>{fixture={state:{spatial:fresh(),layers:fresh()},source:{},commits:[]};};reset();
const bootstrap=`let appState={mode:'experiment',physics:{system_id:'fixture-source',edit_token:'fixture-token',revision:1,time:0,paused:true,contract:{frame:'GALACTIC'},atlas_initial:{kind:'solar_four_physical_centers'},bodies:[['sun','Sol','10'],['earth','Terra','399'],['moon','Lua','301'],['jupiter','Júpiter','599']].map(([id,name,code])=>({id,name,reference_id:'sol:naif:'+code}))}},pending=false,atlasPending=false,atlasState={epoch:{utc:'2026-10-11T12:00:00Z'}};const $=id=>document.getElementById(id);function command(){};`;
function reply(res,status,value,type='application/json'){res.writeHead(status,{'Content-Type':type+'; charset=utf-8','Cache-Control':'no-store'});res.end(type==='application/json'?JSON.stringify(value):value);}
const server=http.createServer(async(req,res)=>{
 const route=new URL(req.url,'http://local').pathname,match=route.match(/^\/api\/(spatial|layers)\/(state|import-preview|import-commit|command)$/);
 if(match){const[,kind,operation]=match,s=fixture.state[kind];if(operation==='state')return reply(res,200,s);
  let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);
  if(operation==='import-preview'){
   fixture.source[kind]=body.source_text;s.import_preview={id:'fixture-preview',valid:true,source_format:'isolated-fixture',source_sha256:hash(body.source_text),body_reference_id:'sol:naif:399',epoch:{utc:'2026-10-11T12:00:00Z'},magnetic_model:'IGRF14',visible:{spatial:true,magnetic:true},changes:[],configuration:{inner_radius_boundary_units:1,outer_radius_boundary_units:3,radial_count:65,azimuth_sectors:96},view:{selected_radial_index:0,selected_azimuth_index:0,reference_radial_index:64,visible:true}};
   return reply(res,200,{ok:true,[kind]:s,result:{}});
  }
  if(operation==='import-commit'){
   if(body.source_text!==fixture.source[kind])return reply(res,400,{ok:false,error:'O arquivo mudou após a prévia; valide novamente.'});
   const branch={id:'new-branch',name:body.name,valid:true};s.branches.push(branch);s.import_preview=null;fixture.commits.push(body);
   return reply(res,200,{ok:true,[kind]:s,result:{record:kind==='spatial'?{branch}:branch}});
  }
  return reply(res,200,{ok:true,[kind]:s,result:{}});
 }
 if(route==='/'){
  let html=fs.readFileSync(fileFor('index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
  html=html.replace('</body>',`<script>${bootstrap}</script><script src="reference-panels.js"></script><script src="is6-spatial.js"></script><script src="is6-layers.js"></script></body>`);
  return reply(res,200,html,'text/html');
 }
 if(/^\/[a-z0-9.-]+\.(js|css)$/.test(route)){const p=fileFor(route.slice(1));if(fs.existsSync(p))return reply(res,200,fs.readFileSync(p),route.endsWith('.js')?'text/javascript':'text/css');}
 return reply(res,404,{});
});
let browser,context,origin;
async function bind(page,kind,content='{"fixture":1}',change=true){
 await page.evaluate(({kind,content,change})=>{const input=document.getElementById(kind+'-import-file'),data=new DataTransfer();data.items.add(new File([content],'same-reference.json',{type:'application/json',lastModified:12345}));input.files=data.files;if(change)input.dispatchEvent(new Event('change',{bubbles:true}));},{kind,content,change});
}
async function preview(page,kind){await page.locator('#'+kind+'-import-preview').click();await page.waitForFunction(k=>!!window[k==='spatial'?'spatialInstrument':'layerInstrument'].snapshot.import_preview&&!window[k==='spatial'?'spatialInstrument':'layerInstrument'].pending&&!window[k==='spatial'?'spatialInstrument':'layerInstrument'].readingFile,kind);}
async function test(kind,name,run){
 reset();const page=await context.newPage();page.setDefaultTimeout(2300);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{await page.goto(origin);await page.waitForFunction(()=>window.spatialInstrument.online&&window.layerInstrument.online);await page.locator('#open-'+kind).click();await page.locator('#'+kind+(kind==='spatial'?'-import-section':'-import')+'>summary').click();await bind(page,kind);await preview(page,kind);await run(page);assert.deepEqual(errors,[]);proof.checks.push({name:kind+'-'+name,passed:true});}
 catch(error){proof.checks.push({name:kind+'-'+name,passed:false,error:error.message,errors});}finally{await page.close();}
}
async function main(){
 const{chromium}=require('/home/an/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');await new Promise(r=>server.listen(0,'127.0.0.1',r));origin='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({headless:true});context=await browser.newContext({viewport:{width:1440,height:900}});
 for(const kind of ['spatial','layers']){
  await test(kind,'same-bytes-new-wrapper-can-be-imported',async page=>{
   await bind(page,kind,'{"fixture":1}',false);await page.waitForTimeout(650);
   assert(!(await page.locator('#'+kind+'-import-commit').isDisabled()),'Byte-identical native re-selection must not disable import');
   assert.match(await page.locator('#'+kind+'-import-reading').innerText(),/Pronto para criar/);
   await page.locator('#'+kind+'-import-name').fill('Mesmo arquivo conferido');assert(!(await page.locator('#'+kind+'-import-commit').isDisabled()));
   await page.locator('#'+kind+'-import-commit').click();await page.waitForFunction(k=>window[k==='spatial'?'spatialInstrument':'layerInstrument'].snapshot.branches.length===1,kind);assert.equal(fixture.commits.length,1);
  });
  await test(kind,'ordinary-change-requires-new-preview',async page=>{
   await bind(page,kind);assert(await page.locator('#'+kind+'-import-commit').isDisabled());assert(!/Pronto para criar/.test(await page.locator('#'+kind+'-import-reading').innerText()),'A previous source must not remain presented as ready');
  });
  await test(kind,'changed-bytes-with-identical-metadata-still-rejected',async page=>{
   await bind(page,kind,'{"fixture":2}',false);await page.waitForTimeout(650);assert(!(await page.locator('#'+kind+'-import-commit').isDisabled()));
   await page.locator('#'+kind+'-import-commit').click();await page.waitForFunction(k=>document.getElementById(k+'-error').textContent.includes('arquivo mudou'),kind);assert.equal(fixture.commits.length,0);
  });
 }
 proof.completed=true;proof.accepted=proof.checks.every(row=>row.passed);
}
main().catch(e=>proof.failure=e.stack).finally(async()=>{if(context)await context.close();if(browser)await browser.close();await new Promise(r=>server.close(r));fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');console.log(JSON.stringify({accepted:proof.accepted,checks:proof.checks,failure:proof.failure}));process.exitCode=proof.accepted?0:1;});
