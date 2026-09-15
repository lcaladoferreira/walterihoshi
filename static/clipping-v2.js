(function(){
'use strict';
var doc=document;
function $$(s,c){return Array.prototype.slice.call((c||doc).querySelectorAll(s));}
function $(s,c){return (c||doc).querySelector(s);}
function norm(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
function hojeISO(){var d=new Date();var p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d);var m={};p.forEach(function(x){m[x.type]=x.value;});return m.year+'-'+m.month+'-'+m.day;}
function diasEntre(a,b){var da=new Date(a+'T12:00:00Z'),db=new Date(b+'T12:00:00Z');return Math.floor((db-da)/86400000);}
function init(){
 var painel=$('#filtros-clipping-v2');if(!painel)return;
 var campo=$('#clip-texto-v2'),periodo=$('#clip-periodo'),fonte=$('#clip-fonte-v2'),saida=$('#clip-contagem-v2'),aviso=$('#clip-aviso-v2');
 var itens=$$('.clip-item[data-fonte]');var hoje=hojeISO();
 function aplicar(){
  var q=norm(campo&&campo.value),per=periodo?periodo.value:'7',ft=fonte?fonte.value:'todas',n=0;
  itens.forEach(function(li){
   var sec=li.closest('.clip-dia');var data=(sec&&sec.id||'').replace(/^dia-/,'');var ok=true;
   if(q){var h=norm(li.getAttribute('data-texto')||li.textContent);var termos=q.split(/\s+/).filter(Boolean);ok=termos.every(function(t){return h.indexOf(t)!==-1;});}
   if(ok&&per!=='tudo'&&data){var dd=diasEntre(data,hoje);if(per==='hoje')ok=dd===0;else if(per==='7')ok=dd>=0&&dd<=6;else if(per==='30')ok=dd>=0&&dd<=29;}
   if(ok&&ft==='oficial')ok=li.getAttribute('data-oficial')==='1';
   if(ok&&ft==='imprensa')ok=li.getAttribute('data-oficial')!=='1';
   li.hidden=!ok;if(ok)n++;
  });
  $$('.clip-dia').forEach(function(sec){var v=$$('.clip-item:not([hidden])',sec).length;sec.hidden=v===0;var c=$('.conta',sec);if(c)c.textContent='('+v+')';});
  if(saida)saida.innerHTML=n===1?'<b>1</b> menção exibida.':'<b>'+n+'</b> menções exibidas.';
  if(aviso){
   aviso.hidden=n!==0;
   if(per==='hoje')aviso.textContent='Nenhuma menção publicada hoje nas fontes monitoradas. Altere o período para “Últimos 7 dias”.';
   else aviso.textContent='Nenhuma menção corresponde aos filtros escolhidos.';
  }
 }
 [campo,periodo,fonte].forEach(function(el){if(el){el.addEventListener(el.tagName==='INPUT'?'input':'change',aplicar);}});
 aplicar();
}
if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',init);else init();
})();
