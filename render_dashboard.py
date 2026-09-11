#!/usr/bin/env python3
"""render_dashboard.py — purple_state.json -> standalone HTML dashboard (inline CSS/JS, embedded state).

Usage: python3 render_dashboard.py --state purple_state.json --out tenable-purple-team-dashboard.html [--lang en|pt]
"""
import argparse, json, html

TEMPLATE = r"""<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Purple Team Dashboard — __TITLE__</title>
<style>
:root{--bg:#44494B;--card:#363A3C;--card2:#2F3234;--border:#5A5F62;--text:#F2F2F2;--muted:#B5B9BC;--accent:#E7FF00;
--blue:#4EA5FF;--green:#71FFC6;--purple:#BB8FF2;--orange:#FF8837;--red:#FF4B4B;--gray:#6B7073}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,"Segoe UI",Roboto,system-ui,sans-serif}
a{color:var(--blue)}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
header{padding:20px 28px 0}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h1{margin:0;font-size:22px;letter-spacing:.2px}h1 span{color:var(--accent)}.sub{color:var(--muted);margin-top:4px;font-size:13px}
.toggle{display:flex;border:1px solid var(--border);border-radius:8px;overflow:hidden}.toggle button{background:transparent;border:0;color:var(--muted);padding:6px 12px;cursor:pointer;font-weight:600}
.toggle button.on{background:var(--accent);color:#1d1f20}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.6px}.kpi .v{font-size:30px;font-weight:700;margin-top:4px}
.kpi .v.acc{color:var(--accent)}.kpi .d{font-size:12px;color:var(--muted);margin-top:2px}.up{color:var(--red)}.down{color:var(--green)}
.mini{display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:10px;background:var(--card2)}.mini i{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--muted);margin-top:8px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
nav{display:flex;gap:4px;padding:0 28px;border-bottom:1px solid var(--border);flex-wrap:wrap}
nav button{background:transparent;border:0;border-bottom:3px solid transparent;color:var(--muted);padding:10px 14px;cursor:pointer;font-weight:600;font-size:14px}
nav button.on{color:var(--accent);border-bottom-color:var(--accent)}nav button .n{background:var(--card2);border-radius:10px;padding:1px 7px;font-size:11px;margin-left:6px;color:var(--text)}
nav button .n.warn{background:var(--orange);color:#1d1f20}
main{padding:20px 28px 40px}section{display:none}section.on{display:block}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px}
.card h3{margin:0 0 10px;font-size:15px}.row{display:grid;gap:16px}.row.c2{grid-template-columns:1fr 1fr}.row.c3{grid-template-columns:1fr 1fr 1fr}
@media(max-width:1100px){.row.c2,.row.c3{grid-template-columns:1fr}}
.tools{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
input,select{background:var(--card2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 8px;font-size:13px}
.btn{background:var(--card2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 10px;cursor:pointer;font-size:13px}
.btn.p{background:var(--accent);color:#1d1f20;border-color:var(--accent);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 9px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px;cursor:pointer;user-select:none;white-space:nowrap}
th.sorted::after{content:" ▾";color:var(--accent)}th.sorted.asc::after{content:" ▴"}tr.click{cursor:pointer}tr.click:hover{background:var(--card2)}
td.red{border-left:3px solid var(--red)}td.blue{border-left:3px solid var(--blue)}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;white-space:nowrap}
.b-open{background:var(--red);color:#1d1f20}.b-in_progress{background:var(--purple);color:#1d1f20}.b-remediated{background:var(--orange);color:#1d1f20}
.b-validated{background:var(--green);color:#1d1f20}.b-validated_failed{background:var(--red);color:#fff;outline:2px solid #fff}.b-accepted{background:var(--gray);color:#fff}
.chip{display:inline-block;background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:1px 6px;margin:1px 3px 1px 0;font-size:11.5px}
.chip.t{border-color:var(--blue)}.sev{font-weight:700}.sev-critical{color:var(--red)}.sev-high{color:var(--orange)}.sev-medium{color:var(--accent)}.sev-low{color:var(--blue)}.sev-info{color:var(--muted)}
.bar{position:relative;height:16px;background:var(--card2);border-radius:4px;overflow:hidden}.bar i{position:absolute;left:0;top:0;height:100%;background:var(--gray);opacity:.45}.bar b{position:absolute;left:0;top:0;height:100%;background:var(--accent)}
.rollup .r{display:grid;grid-template-columns:200px 1fr 90px;gap:10px;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)}.rollup .r:last-child{border:0}
.hm{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(150px,1fr);gap:8px;overflow-x:auto;padding-bottom:8px}
.hm .col h4{margin:0 0 6px;font-size:11.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);white-space:nowrap}
.cell{border-radius:6px;padding:6px 8px;margin-bottom:6px;font-size:12px;cursor:pointer;color:#1d1f20;border:1px solid transparent}
.cell .id{font-weight:700}.cell .nm{opacity:.85;font-size:11px;line-height:1.2}.cell .st{font-size:11px;margin-top:2px;opacity:.9}
.c-gap{background:var(--red)}.c-claimed{background:var(--orange)}.c-validated{background:var(--green)}.c-untested_coverage{background:var(--blue)}.c-accepted{background:var(--gray);color:#fff}.c-out_of_scope{background:var(--card2);color:var(--muted);border-color:var(--border)}
.cell:hover{outline:2px solid var(--accent)}.foot{color:var(--muted);font-size:12px;margin-top:10px}
.drawer{position:fixed;top:0;right:-560px;width:540px;max-width:95vw;height:100%;background:var(--card);border-left:1px solid var(--border);box-shadow:-10px 0 30px rgba(0,0,0,.4);transition:right .2s;overflow:auto;padding:20px;z-index:20}
.drawer.on{right:0}.drawer h3{margin-top:0}.drawer dl{display:grid;grid-template-columns:150px 1fr;gap:6px 10px;font-size:13px}.drawer dt{color:var(--muted)}
.ed{width:100%;min-width:110px;background:var(--card2);border:1px dashed var(--border);color:var(--text);border-radius:6px;padding:4px 6px;font-size:12.5px}
.ed.edited{border:1px solid var(--accent);box-shadow:0 0 0 1px var(--accent) inset}tr.edited td.blue{border-left-color:var(--accent)}
.banner.edits{background:var(--card2);color:var(--text);border:1px solid var(--border);border-left:4px solid var(--accent);font-weight:400;font-size:13px}
.close{float:right;background:transparent;border:0;color:var(--muted);font-size:20px;cursor:pointer}
.banner{background:var(--orange);color:#1d1f20;border-radius:8px;padding:10px 14px;font-weight:600;margin-bottom:14px}.ok{background:var(--green)}
.empty{color:var(--muted);padding:20px;text-align:center}.strip{display:flex;gap:24px;flex-wrap:wrap}.strip div b{font-size:22px;display:block}
.tip{position:fixed;background:#1d1f20;color:#fff;padding:8px 10px;border-radius:6px;font-size:12px;pointer-events:none;display:none;z-index:30;max-width:320px;border:1px solid var(--border)}
</style>
</head>
<body>
<header>
 <div class="top">
  <div><h1><span>Purple Team</span> Dashboard — <span id="h-eng"></span></h1><div class="sub" id="h-sub"></div></div>
  <div class="toggle"><button id="lang-pt" onclick="setLang('pt')">PT</button><button id="lang-en" onclick="setLang('en')">EN</button></div>
 </div>
 <div class="kpis" id="kpis"></div>
</header>
<nav id="nav"></nav>
<main>
 <section id="s-scorecard"></section>
 <section id="s-heatmap"></section>
 <section id="s-validation"></section>
 <section id="s-residual"></section>
 <section id="s-dq"></section>
 <section id="s-changes"></section>
</main>
<div class="drawer" id="drawer"></div>
<div class="tip" id="tip"></div>
<script id="purple-state" type="application/json">__STATE__</script>
<script>
const S = JSON.parse(document.getElementById('purple-state').textContent);
let LANG = '__LANG__';
const I = {
 en:{scorecard:'Scorecard',heatmap:'ATT&CK Heatmap',validation:'Validation',residual:'Residual Risk',dq:'Data Quality',changes:'Changes',
  residual_index:'Residual index',findings:'Findings by status',validation_rate:'Validation rate',techniques:'Techniques (Red)',coverage:'Coverage',dq_issues:'Data-quality issues',
  open:'Open',in_progress:'In progress',remediated:'Remediated (not validated)',validated:'Validated',validated_failed:'Retest failed',accepted:'Risk accepted',
  gap:'Gap — no mitigation / retest failed',claimed:'Claimed — not validated',validated_c:'Validated block',untested_coverage:'Blue control, Red untested',accepted_c:'Risk accepted',out_of_scope:'Not in scope',
  run:'Run',generated:'generated',sources:'Sources',vs:'vs. run',of_inherent:'of inherent',demonstrated:'demonstrated',
  finding:'Finding',title:'Title',technique:'Technique(s)',severity:'Severity',asset:'Asset',path:'Attack path',red_status:'Red status',blue_mit:'Blue mitigation(s)',status:'Effective status',res:'Residual',inh:'Inherent',
  search:'Search…',all_status:'All statuses',all_tactic:'All tactics',all_path:'All attack paths',export:'Export CSV',none:'no mapped mitigation',by_finding:'by finding',by_technique:'by technique',
  hm_foot:'Sub-techniques roll up into parent cells. A finding with several techniques counts in each of them, so technique totals can exceed the overall residual. Click a cell to filter the scorecard.',show_all:'Show full matrix',
  mitigation:'Mitigation',type:'Type',framework:'Framework',covers:'Findings covered',blue_status:'Blue status',retest:'Retest result',retest_date:'Retest date',owner:'Owner',not_retested:'not re-tested',retest_pass:'pass',retest_fail:'FAIL',ticket_no:'Ticket number',
  edit_hint:'Retest date, Owner, Ticket and Retest result are editable when Tenable has no value — edits are kept in this file and can be exported / imported.',import_edits:'Import edits (JSON/CSV)',export_json:'Export edits JSON',export_csv:'Export edits CSV',dl_html:'Download dashboard with edits',
  edits_pending:'manual edit(s) pending — re-run the skill with --overrides (or --prior this file) to rescore',edited:'edited',imported:'edits imported',clear_edit:'revert',
  v_claimed:'Claimed (closed, not re-tested)',v_validated:'Validated by Red',v_failed:'Retest failed',v_unproven:'Residual still counted on claimed fixes',v_queue:'Retest queue (what Red should re-test first)',
  top:'Top residual findings',by_tech:'By technique',by_tactic:'By tactic',by_path:'By attack path',weakest:'weakest link',acc_note:'Accepted risk (excluded from residual)',
  dq_ok:'All rows joined cleanly — no data-quality issues.',flag:'Flag',entity:'Entity',id:'ID',detail:'Detail',count:'Count',
  ch_none:'First run — nothing to compare against. This run becomes the baseline.',ch_w:'Scoring weights changed since the previous run — index values are not directly comparable.',
  ch_new:'New findings',ch_resolved:'Resolved (validated)',ch_regressed:'Regressed',ch_changed:'Status changed',ch_removed:'No longer reported',ch_tech:'Techniques that moved most',from:'from',to:'to',index_move:'Residual index',
  evidence:'Evidence',ticket:'Ticket',found:'Found',exploit:'Exploitability',exposed:'Internet exposed',acr:'ACR',status_hist:'Status history',flags:'Flags',extra:'Other columns'},
 pt:{scorecard:'Scorecard',heatmap:'Heatmap ATT&CK',validation:'Validação',residual:'Residual Risk',dq:'Qualidade dos dados',changes:'Mudanças',
  residual_index:'Residual index',findings:'Findings por status',validation_rate:'Taxa de validação',techniques:'Techniques (Red)',coverage:'Cobertura',dq_issues:'Problemas de qualidade',
  open:'Aberto',in_progress:'Em andamento',remediated:'Remediado (não validado)',validated:'Validado',validated_failed:'Reteste falhou',accepted:'Risco aceito',
  gap:'Gap — sem mitigação / reteste falhou',claimed:'Declarado — não validado',validated_c:'Bloqueio validado',untested_coverage:'Controle Blue, não testado pelo Red',accepted_c:'Risco aceito',out_of_scope:'Fora do escopo',
  run:'Run',generated:'gerado em',sources:'Fontes',vs:'vs. run',of_inherent:'do inherent',demonstrated:'demonstradas',
  finding:'Finding',title:'Título',technique:'Technique(s)',severity:'Severidade',asset:'Asset',path:'Attack path',red_status:'Status Red',blue_mit:'Mitigação(ões) Blue',status:'Status efetivo',res:'Residual',inh:'Inherent',
  search:'Buscar…',all_status:'Todos os status',all_tactic:'Todas as tactics',all_path:'Todos os attack paths',export:'Exportar CSV',none:'sem mitigação mapeada',by_finding:'por finding',by_technique:'por technique',
  hm_foot:'Sub-techniques agregam na célula da technique pai. Um finding com várias techniques conta em cada uma delas, então o total por technique pode exceder o residual geral. Clique em uma célula para filtrar o scorecard.',show_all:'Mostrar matriz completa',
  mitigation:'Mitigação',type:'Tipo',framework:'Framework',covers:'Findings cobertos',blue_status:'Status Blue',retest:'Resultado do reteste',retest_date:'Data do reteste',owner:'Owner',not_retested:'não retestado',retest_pass:'passou',retest_fail:'FALHOU',ticket_no:'Número do ticket',
  edit_hint:'Data do reteste, Owner, Ticket e Resultado do reteste são editáveis quando o Tenable não fornece o valor — as edições ficam neste arquivo e podem ser exportadas / importadas.',import_edits:'Importar edições (JSON/CSV)',export_json:'Exportar edições JSON',export_csv:'Exportar edições CSV',dl_html:'Baixar dashboard com edições',
  edits_pending:'edição(ões) manual(is) pendente(s) — rode a skill novamente com --overrides (ou --prior este arquivo) para repontuar',edited:'editado',imported:'edições importadas',clear_edit:'reverter',
  v_claimed:'Declarado (fechado, não retestado)',v_validated:'Validado pelo Red',v_failed:'Reteste falhou',v_unproven:'Residual ainda contado em fixes declarados',v_queue:'Fila de reteste (o que o Red deve retestar primeiro)',
  top:'Top findings por residual',by_tech:'Por technique',by_tactic:'Por tactic',by_path:'Por attack path',weakest:'elo mais fraco',acc_note:'Risco aceito (excluído do residual)',
  dq_ok:'Todas as linhas foram unidas sem problemas de qualidade.',flag:'Flag',entity:'Entidade',id:'ID',detail:'Detalhe',count:'Qtd',
  ch_none:'Primeira execução — nada para comparar. Esta execução vira a baseline.',ch_w:'Os pesos de scoring mudaram desde a execução anterior — os índices não são diretamente comparáveis.',
  ch_new:'Novos findings',ch_resolved:'Resolvidos (validados)',ch_regressed:'Regrediram',ch_changed:'Status alterado',ch_removed:'Não mais reportados',ch_tech:'Techniques que mais mudaram',from:'de',to:'para',index_move:'Residual index',
  evidence:'Evidência',ticket:'Ticket',found:'Encontrado em',exploit:'Exploitability',exposed:'Exposto à internet',acr:'ACR',status_hist:'Histórico de status',flags:'Flags',extra:'Outras colunas'}
};
const t = k => (I[LANG][k] ?? I.en[k] ?? k);
const ST = ['open','in_progress','remediated','validated','validated_failed','accepted'];
const STC = {open:'var(--red)',in_progress:'var(--purple)',remediated:'var(--orange)',validated:'var(--green)',validated_failed:'var(--red)',accepted:'var(--gray)'};
const TACTICS = ['Reconnaissance','Resource Development','Initial Access','Execution','Persistence','Privilege Escalation','Defense Evasion','Credential Access','Discovery','Lateral Movement','Collection','Command and Control','Exfiltration','Impact','Unknown'];
const F = Object.fromEntries(S.findings.map(f=>[f.finding_id,f])), M = Object.fromEntries(S.mitigations.map(m=>[m.mitigation_id,m]));
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const badge = s => `<span class="badge b-${s}">${esc(t(s))}</span>`;
const sev = s => `<span class="sev sev-${s}">${esc(s[0].toUpperCase()+s.slice(1))}</span>`;
const num = n => (n??0).toFixed(2);
let filter = {status:'',tactic:'',path:'',q:'',tech:''}, showAll=false, tab='scorecard';

function setLang(l){LANG=l;document.getElementById('lang-pt').classList.toggle('on',l==='pt');document.getElementById('lang-en').classList.toggle('on',l==='en');renderAll();}
function show(id){tab=id;document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.t===id));document.querySelectorAll('main section').forEach(s=>s.classList.toggle('on',s.id==='s-'+id));}
function renderAll(){header();nav();scorecard();heatmap();validation();residual();dq();changes();show(tab);}

function header(){
 const m=S.meta, s=S.summary, d=S.delta;
 document.getElementById('h-eng').textContent=m.engagement||'—';
 document.getElementById('h-sub').innerHTML=`${t('run')} ${m.run_number} · ${t('generated')} ${esc(m.generated_at)}${d?` · ${t('vs')} ${d.previous_run??'?'} (${esc(d.previous_generated_at??'')})`:''} · ${t('sources')}: Red = ${esc(m.sources.findings)} · Blue = ${esc(m.sources.mitigations)} · Status = ${esc(m.sources.status)}`;
 const idx=s.residual_index, di=d&&d.index_from!=null?idx-d.index_from:null;
 const tot=Object.values(s.status_counts).reduce((a,b)=>a+b,0)||1;
 const mini=ST.map(k=>`<i style="width:${100*s.status_counts[k]/tot}%;background:${STC[k]}" title="${t(k)}: ${s.status_counts[k]}"></i>`).join('');
 const cov=s.technique_coverage;
 document.getElementById('kpis').innerHTML=`
  <div class="kpi"><div class="l">${t('residual_index')}</div><div class="v acc">${idx}</div><div class="d">${num(s.residual)} / ${num(s.inherent)} ${t('of_inherent')}${di!=null?` <span class="${di>0?'up':'down'}">${di>0?'▲':'▼'} ${Math.abs(di).toFixed(1)}</span>`:''}</div></div>
  <div class="kpi"><div class="l">${t('findings')}</div><div class="v">${S.findings.length}</div><div class="mini">${mini}</div><div class="legend">${ST.map(k=>`<span><i style="background:${STC[k]}"></i>${s.status_counts[k]} ${esc(t(k))}</span>`).join('')}</div></div>
  <div class="kpi"><div class="l">${t('validation_rate')}</div><div class="v">${S.validation.validation_rate==null?'—':S.validation.validation_rate+'%'}</div><div class="d">${S.validation.validated} ${t('validated').toLowerCase()} / ${S.validation.claimed+S.validation.validated} ${t('remediated').toLowerCase().split(' ')[0]}+${t('validated').toLowerCase()} · ${S.validation.failed} ${t('validated_failed').toLowerCase()}</div></div>
  <div class="kpi"><div class="l">${t('techniques')}</div><div class="v">${s.techniques_demonstrated}</div><div class="d">${t('demonstrated')} · ${t('coverage')}: <span style="color:var(--red)">${cov.gap} gap</span> · <span style="color:var(--orange)">${cov.claimed} claimed</span> · <span style="color:var(--green)">${cov.validated} validated</span> · <span style="color:var(--blue)">${cov.untested_coverage} untested</span></div></div>
  <div class="kpi"><div class="l">${t('dq_issues')}</div><div class="v" style="color:${s.data_quality_issues?'var(--orange)':'var(--green)'}">${s.data_quality_issues}</div><div class="d">${Object.keys(S.data_quality).slice(0,3).map(esc).join(' · ')}</div></div>`;
}
function nav(){
 const tabs=[['scorecard',S.findings.length],['heatmap',null],['validation',S.validation.claimed+S.validation.validated+S.validation.failed],['residual',null],['dq',S.summary.data_quality_issues,true],['changes',S.delta?S.delta.new.length+S.delta.resolved.length+S.delta.regressed.length+S.delta.changed.length:null]];
 document.getElementById('nav').innerHTML=tabs.map(([k,n,w])=>`<button data-t="${k}" onclick="show('${k}')">${t(k)}${n!=null?`<span class="n ${w&&n?'warn':''}">${n}</span>`:''}</button>`).join('');
}
function csv(rows,name){const s=rows.map(r=>r.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(',')).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{type:'text/csv'}));a.download=name;a.click();}
function sortable(tableId){const tb=document.getElementById(tableId);if(!tb)return;tb.querySelectorAll('th').forEach((th,i)=>th.onclick=()=>{const asc=th.classList.contains('sorted')&&!th.classList.contains('asc');tb.querySelectorAll('th').forEach(x=>x.classList.remove('sorted','asc'));th.classList.add('sorted');if(asc)th.classList.add('asc');const rows=[...tb.tBodies[0].rows];rows.sort((a,b)=>{const x=a.cells[i].dataset.v??a.cells[i].textContent,y=b.cells[i].dataset.v??b.cells[i].textContent;const nx=parseFloat(x),ny=parseFloat(y);const c=(!isNaN(nx)&&!isNaN(ny))?nx-ny:x.localeCompare(y);return asc?c:-c;});rows.forEach(r=>tb.tBodies[0].appendChild(r));});}

function visible(){return S.findings.filter(f=>(!filter.status||f.effective_status===filter.status)&&(!filter.tactic||f.tactics.includes(filter.tactic))&&(!filter.path||f.attack_path===filter.path)&&(!filter.tech||f.techniques.some(x=>x===filter.tech||x.split('.')[0]===filter.tech))&&(!filter.q||JSON.stringify(f).toLowerCase().includes(filter.q.toLowerCase())));}
function scorecard(){
 const rows=visible();
 const paths=[...new Set(S.findings.map(f=>f.attack_path))].sort(), tactics=TACTICS.filter(x=>S.findings.some(f=>f.tactics.includes(x)));
 document.getElementById('s-scorecard').innerHTML=`<div class="card"><div class="tools">
  <input placeholder="${t('search')}" value="${esc(filter.q)}" oninput="filter.q=this.value;scorecard()">
  <select onchange="filter.status=this.value;scorecard()"><option value="">${t('all_status')}</option>${ST.map(k=>`<option value="${k}" ${filter.status===k?'selected':''}>${t(k)}</option>`).join('')}</select>
  <select onchange="filter.tactic=this.value;scorecard()"><option value="">${t('all_tactic')}</option>${tactics.map(k=>`<option ${filter.tactic===k?'selected':''}>${k}</option>`).join('')}</select>
  <select onchange="filter.path=this.value;scorecard()"><option value="">${t('all_path')}</option>${paths.map(k=>`<option ${filter.path===k?'selected':''}>${esc(k)}</option>`).join('')}</select>
  ${filter.tech?`<span class="chip t">${filter.tech} <a href="#" onclick="filter.tech='';scorecard();return false">✕</a></span>`:''}
  <span style="color:var(--muted)">${rows.length}/${S.findings.length}</span>
  <button class="btn" style="margin-left:auto" onclick="csv([['finding_id','title','techniques','severity','asset','attack_path','exploitability','mitigations','effective_status','inherent','residual','flags'],...visible().map(f=>[f.finding_id,f.title,f.techniques.join(';'),f.severity,f.asset,f.attack_path,f.exploitability,f.mitigations.join(';'),f.effective_status,f.inherent,f.residual,f.flags.join(';')])],'purple_scorecard.csv')">${t('export')}</button></div>
  <table id="tb-sc"><thead><tr><th>${t('finding')}</th><th>${t('title')}</th><th>${t('technique')}</th><th>${t('severity')}</th><th>${t('asset')}</th><th>${t('path')}</th><th>${t('red_status')}</th><th>${t('blue_mit')}</th><th>${t('status')}</th><th>${t('res')}</th></tr></thead><tbody>
  ${rows.map(f=>`<tr class="click" onclick="openF('${esc(f.finding_id)}')"><td class="red mono">${esc(f.finding_id)}</td><td>${esc(f.title)}</td><td>${f.techniques.map(x=>`<span class="chip t">${x}</span>`).join('')||`<span class="chip" style="border-color:var(--orange)">${esc(f.invalid_techniques.join(', ')||'—')}</span>`}</td><td data-v="${f.severity_w}">${sev(f.severity)}</td><td>${esc(f.asset)}</td><td>${esc(f.attack_path)}</td><td>${esc(f.exploitability.replace('_',' '))}</td><td class="blue">${f.mitigations.length?f.mitigations.map(m=>`<span class="chip" title="${esc(M[m].name)}">${m} <small style="color:var(--muted)">${t(M[m].link_type==='finding'?'by_finding':'by_technique')}</small></span>`).join(''):`<span style="color:var(--muted)">${t('none')}</span>`}</td><td data-v="${ST.indexOf(f.effective_status)}">${badge(f.effective_status)}</td><td data-v="${f.residual}"><b>${num(f.residual)}</b> <small style="color:var(--muted)">/ ${num(f.inherent)}</small></td></tr>`).join('')||`<tr><td colspan="10" class="empty">—</td></tr>`}
  </tbody></table></div>`;
 sortable('tb-sc');
}
function openF(id){const f=F[id];const d=document.getElementById('drawer');
 d.innerHTML=`<button class="close" onclick="document.getElementById('drawer').classList.remove('on')">✕</button><h3 class="mono">${esc(f.finding_id)}</h3><p><b>${esc(f.title)}</b></p>${badge(f.effective_status)} ${sev(f.severity)}
 <dl style="margin-top:14px"><dt>${t('technique')}</dt><dd>${f.techniques.map(x=>`<span class="chip t">${x}${S.techniques[x]?.name?' '+esc(S.techniques[x].name):''}</span>`).join('')||'—'}</dd><dt>${t('asset')}</dt><dd>${esc(f.asset)}</dd><dt>${t('path')}</dt><dd>${esc(f.attack_path)}</dd><dt>${t('exploit')}</dt><dd>${esc(f.exploitability)}</dd><dt>${t('exposed')}</dt><dd>${f.internet_exposed?'yes':'no'}</dd><dt>${t('acr')}</dt><dd>${f.acr??'—'}</dd><dt>${t('res')}</dt><dd><b>${num(f.residual)}</b> / ${num(f.inherent)} ${t('inh').toLowerCase()}</dd><dt>${t('found')}</dt><dd>${esc(f.date_found||'—')}</dd><dt>${t('ticket')}</dt><dd>${esc(f.ticket_id||'—')} ${esc(f.owner||'')}</dd><dt>${t('evidence')}</dt><dd>${esc(f.red_evidence||'—')}</dd><dt>${t('flags')}</dt><dd>${f.flags.map(x=>`<span class="chip" style="border-color:var(--orange)">${esc(x)}</span>`).join('')||'—'}</dd></dl>
 <h4>${t('blue_mit')}</h4>${f.mitigations.map(m=>{const x=M[m];return `<div class="card" style="padding:10px;border-left:3px solid var(--blue)"><b class="mono">${m}</b> ${esc(x.name)}<br><small>${esc(x.type)} · ${esc(x.framework||'')} · ${badge(x.status)} · ${t('retest')}: ${t(x.validation)} ${esc(x.validated_date||'')} · ${esc(x.owner||'')}${x.ticket_id?` · ${t('ticket_no')}: ${esc(x.ticket_id)}`:''}</small></div>`}).join('')||`<p style="color:var(--muted)">${t('none')}</p>`}
 <h4>${t('status_hist')}</h4>${f.status_rows.length?`<table>${f.status_rows.map(r=>`<tr><td>${esc(r.updated_date||'')}</td><td>${esc(r.raw_status)} → ${badge(r.status)}</td><td>${t(r.validation)} ${esc(r.validated_date||'')}</td><td>${esc(r.ticket_id)} ${esc(r.owner)}</td><td>${esc(r.notes)}</td></tr>`).join('')}</table>`:`<p style="color:var(--muted)">no_status_row</p>`}
 ${Object.keys(f.extra).length?`<h4>${t('extra')}</h4><dl>${Object.entries(f.extra).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`:''}`;
 d.classList.add('on');}

function heatmap(){
 const techs=Object.values(S.techniques).filter(x=>!x.is_sub&&(showAll||x.coverage!=='out_of_scope'));
 const cols=TACTICS.filter(tc=>techs.some(x=>x.tactic===tc));
 document.getElementById('s-heatmap').innerHTML=`<div class="card"><div class="tools"><div class="legend">${['gap','claimed','validated','untested_coverage','accepted'].map(c=>`<span><i style="background:var(--${{gap:'red',claimed:'orange',validated:'green',untested_coverage:'blue',accepted:'gray'}[c]})"></i>${t(c==='validated'?'validated_c':c==='accepted'?'accepted_c':c)}</span>`).join('')}</div></div>
  <div class="hm">${cols.map(tc=>`<div class="col"><h4>${tc}</h4>${techs.filter(x=>x.tactic===tc).sort((a,b)=>b.residual-a.residual).map(x=>{const subs=Object.values(S.techniques).filter(y=>y.is_sub&&y.parent===x.technique);return `<div class="cell c-${x.coverage}" onclick="filter.tech='${x.technique}';tab='scorecard';scorecard();show('scorecard')" onmousemove="tip(event,'${esc(x.technique)}')" onmouseleave="hideTip()"><div class="id">${x.technique}</div><div class="nm">${esc(x.name||'')}${subs.length?` <small>(${subs.map(s=>s.technique.split('.')[1]).join(', ')})</small>`:''}</div><div class="st">${x.findings.length} ${t('finding').toLowerCase()}${x.findings.length===1?'':'s'} · ${num(x.residual)}${x.mitigations.length?` · ${x.mitigations.length} ${t('mitigation').toLowerCase()}`:''}</div></div>`}).join('')}</div>`).join('')}</div>
  <div class="foot">${t('hm_foot')}</div></div>`;
}
function tip(e,id){const x=S.techniques[id],el=document.getElementById('tip');el.style.display='block';el.style.left=(e.clientX+14)+'px';el.style.top=(e.clientY+14)+'px';el.innerHTML=`<b>${id}</b> ${esc(x.name||'')}<br>${t(x.coverage==='validated'?'validated_c':x.coverage==='accepted'?'accepted_c':x.coverage)}<br>${Object.entries(x.status_counts).map(([k,n])=>`${n} ${esc(t(k))}`).join(' · ')||'—'}<br>${x.findings.map(esc).join(', ')}<br>${x.mitigations.map(esc).join(', ')}`;}
function hideTip(){document.getElementById('tip').style.display='none';}

// ---- Blue edits (manual overrides) --------------------------------------
S.blue_edits = S.blue_edits || [];
const EDIT_FIELDS=['owner','validated_date','ticket_id','validation_status'];
function editMap(){const m={};S.blue_edits.forEach(e=>{if(e.target_id)m[e.target_id]={...(m[e.target_id]||{}),...e}});return m;}
function applyEdits(){const em=editMap();Object.entries(em).forEach(([id,e])=>{const x=M[id]||F[id];if(!x)return;if(e.owner!=null&&e.owner!=='')x.owner=e.owner;if(e.validated_date)x.validated_date=e.validated_date;if(e.ticket_id!=null&&e.ticket_id!=='')x.ticket_id=e.ticket_id;if(e.validation_status)x.validation=e.validation_status;});}
function setEdit(id,field,val){
  let e=S.blue_edits.find(x=>x.target_id===id);
  if(!e){e={target_id:id,entity:M[id]?'mitigation':'finding'};S.blue_edits.push(e);}
  e[field]=val; e.edited_at=new Date().toISOString().slice(0,10);
  if(!EDIT_FIELDS.some(k=>e[k])){S.blue_edits=S.blue_edits.filter(x=>x!==e);}
  applyEdits(); validation(); header();
}
function revertEdit(id){S.blue_edits=S.blue_edits.filter(x=>x.target_id!==id);validation();header();}
function edCell(id,field,val,type){
  const em=editMap(), ed=em[id]&&em[id][field]!=null&&em[id][field]!==''; const v=esc(val||'');
  if(field==='validation_status'){return `<select class="ed${ed?' edited':''}" onchange="setEdit('${esc(id)}','validation_status',this.value)"><option value="not_retested"${val==='not_retested'||!val?' selected':''}>${t('not_retested')}</option><option value="retest_pass"${val==='retest_pass'?' selected':''}>${t('retest_pass')}</option><option value="retest_fail"${val==='retest_fail'?' selected':''}>${t('retest_fail')}</option></select>`;}
  return `<input class="ed${ed?' edited':''}" type="${type||'text'}" value="${v}" placeholder="—" onchange="setEdit('${esc(id)}','${field}',this.value)">`;
}
function exportEditsJSON(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({blue_edits:S.blue_edits},null,1)],{type:'application/json'}));a.download='blue_edits.json';a.click();}
function exportEditsCSV(){csv([['target_id','entity','owner','validated_date','ticket_id','validation_status','note','edited_at','edited_by'],...S.blue_edits.map(e=>[e.target_id,e.entity,e.owner,e.validated_date,e.ticket_id,e.validation_status,e.note,e.edited_at,e.edited_by])],'blue_edits.csv');}
function parseCSV(txt){const rows=[];let row=[],cur='',q=false;for(let i=0;i<txt.length;i++){const c=txt[i];if(q){if(c==='"'){if(txt[i+1]==='"'){cur+='"';i++;}else q=false;}else cur+=c;}else if(c==='"')q=true;else if(c===','||c===';'){row.push(cur);cur='';}else if(c==='\n'||c==='\r'){if(c==='\r'&&txt[i+1]==='\n')i++;row.push(cur);rows.push(row);row=[];cur='';}else cur+=c;}if(cur!==''||row.length){row.push(cur);rows.push(row);}return rows.filter(r=>r.some(v=>v!==''));}
const KEYMAP={targetid:'target_id',id:'target_id',mitigationid:'target_id',findingid:'target_id',owner:'owner',assignee:'owner',validateddate:'validated_date',retestdate:'validated_date',datadoreteste:'validated_date',ticketid:'ticket_id',ticketnumber:'ticket_id',ticket:'ticket_id',numerodoticket:'ticket_id',validationstatus:'validation_status',retestresult:'validation_status',retest:'validation_status',note:'note',notes:'note',editedat:'edited_at',editedby:'edited_by',entity:'entity'};
function importEdits(input){const f=input.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{let rows=[];const txt=r.result;try{if(f.name.toLowerCase().endsWith('.json')){const j=JSON.parse(txt);rows=Array.isArray(j)?j:(j.blue_edits||j.edits||j.overrides||[]);}else{const c=parseCSV(txt);const h=c[0].map(x=>KEYMAP[x.toLowerCase().replace(/[^a-z]/g,'')]||x);rows=c.slice(1).map(rw=>Object.fromEntries(h.map((k,i)=>[k,rw[i]||''])));}}catch(e){alert('Invalid file: '+e.message);return;}
  let n=0;rows.forEach(e=>{const id=String(e.target_id||'').trim();if(!id||!(M[id]||F[id]))return;let cur=S.blue_edits.find(x=>x.target_id===id);if(!cur){cur={target_id:id,entity:M[id]?'mitigation':'finding'};S.blue_edits.push(cur);}EDIT_FIELDS.concat(['note','edited_at','edited_by']).forEach(k=>{if(e[k]!=null&&e[k]!=='')cur[k]=String(e[k]).trim();});if(e.validation_status)cur.validation_status=/fail/i.test(e.validation_status)?'retest_fail':/pass|ok|block|valid/i.test(e.validation_status)?'retest_pass':'not_retested';n++;});
  applyEdits();validation();header();alert(`${n} ${t('imported')}`);input.value='';};r.readAsText(f);}
function downloadWithEdits(){const clone=document.documentElement.cloneNode(true);clone.querySelector('#purple-state').textContent=JSON.stringify(S).replace(/<\//g,'<\\/');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['<!DOCTYPE html>\n'+clone.outerHTML],{type:'text/html'}));a.download='tenable-purple-team-dashboard.html';a.click();}
applyEdits();

function validation(){
 const v=S.validation, em=editMap();
 const mits=S.mitigations, rem=S.findings.filter(f=>f.effective_status==='remediated'&&!f.mitigations.length);
 const rowCls=id=>em[id]?' class="edited"':'';
 document.getElementById('s-validation').innerHTML=`<div class="card"><div class="strip"><div><b style="color:var(--orange)">${v.claimed}</b>${t('v_claimed')}</div><div><b style="color:var(--green)">${v.validated}</b>${t('v_validated')}</div><div><b style="color:var(--red)">${v.failed}</b>${t('v_failed')}</div><div><b class="acc" style="color:var(--accent)">${num(v.claimed_unproven_residual)}</b>${t('v_unproven')}</div></div></div>
  ${S.blue_edits.length?`<div class="banner edits"><b>${S.blue_edits.length}</b> ${t('edits_pending')}</div>`:''}
  <div class="row c2"><div class="card"><h3>${t('v_queue')}</h3>${v.retest_queue.length?`<table>${v.retest_queue.map((id,i)=>{const f=F[id];return `<tr class="click" onclick="openF('${id}')"><td>${i+1}</td><td class="mono">${id}</td><td>${esc(f.title)}</td><td>${f.techniques.join(', ')}</td><td><b>${num(f.residual)}</b></td></tr>`}).join('')}</table>`:`<div class="empty">—</div>`}</div>
  <div class="card"><h3>${t('blue_mit')}</h3><p class="foot" style="margin:0 0 10px">${t('edit_hint')}</p>
  <div class="tools"><label class="btn" style="cursor:pointer">${t('import_edits')} <input type="file" accept=".json,.csv,.txt" style="display:none" onchange="importEdits(this)"></label><button class="btn" onclick="exportEditsJSON()">${t('export_json')}</button><button class="btn" onclick="exportEditsCSV()">${t('export_csv')}</button><button class="btn p" onclick="downloadWithEdits()">${t('dl_html')}</button>
  <button class="btn" style="margin-left:auto" onclick="csv([['mitigation_id','name','type','framework','techniques','findings','status','validation','validated_date','owner','ticket_id','link_type','flags'],...S.mitigations.map(m=>[m.mitigation_id,m.name,m.type,m.framework,m.techniques.join(';'),m.linked_findings.join(';'),m.status,m.validation,m.validated_date,m.owner,m.ticket_id,m.link_type,m.flags.join(';')])],'purple_validation.csv')">${t('export')}</button></div>
  <table id="tb-v"><thead><tr><th>${t('mitigation')}</th><th>${t('type')}</th><th>${t('framework')}</th><th>${t('technique')}</th><th>${t('covers')}</th><th>${t('blue_status')}</th><th>${t('retest')}</th><th>${t('retest_date')}</th><th>${t('owner')}</th><th>${t('ticket_no')}</th><th></th></tr></thead><tbody>
  ${mits.map(m=>`<tr${rowCls(m.mitigation_id)}><td class="blue"><span class="mono">${esc(m.mitigation_id)}</span><br><small>${esc(m.name)}</small></td><td>${esc(m.type)}</td><td>${esc(m.framework)}</td><td>${m.techniques.map(x=>`<span class="chip t">${x}</span>`).join('')}</td><td>${m.linked_findings.map(x=>`<span class="chip">${x}</span>`).join('')||`<span style="color:var(--orange)">orphan</span>`}</td><td>${badge(m.status)}</td><td data-v="${m.validation}">${edCell(m.mitigation_id,'validation_status',m.validation)}</td><td>${edCell(m.mitigation_id,'validated_date',m.validated_date,'date')}</td><td>${edCell(m.mitigation_id,'owner',m.owner)}</td><td>${edCell(m.mitigation_id,'ticket_id',m.ticket_id)}</td><td>${em[m.mitigation_id]?`<button class="btn" title="${t('clear_edit')}" onclick="revertEdit('${esc(m.mitigation_id)}')">↺</button>`:''}</td></tr>`).join('')}
  ${rem.map(f=>`<tr${rowCls(f.finding_id)}><td class="blue"><span class="mono">${esc(f.finding_id)}</span><br><small>${esc(f.title)}</small></td><td>ticket</td><td></td><td>${f.techniques.map(x=>`<span class="chip t">${x}</span>`).join('')}</td><td><span class="chip">${f.finding_id}</span></td><td>${badge('remediated')}</td><td data-v="${f.validation}">${edCell(f.finding_id,'validation_status',f.validation)}</td><td>${edCell(f.finding_id,'validated_date',f.validated_date,'date')}</td><td>${edCell(f.finding_id,'owner',f.owner)}</td><td>${edCell(f.finding_id,'ticket_id',f.ticket_id)}</td><td>${em[f.finding_id]?`<button class="btn" title="${t('clear_edit')}" onclick="revertEdit('${esc(f.finding_id)}')">↺</button>`:''}</td></tr>`).join('')}
  </tbody></table></div></div>`;
 sortable('tb-v');
}
function bars(obj,keyLabel){const max=Math.max(...Object.values(obj).map(x=>x.inherent||0),1);return `<div class="rollup">${Object.entries(obj).sort((a,b)=>b[1].residual-a[1].residual).map(([k,x])=>`<div class="r"><div title="${esc(k)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${keyLabel?keyLabel(k,x):esc(k)}</div><div class="bar"><i style="width:${100*x.inherent/max}%"></i><b style="width:${100*x.residual/max}%"></b></div><div><b>${num(x.residual)}</b> <small style="color:var(--muted)">/ ${num(x.inherent)}</small></div></div>`).join('')}</div>`;}
function residual(){
 const tech=Object.fromEntries(Object.values(S.techniques).filter(x=>!x.is_sub&&x.findings.length).map(x=>[x.technique,x]));
 const acc=S.findings.filter(f=>f.effective_status==='accepted');
 document.getElementById('s-residual').innerHTML=`<div class="card"><h3>${t('top')}</h3><table id="tb-top"><thead><tr><th>#</th><th>${t('finding')}</th><th>${t('title')}</th><th>${t('technique')}</th><th>${t('severity')}</th><th>${t('path')}</th><th>${t('status')}</th><th>${t('res')}</th></tr></thead><tbody>
  ${S.top.map((id,i)=>{const f=F[id];return `<tr class="click" onclick="openF('${id}')"><td>${i+1}</td><td class="red mono">${id}</td><td>${esc(f.title)}</td><td>${f.techniques.map(x=>`<span class="chip t">${x}</span>`).join('')}</td><td data-v="${f.severity_w}">${sev(f.severity)}</td><td>${esc(f.attack_path)}</td><td>${badge(f.effective_status)}</td><td data-v="${f.residual}"><b>${num(f.residual)}</b> <small style="color:var(--muted)">/ ${num(f.inherent)}</small></td></tr>`}).join('')}</tbody></table></div>
  <div class="row c3"><div class="card"><h3>${t('by_tech')}</h3>${bars(tech,(k,x)=>`<span class="mono">${k}</span> <small style="color:var(--muted)">${esc(x.name||'')}</small>`)}</div><div class="card"><h3>${t('by_tactic')}</h3>${bars(S.tactics)}</div><div class="card"><h3>${t('by_path')}</h3>${bars(S.attack_paths,(k,x)=>`${esc(k)}<br><small style="color:var(--muted)">${t('weakest')}: <span class="mono">${esc(x.weakest_link)}</span></small>`)}</div></div>
  ${acc.length?`<div class="card" style="color:var(--muted)"><h3>${t('acc_note')}: ${num(S.summary.accepted_risk)}</h3>${acc.map(f=>`<span class="chip" onclick="openF('${f.finding_id}')" style="cursor:pointer">${f.finding_id} ${esc(f.title)} (${num(f.inherent)})</span>`).join(' ')}</div>`:''}`;
 sortable('tb-top');
}
function dq(){
 const d=S.data_quality, keys=Object.keys(d);
 document.getElementById('s-dq').innerHTML=keys.length?`<div class="card"><div class="tools"><button class="btn" onclick="csv([['flag','entity','id','detail'],...Object.entries(S.data_quality).flatMap(([k,v])=>v.map(x=>[k,x.entity,x.id,x.detail]))],'purple_data_quality.csv')">${t('export')}</button></div>
  <table><thead><tr><th>${t('flag')}</th><th>${t('count')}</th><th>${t('entity')}</th><th>${t('id')}</th><th>${t('detail')}</th></tr></thead><tbody>${keys.map(k=>d[k].map((x,i)=>`<tr>${i===0?`<td rowspan="${d[k].length}"><span class="chip" style="border-color:var(--orange)">${esc(k)}</span></td><td rowspan="${d[k].length}"><b>${d[k].length}</b></td>`:''}<td>${esc(x.entity)}</td><td class="mono">${esc(x.id)}</td><td>${esc(x.detail)}</td></tr>`).join('')).join('')}</tbody></table></div>`:`<div class="banner ok">${t('dq_ok')}</div>`;
}
function changes(){
 const d=S.delta, el=document.getElementById('s-changes');
 if(!d){el.innerHTML=`<div class="card empty">${t('ch_none')}</div>`;return;}
 const list=(title,items,fmt)=>`<div class="card"><h3>${title} <span class="chip">${items.length}</span></h3>${items.length?`<table>${items.map(fmt).join('')}</table>`:`<div class="empty">—</div>`}</div>`;
 const rec=r=>`<tr class="click" onclick="openF('${r.finding_id}')"><td class="mono">${r.finding_id}</td><td>${esc(F[r.finding_id]?.title)}</td><td>${badge(r.from)} → ${badge(r.to)}</td><td>${num(r.residual_from)} → <b>${num(r.residual_to)}</b></td></tr>`;
 const idrow=id=>`<tr class="click" onclick="openF('${id}')"><td class="mono">${id}</td><td>${esc(F[id]?.title)}</td><td>${F[id]?badge(F[id].effective_status):''}</td><td>${F[id]?num(F[id].residual):''}</td></tr>`;
 el.innerHTML=`${d.weights_changed?`<div class="banner">${t('ch_w')}</div>`:''}
  <div class="card"><div class="strip"><div><b style="color:var(--accent)">${d.index_from??'—'} → ${d.index_to}</b>${t('index_move')}</div><div><b style="color:var(--blue)">${d.new.length}</b>${t('ch_new')}</div><div><b style="color:var(--green)">${d.resolved.length}</b>${t('ch_resolved')}</div><div><b style="color:var(--red)">${d.regressed.length}</b>${t('ch_regressed')}</div><div><b style="color:var(--purple)">${d.changed.length}</b>${t('ch_changed')}</div></div></div>
  <div class="row c2">${list(t('ch_regressed'),d.regressed,rec)}${list(t('ch_resolved'),d.resolved,rec)}${list(t('ch_new'),d.new,idrow)}${list(t('ch_changed'),d.changed,rec)}
  ${list(t('ch_tech'),d.technique_moves,m=>`<tr><td class="mono">${m.technique}</td><td>${esc(S.techniques[m.technique]?.name||'')}</td><td>${num(m.from)} → <b>${num(m.to)}</b> <span class="${m.delta>0?'up':'down'}">(${m.delta>0?'+':''}${num(m.delta)})</span></td><td>${esc(m.coverage_from||'')} → ${esc(m.coverage_to||'')}</td></tr>`)}
  ${list(t('ch_removed'),d.removed,id=>`<tr><td class="mono">${esc(id)}</td><td colspan="3" style="color:var(--muted)">not in current Red data</td></tr>`)}</div>`;
}
setLang(LANG);
</script>
</body>
</html>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True); ap.add_argument("--out", default="tenable-purple-team-dashboard.html")
    ap.add_argument("--lang", choices=["en", "pt"], default="en")
    a = ap.parse_args()
    state = json.load(open(a.state, encoding="utf-8"))
    blob = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    out = TEMPLATE.replace("__STATE__", blob).replace("__LANG__", a.lang).replace("__TITLE__", html.escape(state["meta"].get("engagement") or ""))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {a.out} ({len(out)//1024} KB, run {state['meta'].get('run_number')}, embedded state included)")

if __name__ == "__main__":
    main()
