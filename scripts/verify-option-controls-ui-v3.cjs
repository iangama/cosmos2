'use strict';
// Focused DOM/keyboard/layout checks. Native mouse delivery is a separate gate.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const crypto=require('node:crypto'),assert=require('node:assert/strict');
const opts=Object.fromEntries(process.argv.slice(2).map(value=>{const i=value.indexOf('=');return [value.slice(0,i),value.slice(i+1)];}));
const root=path.resolve(__dirname,'..'),label=opts['--label'];assert(/^[a-z0-9-]+$/.test(label||''));
const product=path.resolve(root,opts['--product']||'output/original-flow-hotfix-product0.27.4');
const ui=path.join(product,'app/ui'),folder=path.join(root,'output',`option-controls-ui-${label}`),out=path.join(root,'evidence',`option-controls-ui-${label}.json`);
assert(!fs.existsSync(folder)&&!fs.existsSync(out));fs.mkdirSync(folder);
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const proof={accepted:false,completed:false,native_user_flow_accepted:false,scope:'Isolated page DOM/keyboard/layout regression checks. No native renderer or original owner-entry acceptance.',
 source_sha256:Object.fromEntries([__filename,...['index.html','forces.html','forces.js','option-controls.css','option-controls.js'].map(name=>path.join(ui,name))].map(file=>[path.relative(root,file),sha(file)])),checks:[],captures:[]};
