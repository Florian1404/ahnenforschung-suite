import {graph,persons,dateLabel,edgeLabel,table} from '../common.mjs?v=1.5.0';

// Each occurrence owns its path. Shared ancestors remain visible in every branch.
export function lineage(a,root,direction='ancestors',depth=4,opts={}){
  const people=persons(a),g=graph(a,opts),nodes=[],limit=opts.limit||1500;
  let truncated=false;
  const maxDepth=Math.max(0,Math.min(12,Math.floor(Number(depth)||0)));
  function visit(id,key,generation,via,path,uncertain,start,end){
    if(nodes.length>=limit){truncated=true;return null;}
    const cycle=!!id&&path.has(id);
    const node={id,key,generation,via,uncertain,cycle,start,end,children:[]};nodes.push(node);
    if(generation>=maxDepth||cycle)return node;
    const links=id?(g.get(id)||[]).filter(e=>e.dir===(direction==='ancestors'?'parent':'child')).sort((a,b)=>String(people.get(a.to)?.anzeigename).localeCompare(String(people.get(b.to)?.anzeigename),'de')||a.to.localeCompare(b.to)):[];
    // Missing slots are visual placeholders, never new people or relationships.
    const count=direction==='ancestors'&&opts.placeholders?Math.max(2,links.length):links.length;
    const nextPath=new Set(path);if(id)nextPath.add(id);
    for(let i=0;i<count;i++){
      if(nodes.length>=limit){truncated=true;break;}
      const e=links[i],span=(end-start)/count;
      const child=visit(e?.to||null,key+'.'+(i+1),generation+1,e||null,nextPath,uncertain||(e?!e.confirmed:false),start+i*span,start+(i+1)*span);
      if(child)node.children.push(child);
    }
    return node;
  }
  if(!people.has(root))return {root:null,nodes:[],truncated:false};
  const tree=visit(root,'1',0,null,new Set(),false,Math.PI,2*Math.PI);
  const counts=new Map();for(const n of nodes)if(n.id)counts.set(n.id,(counts.get(n.id)||0)+1);
  for(const n of nodes)n.repeat=!!n.id&&(counts.get(n.id)||0)>1;
  return {root:tree,nodes,truncated};
}
const round=v=>Number(v.toFixed(3));
function point(cx,cy,r,angle){return [round(cx+r*Math.cos(angle)),round(cy+r*Math.sin(angle))];}
export function sector(cx,cy,inner,outer,start,end){
  const a=point(cx,cy,outer,start),b=point(cx,cy,outer,end),large=end-start>Math.PI?1:0;
  if(inner===0)return `M ${cx} ${cy} L ${a.join(' ')} A ${outer} ${outer} 0 ${large} 1 ${b.join(' ')} Z`;
  const c=point(cx,cy,inner,end),d=point(cx,cy,inner,start);
  return `M ${a.join(' ')} A ${outer} ${outer} 0 ${large} 1 ${b.join(' ')} L ${c.join(' ')} A ${inner} ${inner} 0 ${large} 0 ${d.join(' ')} Z`;
}
const palette=['#f4e1ac','#d9e8f3','#eadfcf','#d5e6df','#e5dff1','#f1ddd8','#e8e8d6'];
const short=(v,n)=>Array.from(String(v||'')).length>n?Array.from(String(v||'')).slice(0,Math.max(1,n-1)).join('')+'…':String(v||'');
function life(p){return '* '+dateLabel(p?.geburt?.datum)+' · † '+dateLabel(p?.tod?.datum);}
function tooltip(n,people){
  if(!n.id)return 'Nicht erfasste Elternposition · '+n.key;
  const p=people.get(n.id);
  return n.key+' · '+p.anzeigename+(p.namen?.geburtsname?'\ngeb. '+p.namen.geburtsname:'')+'\n'+life(p)+(n.via?'\n'+edgeLabel(n.via):'')+(n.uncertain?'\nWeg enthält ungeklärte Verbindungen':'')+(n.repeat?'\nMehrfach im dargestellten Baum':'')+(n.cycle?'\nAbstammungskreis: Zweig hier gestoppt':'');
}
function interaction(n,people,esc){
  return n.id?`data-chart-person="${esc(n.id)}" tabindex="0" role="button" aria-label="${esc(tooltip(n,people))}"`:'';
}
function svgOpen(w,h,title,esc,type){
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="group" aria-label="${esc(title)}" data-chart-type="${type}" font-family="Arial, sans-serif"><title>${esc(title)}</title><rect width="${w}" height="${h}" fill="#fffdf8"/>`;
}
export function fanSvg(a,root,depth=4,opts={},esc=String,fullCircle=false){
  depth=Math.max(1,Math.min(6,Math.floor(Number(depth)||4)));
  const model=lineage(a,root,'ancestors',depth,{...opts,placeholders:true}),people=persons(a);
  if(!model.root)return {svg:'',model};
  const ring=96,radius=(depth+1)*ring,margin=35,w=radius*2+margin*2,h=fullCircle?radius*2+margin*2:radius+margin+100,cx=w/2,cy=fullCircle?h/2:radius+margin;
  const title=(fullCircle?'Kreisdiagramm':'Fächerdiagramm')+' · '+people.get(root).anzeigename;
  let svg=svgOpen(w,h,title,esc,fullCircle?'circle':'fan');
  for(const n of model.nodes){
    const start=fullCircle?(n.start-Math.PI)*2-Math.PI/2:n.start,end=fullCircle?(n.end-Math.PI)*2-Math.PI/2:n.end;
    const inner=n.generation*ring,outer=inner+ring-3,mid=(start+end)/2,r=(inner+outer)/2;
    const p=people.get(n.id),label=p?.anzeigename||'Unbekannt',fill=n.id?palette[n.generation%palette.length]:'#f1f0eb';
    const stroke=n.cycle?'#713f31':n.uncertain?'#5b4d3a':'#a39b8c',dash=n.uncertain||!n.id?' stroke-dasharray="5 3"':'';
    svg+=`<g ${interaction(n,people,esc)}><title>${esc(tooltip(n,people))}</title>`;
    // The centre is a full disc in the circle layout; split its arc into two semicircles.
    if(fullCircle&&n.generation===0)svg+=`<circle cx="${cx}" cy="${cy}" r="${outer}" fill="${fill}" stroke="${stroke}" stroke-width="1.4"/>`;
    else svg+=`<path d="${sector(cx,cy,inner,outer,start,end)}" fill="${fill}" stroke="${stroke}" stroke-width="${n.uncertain?2:1}"${dash}/>`;
    const [x,y]=point(cx,cy,r,mid),angularSpace=r*(end-start),font=n.generation===0?13:Math.min(13,Math.max(8,angularSpace/2.7));
    let angle=round(mid*180/Math.PI);if(angle>90&&angle<270)angle+=180;
    // Centre label horizontal; other labels run radially inside their own ring.
    const tx=n.generation===0?cx:x,ty=n.generation===0?(fullCircle?cy:cy-35):y;
    const rotate=n.generation===0?0:angle,maxChars=Math.floor((ring-14)/(font*.56));
    const surname=typeof p?.namen?.familienname==='string'?p.namen.familienname:'';
    const split=n.generation>0&&angularSpace>=38&&surname&&label.endsWith(surname)&&label!==surname;
    svg+=`<text transform="translate(${tx} ${ty}) rotate(${rotate})" text-anchor="middle" fill="#252820" font-size="${font}"><tspan x="0" dy="${split?-14:-7}">${esc(short(split?label.slice(0,-surname.length).trim():label,n.generation===0?24:maxChars))}</tspan>`;
    if(split)svg+=`<tspan x="0" dy="14">${esc(short(surname,maxChars))}</tspan>`;
    if(angularSpace>=18||n.generation===0)svg+=`<tspan x="0" dy="14" font-size="${Math.max(7,font-2)}">${esc(n.id?(n.cycle?'Kreis! ':n.repeat?'↺ ':'')+(p.geburt?.datum?.iso||'?').slice(0,4)+'–'+(p.tod?.datum?.iso||'?').slice(0,4):'—')}</tspan>`;
    svg+='</text></g>';
  }
  if(!fullCircle)svg+=`<text x="${cx}" y="${cy+35}" text-anchor="middle" font-size="17" fill="#252820">${esc(people.get(root).anzeigename)}</text><text x="${cx}" y="${cy+59}" text-anchor="middle" font-size="12" fill="#514b41">${depth} Vorfahrengenerationen · gestrichelt: ungeklärt / nicht erfasst · ↺: mehrfach</text>`;
  svg+='</svg>';
  return {svg,model,width:w,height:h};
}
function positionTree(tree,widthStep){
  function size(n){n.span=n.children.length?n.children.reduce((sum,c)=>sum+size(c),0):1;return n.span;}
  size(tree);
  function place(n,left){n.x=(left+n.span/2)*widthStep;let x=left;for(const c of n.children){place(c,x);x+=c.span;}}
  place(tree,0);return tree.x;
}
export function hourglassSvg(a,root,depth=3,opts={},esc=String){
  depth=Math.max(1,Math.min(6,Math.floor(Number(depth)||3)));
  const above=lineage(a,root,'ancestors',depth,{...opts,limit:600}),below=lineage(a,root,'descendants',depth,{...opts,limit:600}),people=persons(a);
  if(!above.root)return {svg:'',above,below};
  const stepX=202,stepY=132,cardW=180,cardH=92,margin=35;
  const ax=positionTree(above.root,stepX),bx=positionTree(below.root,stepX),half=Math.max(ax,bx),w=Math.max(650,half*2+margin*2);
  const up=Math.max(...above.nodes.map(n=>n.generation)),down=Math.max(...below.nodes.map(n=>n.generation)),h=(up+down)*stepY+cardH+margin*2,centreX=w/2,centreY=margin+up*stepY+cardH/2;
  for(const [model,offset,sign] of [[above,ax,-1],[below,bx,1]])for(const n of model.nodes){n.x=round(n.x-offset+centreX);n.y=centreY+sign*n.generation*stepY;}
  const title='Sanduhr · '+people.get(root).anzeigename;
  let svg=svgOpen(w,h,title,esc,'hourglass');
  for(const [model,sign] of [[above,-1],[below,1]])for(const n of model.nodes)for(const c of n.children){
    const fromY=n.y+sign*cardH/2,toY=c.y-sign*cardH/2,middle=(fromY+toY)/2;
    svg+=`<path d="M ${n.x} ${fromY} V ${middle} H ${c.x} V ${toY}" fill="none" stroke="#536878" stroke-width="1.8"${c.uncertain?' stroke-dasharray="6 4"':''}/>`;
  }
  const seenRoot=new Set();
  for(const model of [above,below])for(const n of model.nodes){
    if(n.generation===0){if(seenRoot.has(root))continue;seenRoot.add(root);}
    const p=people.get(n.id),x=n.x-cardW/2,y=n.y-cardH/2,fill=n.generation===0?'#f4e1ac':palette[n.generation%palette.length];
    svg+=`<g ${interaction(n,people,esc)}><title>${esc(tooltip(n,people))}</title><rect x="${x}" y="${y}" width="${cardW}" height="${cardH}" rx="9" fill="${fill}" stroke="#665e53" stroke-width="${n.uncertain?2:1}"${n.uncertain?' stroke-dasharray="6 4"':''}/>`;
    svg+=`<text x="${n.x}" y="${y+22}" text-anchor="middle" fill="#252820" font-size="12" font-weight="bold">${esc(short((n.repeat?'↺ ':'')+p.anzeigename,24))}</text>`;
    const lines=[p.namen?.geburtsname?'geb. '+p.namen.geburtsname:'', '* '+dateLabel(p.geburt?.datum)+' · † '+dateLabel(p.tod?.datum),n.cycle?'Abstammungskreis – gestoppt':n.uncertain?'Weg enthält ungeklärte Verbindung':n.via?edgeLabel(n.via):'Ausgangspunkt'];
    lines.forEach((text,i)=>{svg+=`<text x="${n.x}" y="${y+40+i*17}" text-anchor="middle" font-size="10" fill="#45463e">${esc(short(text,30))}</text>`;});
    svg+='</g>';
  }
  return {svg:svg+'</svg>',above,below,width:w,height:h};
}
export function ahnentafelHtml(a,root,depth,opts,ctx){
  const model=lineage(a,root,'ancestors',Math.min(8,depth),{...opts,limit:1500}),people=persons(a),esc=ctx.esc;
  return {model,html:table(['Pfadnummer','Generation','Person','Lebensdaten / Ort','Verbindung / Hinweise'],model.nodes.map(n=>{
    const p=people.get(n.id);
    return [esc(n.key),String(n.generation),ctx.personButton(n.id)+(p.namen?.geburtsname?'<br>geb. '+esc(p.namen.geburtsname):''),esc(life(p))+'<br>'+esc(p.geburt?.ort_original||'—'),esc(n.via?edgeLabel(n.via):'Ausgangspunkt')+(n.repeat?'<br>↺ Mehrfach im dargestellten Baum':'')+(n.cycle?'<br>Abstammungskreis – hier gestoppt':'')+(n.uncertain?'<br>Weg enthält ungeklärte Verbindung':'')];
  }))};
}
