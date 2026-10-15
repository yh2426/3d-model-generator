'use strict';
const $ = id => document.getElementById(id);
const factors = {mm:1,cm:10,inch:25.4};
const names = {rectangular_bar:'Rectangular bar'};
let models = [], currentUnit = 'mm', triangles = [], yaw = -0.6, pitch = -0.45, zoom = 1;
let radius = 1, center = [0,0,0], photoURL, drag;
const canvas = $('canvas'), ctx = canvas.getContext('2d');
function status(message, error=false) { $('status').textContent=message; $('status').className=error?'error':''; }
function fillDimensions() {
  const model = models[Number($('model').value)];
  for (const key of ['width','depth','height']) $(key).value=+(model.dimensions[key]/factors[currentUnit]).toFixed(6);
}
function clearResult() {
  triangles=[]; draw();
  $('overlay').hidden=false; $('overlay').textContent='Choose a model and click Generate to preview it';
  $('actual').textContent='No model generated yet'; $('resultName').textContent='Model preview';
  $('resultInfo').textContent='Actual dimensions and downloads will appear here.';
  for (const ext of ['stl','glb']) { $(ext).removeAttribute('href'); $(ext).setAttribute('aria-disabled','true'); }
}
$('model').addEventListener('change',()=>{fillDimensions();clearResult();status('Model changed. Generate a new preview.');});
$('unit').addEventListener('change',()=>{
  const next=$('unit').value;
  for (const key of ['width','depth','height']) {
    const input=$(key);
    if(input.value!=='' && Number.isFinite(input.valueAsNumber)) input.value=+(input.valueAsNumber*factors[currentUnit]/factors[next]).toFixed(6);
  }
  currentUnit=next;
});
for(const key of ['width','depth','height']) $(key).addEventListener('input',()=>status('Parameters edited. Mock results still use the original sample dimensions.'));
$('photo').addEventListener('change',()=>{
  if(photoURL) URL.revokeObjectURL(photoURL);
  $('photoPreview').style.display='none';
  const file=$('photo').files[0];
  if(!file) return;
  if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>10*1024*1024) {
    $('photo').value=''; status('Choose a PNG, JPEG, or WebP image up to 10 MB.',true);return;
  }
  photoURL=URL.createObjectURL(file);
  $('photoPreview').src=photoURL;
  $('photoPreview').onload=()=>{$('photoPreview').style.display='block';status('Photo previewed locally. It is not uploaded or used to generate the model.');};
  $('photoPreview').onerror=()=>{status('Cannot read this image. Please choose another photo.',true);$('photo').value='';};
});
function parseSTL(buffer) {
  if(buffer.byteLength<84) throw Error('Incomplete STL file');
  const view=new DataView(buffer), count=view.getUint32(80,true);
  if(count===0||buffer.byteLength!==84+count*50) throw Error('Invalid STL format');
  return Array.from({length:count},(_,i)=>Array.from({length:3},(_,j)=>Array.from({length:3},(_,k)=>{
    const v=view.getFloat32(84+i*50+12+j*12+k*4,true);
    if(!Number.isFinite(v)) throw Error('Invalid STL coordinates');
    return v;
  })));
}
$('form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(!$('form').reportValidity()) return;
  const model=models[Number($('model').value)];
  const requested=Object.fromEntries(['width','depth','height'].map(k=>[k,$(k).valueAsNumber*factors[currentUnit]]));
  clearResult();
  for(const id of ['generate','model','unit','width','depth','height']) $(id).disabled=true;
  $('generate').textContent='Generating…';$('overlay').textContent='Loading sample model…';status('Generating mock result…');
  try {
    await new Promise(resolve=>setTimeout(resolve,650));
    const response=await fetch(`../models/${model.name}.stl`);
    if(!response.ok) throw Error(`Model loading failed (${response.status})`);
    triangles=parseSTL(await response.arrayBuffer());
    const points=triangles.flat(), min=[0,1,2].map(a=>Math.min(...points.map(p=>p[a])));
    const max=[0,1,2].map(a=>Math.max(...points.map(p=>p[a])));
    center=min.map((v,a)=>(v+max[a])/2);radius=Math.max(...max.map((v,a)=>v-min[a]));
    reset();$('overlay').hidden=true;$('resultName').textContent=names[model.name];
    $('actual').textContent=`Actual sample: ${max.map((v,a)=>+(v-min[a]).toFixed(3)).join(' × ')} mm`;
    $('resultInfo').textContent=`Your input: ${Object.values(requested).map(v=>+v.toFixed(3)).join(' × ')} mm · Preview and downloads use the original sample`;
    for(const ext of ['stl','glb']) {$(ext).href=`../models/${model.name}.${ext}`;$(ext).download=`${model.name}.${ext}`;$(ext).setAttribute('aria-disabled','false');}
    status('Mock result ready. Rotate, zoom, or download the original sample.');
  } catch(error) {clearResult();$('overlay').textContent='Model loading failed. Check the files and try again.';status(error.message,true);}
  finally {for(const id of ['generate','model','unit','width','depth','height']) $(id).disabled=false;$('generate').textContent='Generate preview →';}
});
function reset(){yaw=-0.6;pitch=-0.45;zoom=1;draw();}
function scaleZoom(factor){zoom=Math.max(0.4,Math.min(3,zoom*factor));draw();}
function draw(){
  const w=canvas.clientWidth,h=canvas.clientHeight,dpr=window.devicePixelRatio||1;
  canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  if(!triangles.length)return;
  const transform=p=>{
    const x=p[0]-center[0],z=p[1]-center[1],y=p[2]-center[2];
    const rx=x*Math.cos(yaw)-z*Math.sin(yaw),rz=x*Math.sin(yaw)+z*Math.cos(yaw);
    return [rx,y*Math.cos(pitch)-rz*Math.sin(pitch),y*Math.sin(pitch)+rz*Math.cos(pitch)];
  };
  const project=p=>{const s=Math.min(w,h)*0.69*zoom/radius*4/(4+p[2]/radius);return [w/2+p[0]*s,h/2-p[1]*s];};
  ctx.strokeStyle='#d6dfd2';ctx.lineWidth=1;
  for(let i=-4;i<=4;i++) {ctx.beginPath();ctx.moveTo(w/2+i*48,0);ctx.lineTo(w/2+i*48,h);ctx.stroke();ctx.beginPath();ctx.moveTo(0,h/2+i*48);ctx.lineTo(w,h/2+i*48);ctx.stroke();}
  const faces=triangles.map(t=>t.map(transform)).sort((a,b)=>b.reduce((s,p)=>s+p[2],0)-a.reduce((s,p)=>s+p[2],0));
  for(const face of faces){
    const a=face[1].map((v,i)=>v-face[0][i]),b=face[2].map((v,i)=>v-face[0][i]);
    const n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
    const light=Math.abs((n[0]*-.4+n[1]*.7+n[2]*-.6)/Math.hypot(...n));
    const pts=face.map(project);ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();
    ctx.fillStyle=`hsl(164,35%,${38+light*22}%)`;ctx.fill();ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=.5;ctx.stroke();
  }
}
canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.01;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-drag[1])*.01));drag=[e.clientX,e.clientY];draw();});
for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,()=>{drag=null;});
canvas.addEventListener('wheel',e=>{e.preventDefault();scaleZoom(Math.exp(-e.deltaY*.001));},{passive:false});
canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')yaw-=.1;if(e.key==='ArrowRight')yaw+=.1;if(e.key==='ArrowUp')pitch=Math.max(-1.4,pitch-.1);if(e.key==='ArrowDown')pitch=Math.min(1.4,pitch+.1);if(['+','='].includes(e.key))scaleZoom(1.15);if(e.key==='-')scaleZoom(1/1.15);draw();});
$('zoomIn').onclick=()=>scaleZoom(1.2);$('zoomOut').onclick=()=>scaleZoom(1/1.2);$('reset').onclick=reset;
new ResizeObserver(draw).observe(canvas);
(async()=>{try{const response=await fetch('../samples.json');if(!response.ok)throw Error('Cannot read configuration');const config=await response.json();models=config.models;for(const [i,model]of models.entries())$('model').add(new Option(names[model.name],i));fillDimensions();$('model').disabled=false;$('generate').disabled=false;status('Ready. Choose a sample and generate a preview.');}catch(error){status('Initialization failed. Check the bundled assets, or follow the README server instructions.',true);}})();