const fixtures=path.join(root,'output/forces-confirmed-ui-fixtures-20261120a');
const catalog=JSON.parse(fs.readFileSync(path.join(fixtures,'catalog.json'))),posts=[];
const fixtureHtml=`<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="option-controls.css"></head>
<body><aside id="test-panel" class="glass" style="overflow:auto"><form id="test-form"><label class="field">Corpo de referência<select id="test-choice" name="body" required><option value="earth">Terra</option><option value="jupiter">Júpiter</option><option disabled value="missing">Indisponível</option><option hidden value="hidden">Oculta</option><option value="moon">Lua</option></select></label>
<fieldset id="test-fieldset"><label class="field">Ramos salvos<select id="test-branches" name="branch"></select></label></fieldset><button type="submit">Aplicar</button></form></aside>
<footer class="glass"><label>Interface <select id="test-scale"><option value="1">100%</option><option value="1.25">125%</option><option value="1.5">150%</option></select></label></footer>
<script>window.events=[];window.submits=0;document.querySelectorAll('select').forEach(s=>['input','change'].forEach(type=>s.addEventListener(type,()=>events.push({id:s.id,type,value:s.value}))));document.getElementById('test-form').onsubmit=e=>{e.preventDefault();submits++};document.getElementById('test-scale').onchange=e=>document.documentElement.style.setProperty('--ui-scale',e.target.value);</script><script src="option-controls.js"></script></body></html>`;
const server=http.createServer(async(req,res)=>{
 const route=new URL(req.url,'http://local').pathname;
 const reply=(status,value,type='application/json')=>{res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store'});res.end(type==='application/json'?JSON.stringify(value):value);};
 if(route==='/fixture')return reply(200,fixtureHtml,'text/html; charset=utf-8');
 if(route==='/api/forces/catalog')return reply(200,catalog);
 if(route==='/api/forces/evaluate'){
  let body='';for await(const chunk of req)body+=chunk;const data=JSON.parse(body);posts.push(data);
  return reply(200,JSON.parse(fs.readFileSync(path.join(fixtures,data.scenario+'.json'))));
 }
 if(route==='/api/geomagnetism/texture')return reply(200,fs.readFileSync(path.join(product,'data/textures/earth.jpg')),'image/jpeg');
 if(/^\/[a-z0-9.-]+\.(js|css|html)$/.test(route)){
  const file=path.join(ui,route.slice(1));if(fs.existsSync(file))return reply(200,fs.readFileSync(file),route.endsWith('.html')?'text/html; charset=utf-8':route.endsWith('.css')?'text/css':'text/javascript');
 }
 return reply(404,{});
});
let browser,context,origin;
async function test(name,run,route='/fixture'){
 const page=await context.newPage();page.setDefaultTimeout(2500);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{await page.goto(origin+route,{waitUntil:'load'});await run(page);assert.deepEqual(errors,[]);proof.checks.push({name,passed:true});}
 catch(error){proof.checks.push({name,passed:false,error:error.message,stack:error.stack,errors});}
 finally{await page.close();}
}
const choose=async(page,id,value)=>{await page.locator('#'+id+'-choice').click();await page.locator('[role=option][data-choice-value="'+value+'"]').click();};
async function main(){
 const {chromium}=require('/home/an/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));origin='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({headless:true});context=await browser.newContext({viewport:{width:1440,height:900}});
 await test('mouse-opens-readable-options-and-selects-once',async page=>{
  await choose(page,'test-choice','jupiter');assert.equal(await page.locator('#test-choice').inputValue(),'jupiter');
  assert.deepEqual(await page.evaluate(()=>events),[{id:'test-choice',type:'input',value:'jupiter'},{id:'test-choice',type:'change',value:'jupiter'}]);
  assert.equal(await page.evaluate(()=>submits),0);assert.equal(await page.locator('#test-choice-choice').getAttribute('aria-expanded'),'false');
 });
 await test('same-option-does-not-trigger-recalculation',async page=>{
  await choose(page,'test-choice','earth');assert.deepEqual(await page.evaluate(()=>events),[]);
 });
 await test('escape-cancels-without-changing-selection',async page=>{
  await page.locator('#test-choice-choice').click();await page.keyboard.press('ArrowDown');await page.keyboard.press('Escape');
  assert.equal(await page.locator('#test-choice').inputValue(),'earth');assert.deepEqual(await page.evaluate(()=>events),[]);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'test-choice-choice');
 });
 await test('keyboard-skips-disabled-and-hidden-options',async page=>{
  await page.locator('#test-choice-choice').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('ArrowDown');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  assert.equal(await page.locator('#test-choice').inputValue(),'moon');
 });
 await test('disabled-choice-remains-inert',async page=>{
  await page.evaluate(()=>document.getElementById('test-choice').disabled=true);await page.waitForFunction(()=>document.getElementById('test-choice-choice').getAttribute('aria-disabled')==='true');
  const r=await page.locator('#test-choice-choice').boundingBox();await page.mouse.click(r.x+r.width/2,r.y+r.height/2);assert(await page.locator('.c2-options-portal').isHidden());assert.equal(await page.evaluate(()=>events.length),0);
 });
 await test('fieldset-disabled-closes-an-open-popup',async page=>{
  await page.evaluate(()=>document.getElementById('test-branches').innerHTML='<option>a</option><option>b</option>');
  await page.locator('#test-branches-choice').click();await page.evaluate(()=>document.getElementById('test-fieldset').disabled=true);
  await page.waitForFunction(()=>document.querySelector('.c2-options-portal').hidden);assert.equal(await page.locator('#test-branches-choice').getAttribute('aria-disabled'),'true');
 });
 await test('dynamic-options-and-programmatic-value-stay-readable',async page=>{
  await page.evaluate(()=>{const s=document.getElementById('test-branches');s.innerHTML='<option value="a">Primeiro ramo</option><option value="b">Segundo ramo</option>';s.value='b';});
  await page.waitForFunction(()=>document.getElementById('test-branches-choice').textContent.includes('Segundo ramo'));
  await choose(page,'test-branches','a');assert.equal(await page.locator('#test-branches').inputValue(),'a');
 });
 await test('empty-options-explain-the-state',async page=>{
  await page.locator('#test-branches-choice').click();assert.equal(await page.locator('.c2-choice-empty').innerText(),'Nenhuma opção disponível');await page.keyboard.press('Escape');
 });
 await test('typing-finds-accented-option',async page=>{
  await page.locator('#test-choice-choice').focus();await page.keyboard.type('ju');await page.keyboard.press('Enter');assert.equal(await page.locator('#test-choice').inputValue(),'jupiter');
 });
 await test('label-click-opens-the-correct-control',async page=>{
  const label=page.locator('#test-form>label');await label.click({position:{x:15,y:5}});assert.equal(await page.locator('#test-choice-choice').getAttribute('aria-expanded'),'true');
 });
 await test('form-data-retains-only-original-fields',async page=>{
  assert.deepEqual(await page.evaluate(()=>[...document.getElementById('test-form').elements].map(e=>e.tagName)),['SELECT','FIELDSET','SELECT','BUTTON']);
  await choose(page,'test-choice','jupiter');assert.equal(await page.evaluate(()=>new FormData(document.getElementById('test-form')).get('body')),'jupiter');
 });
 for(const scale of ['1','1.25','1.5'])await test('bottom-popup-fits-and-clicks-at-'+scale,async page=>{
  if(scale!=='1')await choose(page,'test-scale',scale);
  await page.locator('#test-scale-choice').click();const bounds=await page.locator('.c2-options-list').boundingBox();
  assert(bounds.x>=0&&bounds.y>=0&&bounds.x+bounds.width<=1440&&bounds.y+bounds.height<=900,JSON.stringify(bounds));
  const capture=path.join(folder,'popup-'+scale+'.png');await page.screenshot({path:capture});proof.captures.push({path:path.relative(root,capture),sha256:sha(capture)});
  await page.locator('[role=option][data-choice-value="1"]').click();assert.equal(await page.locator('#test-scale').inputValue(),'1');
 });
 await test('long-list-scroll-reaches-the-last-option',async page=>{
  await page.evaluate(()=>document.getElementById('test-branches').innerHTML=Array.from({length:60},(_,i)=>'<option value="'+i+'">Ramo '+i+'</option>').join(''));
  await choose(page,'test-branches','59');assert.equal(await page.locator('#test-branches').inputValue(),'59');
 });
 await test('actual-forces-form-keeps-parameter-names-and-change-events',async page=>{
  await page.waitForFunction(()=>typeof response!=='undefined'&&response?.ok&&!pending);
  await page.locator('[data-scenario=decays]').click();await page.waitForFunction(()=>!pending&&config.scenario==='decays');
  const trigger=page.locator('#parameters .c2-choice-trigger').first();
  const info=await page.locator('#parameters select').first().evaluate(s=>({name:s.name,values:[...s.options].map(o=>o.value),id:s.id}));
  await trigger.click();await page.locator('[role=option][data-choice-value=\"'+info.values[1]+'\"]').click();
  assert(await page.locator('#result-draft-note').isVisible());await page.locator('#calculate').click();await page.waitForFunction(()=>!pending);
  assert.equal(posts.at(-1).parameters[info.name],info.values[1]);assert(!Object.hasOwn(posts.at(-1).parameters,''));
 },'/forces.html');
 await test('forces-legend-control-keeps-a-single-grid-row',async page=>{
  await page.waitForFunction(()=>typeof response!=='undefined'&&response?.ok&&!pending);
  assert.equal(await page.locator('#chart-axis-choice').evaluate(e=>getComputedStyle(e.parentElement).display),'inline-grid');
  await choose(page,'chart-axis','log');assert.equal(await page.locator('#chart-axis').inputValue(),'log');
 },'/forces.html');
 await test('data-page-inherits-the-selected-interface-scale',async page=>{
  await page.evaluate(()=>localStorage.setItem('cosmos2-ui-scale','1.5'));await page.reload();
  assert.equal(await page.evaluate(()=>Number(getComputedStyle(document.body).zoom)),1.5);
  await choose(page,'reference-body','606');assert.equal(await page.locator('#reference-body').inputValue(),'606');
  await page.evaluate(()=>localStorage.removeItem('cosmos2-ui-scale'));
 },'/content.html');
 proof.completed=true;proof.accepted=proof.checks.every(row=>row.passed);
}
main().catch(error=>proof.failure=error.stack).finally(async()=>{
 if(context)await context.close();if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));
 fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');console.log(JSON.stringify({accepted:proof.accepted,completed:proof.completed,passed:proof.checks.filter(row=>row.passed).length,failed:proof.checks.filter(row=>!row.passed),failure:proof.failure}));process.exitCode=proof.accepted?0:1;
});
