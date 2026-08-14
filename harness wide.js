/* Recording-context harness for the v2 build. Bounds, distinctness, labels,
   mark arithmetic, drag mapping, thumbnails. */
const fs=require('fs');
const src=fs.readFileSync(fs.readFileSync('.latest','utf8').trim(),'utf8');
const js=src.match(/<script>([\s\S]*?)<\/script>/)[1];
let calls=[]; const W=588,H=470;
function Rec(){
  let cur={x:0,y:0,r:0}; const stk=[];
  const map=(x,y)=>{ const c=Math.cos(cur.r),s=Math.sin(cur.r);
    return [cur.x+x*c-y*s, cur.y+x*s+y*c]; };
  const t=(x,y)=>{ if(Number.isFinite(x)&&Number.isFinite(y)){ const[mx,my]=map(x,y);
    calls.push({op:'pt',x:mx,y:my}); } };
  const s={
    canvas:{width:W,height:H},
    setTransform(){cur={x:0,y:0,r:0};},save(){stk.push({...cur});},restore(){if(stk.length)cur=stk.pop();},beginPath(){},closePath(){},clearRect(){},
    moveTo(x,y){t(x,y);},lineTo(x,y){t(x,y);},
    arc(x,y,r){ if(!(r>=0)||!Number.isFinite(r)) throw new Error('IndexSizeError: The index is not in the allowed range.');
      const[mx,my]=map(x,y); calls.push({op:'arc',x:mx,y:my,r});},
    arcTo(){},ellipse(x,y,rx,ry){ if(!(rx>=0)||!(ry>=0)) throw new Error('IndexSizeError: The index is not in the allowed range.');
      calls.push({op:'ell',x,y,rx,ry});},
    rect(x,y,w,h){calls.push({op:'rect',x,y,w,h});},
    roundRect(x,y,w,hh){ for(const[px,py] of [[x,y],[x+w,y],[x,y+hh],[x+w,y+hh]]) t(px,py); calls.push({op:'rect'});},
    fillRect(x,y,w,h){calls.push({op:'rect',x,y,w,h});},
    strokeRect(x,y,w,h){calls.push({op:'rect',x,y,w,h});},
    stroke(){},fill(){},
    fillText(txt,x,y){calls.push({op:'text',t:String(txt),x,y});},
    measureText(txt){return {width:String(txt).length*6.2};},
    createImageData(w,h){return{data:new Uint8ClampedArray(w*h*4),width:w,height:h};},
    putImageData(){},drawImage(){},
    translate(dx,dy){const c=Math.cos(cur.r),s=Math.sin(cur.r);cur.x+=dx*c-dy*s;cur.y+=dx*s+dy*c;},rotate(a){cur.r+=a;},
    strokeStyle:'',fillStyle:'',lineWidth:1,font:'',textAlign:'left',textBaseline:'alphabetic',
    lineCap:'butt',shadowColor:'',shadowBlur:0,shadowOffsetY:0,globalAlpha:1,
  };
  return s;
}
global.window={matchMedia:()=>({matches:true}),addEventListener(){},devicePixelRatio:2,scrollTo(){}};
global.requestAnimationFrame=f=>0; global.cancelAnimationFrame=()=>{};
global.performance={now:()=>0};
const mkEl=()=>({appendChild(){},setAttribute(){},getAttribute:()=>'',addEventListener(){},
  textContent:'',className:'',innerHTML:'',style:{},children:[],width:0,height:0,
  getBoundingClientRect:()=>({width:W,height:H,left:0,top:0}),getContext:()=>Rec(),
  setPointerCapture(){}});
global.document={getElementById:()=>mkEl(),createElement:()=>mkEl(),body:{},
  fonts:{ready:{then:f=>{}}}};
global.CanvasRenderingContext2D=function(){}; CanvasRenderingContext2D.prototype={};
eval(js+';globalThis.__X={CARDS,PICS,G,state,KH};');
const {CARDS,PICS,G,state,KH}=globalThis.__X;
let fails=[]; const g=(n,ok,d)=>{console.log(`  [${ok?'ok  ':'FAIL'}] ${n}${d?'  '+d:''}`); if(!ok)fails.push(n);};
const stFor=c=>{const st={}; (c.ctrl||[]).forEach(k=>{ if(k.key==="len") st.len=0; else st[k.key]=k.opts[0][0];}); return st;};
const run=(c,st)=>{calls=[]; const HH=KH[c.pic]||470; const label=PICS[c.pic](Rec(),W,HH,c,st,false)||''; return {calls:calls.slice(),label,HH};};

