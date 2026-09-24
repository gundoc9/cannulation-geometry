/* Record the app's own canvas calls (with styles, transforms, shadows, dashes) for chosen
   card states, so qa/raster.py can replay them with the real faces. Usage:
   node qa/canvas.js built.html jobs.json out.json   (jobs: [{id,state,W,H,small}]) */
const fs=require('fs');
const [,,src,jobsPath,outPath]=process.argv;
const html=fs.readFileSync(src,'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
function Rec(log,W,H){
  let cur={x:0,y:0,r:0}; const stk=[]; let path=[]; let dash=[];
  const map=(x,y)=>{const c=Math.cos(cur.r),s=Math.sin(cur.r);return [cur.x+x*c-y*s,cur.y+x*s+y*c];};
  const sh=()=>S.shadowBlur>0?{b:S.shadowBlur,c:S.shadowColor}:null;
  const S={
    canvas:{width:W,height:H},
    setTransform(a,b,c,d,e,f){cur={x:e||0,y:f||0,r:0};},
    save(){stk.push({cur:{...cur},ga:S.globalAlpha,dash:dash.slice(),font:S.font,fs:S.fillStyle,ss:S.strokeStyle,lw:S.lineWidth,sb:S.shadowBlur,sc:S.shadowColor,ta:S.textAlign,lc:S.lineCap});},
    restore(){const p=stk.pop(); if(p){cur=p.cur;S.globalAlpha=p.ga;dash=p.dash;S.font=p.font;S.fillStyle=p.fs;S.strokeStyle=p.ss;S.lineWidth=p.lw;S.shadowBlur=p.sb;S.shadowColor=p.sc;S.textAlign=p.ta;S.lineCap=p.lc;}},
    setLineDash(a){dash=(a||[]).slice();}, getLineDash(){return dash.slice();},
    beginPath(){path=[];},closePath(){path.push({k:'z'});},clearRect(){},clip(){},
    moveTo(x,y){const[a,b]=map(x,y);path.push({k:'m',x:a,y:b});},
    lineTo(x,y){const[a,b]=map(x,y);path.push({k:'l',x:a,y:b});},
    quadraticCurveTo(cx,cy,x,y){const[a,b]=map(x,y);path.push({k:'l',x:a,y:b});},
    bezierCurveTo(c1,c2,c3,c4,x,y){const[a,b]=map(x,y);path.push({k:'l',x:a,y:b});},
    arc(x,y,r,a0,a1,ccw){if(!(r>=0)||!Number.isFinite(r))throw new Error('IndexSizeError');const[a,b]=map(x,y);path.push({k:'a',x:a,y:b,r,a0:a0??0,a1:a1??7,ccw:!!ccw,rot:cur.r});},
    ellipse(x,y,rx,ry,ro,a0,a1){if(!(rx>=0)||!(ry>=0))throw new Error('IndexSizeError');const[a,b]=map(x,y);path.push({k:'e',x:a,y:b,rx,ry,ro:(ro??0)+cur.r});},
    rect(x,y,w,h){const[a,b]=map(x,y);path.push({k:'rr',x:a,y:b,w,h,rad:0,rot:cur.r});},
    roundRect(x,y,w,h,rad){const[a,b]=map(x,y);path.push({k:'rr',x:a,y:b,w,h,rad:Array.isArray(rad)?rad[0]:(rad||0),rot:cur.r});},
    fillRect(x,y,w,h){const[a,b]=map(x,y);log.push({op:'fr',x:a,y:b,w,h,fs:S.fillStyle,ga:S.globalAlpha});},
    strokeRect(x,y,w,h){const[a,b]=map(x,y);log.push({op:'sr',x:a,y:b,w,h,ss:S.strokeStyle,lw:S.lineWidth,ga:S.globalAlpha});},
    stroke(){log.push({op:'st',p:path.slice(),ss:S.strokeStyle,lw:S.lineWidth,ga:S.globalAlpha,cap:S.lineCap,dash:dash.slice(),sh:sh()});},
    fill(){log.push({op:'fi',p:path.slice(),fs:S.fillStyle,ga:S.globalAlpha,sh:sh()});},
    strokeText(t,x,y){const[a,b]=map(x,y);log.push({op:'tx',stroke:true,t:String(t),x:a,y:b,f:S.font,al:S.textAlign,bl:S.textBaseline,fs:S.strokeStyle,sw:S.lineWidth,ga:S.globalAlpha});},
    fillText(t,x,y){const[a,b]=map(x,y);log.push({op:'tx',t:String(t),x:a,y:b,f:S.font,al:S.textAlign,bl:S.textBaseline,fs:S.fillStyle,ga:S.globalAlpha});},
    measureText(t){const m=/(\d+(?:\.\d+)?)px/.exec(S.font||'');const px=m?+m[1]:10;const fam=/'(\w+)'/.exec(S.font||'');
      const k=fam&&fam[1]==='BS'?0.47:fam&&fam[1]==='GM'?0.62:0.52; return {width:String(t).length*px*k};},
    createLinearGradient(){return{addColorStop(){}}},
    createImageData(w,h){return{data:new Uint8ClampedArray(w*h*4),width:w,height:h};},
    putImageData(){},drawImage(){log.push({op:'field'});},
    translate(dx,dy){const c=Math.cos(cur.r),s=Math.sin(cur.r);cur.x+=dx*c-dy*s;cur.y+=dx*s+dy*c;},
    rotate(a){cur.r+=a;}, scale(){},
    strokeStyle:'',fillStyle:'',lineWidth:1,font:'',textAlign:'left',textBaseline:'alphabetic',
    lineCap:'butt',lineJoin:'miter',shadowColor:'',shadowBlur:0,shadowOffsetY:0,globalAlpha:1,
  };
  return S;
}
global.window={matchMedia:()=>({matches:false}),addEventListener(){},devicePixelRatio:2,scrollTo(){},innerWidth:390,innerHeight:844};
global.requestAnimationFrame=f=>0; global.cancelAnimationFrame=()=>{};
global.performance={now:()=>0}; global.getComputedStyle=()=>({maxWidth:'620px',getPropertyValue:()=>''});
global.history={replaceState(){}}; global.location={hash:'',pathname:'/',search:''};
const mkEl=()=>({appendChild(){},setAttribute(){},getAttribute:()=>'',addEventListener(){},style:{},children:[],
  textContent:'',className:'',innerHTML:'',width:0,height:0,parentNode:null,
  getBoundingClientRect:()=>({width:390,height:470,left:0,top:0}),getContext:()=>Rec([],390,470),setPointerCapture(){}});
global.document={getElementById:()=>mkEl(),createElement:()=>mkEl(),body:{},documentElement:{},fonts:null};
global.CanvasRenderingContext2D=function(){}; CanvasRenderingContext2D.prototype={};
const body=js.replace(/if\(document\.fonts&&document\.fonts\.ready\) document\.fonts\.ready\.then\(\w+\); else \w+\(\);\s*$/,'');
eval(body+';globalThis.__X={CARDS,PICS,KH};');
const {CARDS,PICS,KH}=globalThis.__X;
const jobs=JSON.parse(fs.readFileSync(jobsPath,'utf8')); const out=[];
for(const j of jobs){
  const c=CARDS.find(x=>x.id===j.id); const H=j.H||(c.kh||KH[c.pic]); const W=j.W||358;
  const st=Object.assign({},j.state||{}); const log=[];
  let label=''; try{ label=PICS[c.pic](Rec(log,W,H),W,H,c,st,!!j.small)||''; }catch(e){ label='THREW: '+e.message; }
  out.push({id:j.id,name:j.name||j.id,W,H,log,label});
}
fs.writeFileSync(outPath,JSON.stringify(out)); console.log('recorded',out.length,'states');