console.log('=== H1 bounds ===');
let off=[];
for(const c of CARDS){
  const ks=(c.ctrl&&c.ctrl[0])?c.ctrl[0].opts:[[0,'-']];
  ks.forEach((o,j)=>{
    const st=stFor(c);
    if(c.ctrl&&c.ctrl[0]){ if(c.ctrl[0].key==="len") st.len=j; else st[c.ctrl[0].key]=o[0]; }
    const rr=run(c,st);
    for(const k of rr.calls){
      if(k.op==='pt'&&(k.x<-2||k.x>W+2||k.y<-2||k.y>rr.HH+2)) off.push([c.id,o[1],'pt',k.x|0,k.y|0]);
      if(k.op==='text'&&(k.x<-2||k.x>W+40||k.y<-2||k.y>rr.HH+2)) off.push([c.id,o[1],k.t,k.x|0,k.y|0]);
    }
  });
}
g('nothing outside the window', off.length===0, off.length?JSON.stringify(off.slice(0,6)):'');

console.log('=== H2 no inert control ===');
let vac=[];
for(const c of CARDS) for(const k of (c.ctrl||[])){
  const sigs=k.opts.map((o,j)=>{const st=stFor(c);
    if(k.key==="len") st.len=j; else st[k.key]=o[0];
    return JSON.stringify(run(c,st).calls);});
  if(new Set(sigs).size!==sigs.length) vac.push(c.id+'/'+k.key);
}
g('every option changes the picture', vac.length===0, vac.join(','));

console.log('=== H3 required labels ===');
const need={"vein-depth":["PROBE","DEPTH FROM PROBE FACE"],"gauge-length":["24G","22G","LENGTH"],
 "entry-angle":["PATH \u00f7 DEPTH","SKIN","VEIN"],"intraluminal":["IN THE VEIN","TIP","SKIN"],
 "rule-65":["65%","MIN LENGTH \u00f7 DEPTH"],"reach":["MAX VEIN DEPTH SERVED","SKIN"],
 "shallowing":["OF THE 45\u00b0 REACH KEPT"],"judging-angle":["65%","IN THE VEIN"],
 "flattening":["SHAFT ANGLE"],"floor-275":["27.5","MIN LENGTH HERE"],
 "which-governs":["65%","27.5","THE BINDING MARK"],"cvr":["22G","MIN VEIN FOR A 22G"],
 "flow-dwell":["MAX FLOW","mL/min"],"limits":["65%","27.5"],
 "out-of-plane":["LONG AXIS","SHORT AXIS","WHERE THE PLANE IS"]};
let miss=[];
for(const c of CARDS){
  if(!need[c.id])continue;
  const parts=run(c,stFor(c)).calls.filter(z=>z.op==='text').map(z=>z.t);
  const txts=parts.join('|'), flat=parts.join('');   // letterspaced text arrives per character
  for(const w of need[c.id]) if(!(txts.includes(w)||flat.includes(w))) miss.push(c.id+' missing '+JSON.stringify(w));
}
g('labels present', miss.length===0, miss.slice(0,5).join(' ; '));

console.log('=== H4 marks vs arithmetic ===');
const sin=d=>Math.sin(d*Math.PI/180);
let wrong=[];
for(const id of ['rule-65','judging-angle','floor-275']){
  const c=CARDS.find(x=>x.id===id);
  for(const o of c.ctrl[0].opts){
    const L=32, lin=L-5/sin(o[0]);
    const lab=run(c,{angle:o[0]}).label;
    if(id!=='floor-275'){
      const said=lab.includes('rule met')||run(c,{angle:o[0]}).calls.some(z=>z.op==='text'&&z.t.includes('inside'));
      if(said!==(0.65*L<=lin)) wrong.push(`${id}@${o[0]}`);
    }
  }
}
const wg=CARDS.find(x=>x.id==='which-governs');
for(let j=0;j<4;j++){
  const L=[19,25,32,45][j], lin=L-5/sin(45);
  const t=run(wg,{len:j}).calls.filter(z=>z.op==='text').map(z=>z.t).join('|').replace(/\s+/g,' ');
  const beyond=27.5>L;
  if(beyond!==t.includes('beyond the hub')) wrong.push(`wg@${L} beyond`);
  if(!beyond && (27.5<=lin)!==t.includes('27.5 mm inside')) wrong.push(`wg@${L} abs`);
}
g('marks agree with the formula', wrong.length===0, wrong.join(','));

console.log('=== H5 thumbnails ===');
let th=[];
for(const c of CARDS){ calls=[];
  try{ PICS[c.pic](Rec(),92,56,c,state[c.id]||stFor(c),true);}
  catch(e){th.push(c.id+' THREW: '+e.message); continue;}
  if(calls.length<2) th.push(c.id+' only '+calls.length);
}
g('all 14 draw small', th.length===0, th.join(';'));

console.log('=== H6 drag mapping ===');
let dm=[];
const at=PICS.angleTri.drag; const stA={angle:45};
at(null,stA, 52+200*Math.cos(30*Math.PI/180), 48+200*Math.sin(30*Math.PI/180), W,H);
if(Math.abs(stA.angle-30)>0.6) dm.push('angleTri->'+stA.angle.toFixed(1));
const ar=PICS.arc.drag; const stR={angle:45};
ar(null,stR, 52+150*Math.cos(20*Math.PI/180), 46+150*Math.sin(20*Math.PI/180), W,H);
if(Math.abs(stR.angle-20)>0.6) dm.push('arc->'+stR.angle.toFixed(1));
const dp=PICS.depth.drag; const stD={press:0};
dp(null,stD,100,70,W,H); const p0=stD.press; dp(null,stD,100,70+H*0.34,W,H);
if(!(p0<=0.01&&stD.press>=0.99)) dm.push('depth->'+p0+','+stD.press);
const pn=PICS.planes.drag; const stP={plane:14};
pn(null,stP,40,100,W,H); const pLo=stP.plane; pn(null,stP,W-30,100,W,H);
if(!(pLo<8 && stP.plane>30)) dm.push('planes->'+pLo.toFixed(1)+','+stP.plane.toFixed(1));
g('pointer maps to the value', dm.length===0, dm.join(','));

console.log('=== H7 geometry clear of the readout band ===');
const RD=new Set(["DEPTH FROM PROBE FACE","PATH \u00f7 DEPTH","IN THE VEIN","MIN LENGTH \u00f7 DEPTH","MIN LENGTH HERE","THE BINDING MARK","MAX VEIN DEPTH SERVED","OF THE 45\u00b0 REACH KEPT","SHAFT ANGLE","LENGTH","WHERE THE PLANE IS","OVER THE SHAFT","OVER THE TIP","PAST THE TIP","MAX FLOW","MIN VEIN FOR A 22G","mm","%","\u00b0","mL/min"]);
const PILL=new Set(["DRAG THE PROBE","DRAG THE TIP","DRAG ALONG THE ARC","DRAG THE ANGLE","DRAG THE PLANE","SWITCH THE LENGTH","SWITCH THE LIMIT","PICK A CATHETER","STEP THROUGH"]);
let clr=[];
for(const [id,st0] of [["which-governs",{len:0}],["flattening",{stage:2}],["cvr",{thr:33}],["gauge-length",{len:3}],["reach",{len:3,angle:20}],["intraluminal",{len:0}],["out-of-plane",{plane:33}]]){
  const c=CARDS.find(x=>x.id===id); const st={...stFor(c),...st0};
  const r=run(c,st);
  for(const z of r.calls) if(z.op==='text'){
    const s=String(z.t);
    if(s.length<=1||RD.has(s)||PILL.has(s)) continue;
    if(/^\d+(\.\d+)?(\u00b0|\u00d7|%)?$/.test(s)) continue;
    if(z.y>r.HH-64) clr.push(id+':'+s.slice(0,18)+'@'+(z.y|0));
  }
}
g('geometry stays above the readout band', clr.length===0, clr.slice(0,5).join(' ; '));
console.log(fails.length?fails.length+' FAILED: '+fails.join(', '):'HARNESS CLEAN');
process.exit(fails.length?1:0);
