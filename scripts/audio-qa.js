#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const game=path.join(root,'phonics-game');
const manifest=JSON.parse(fs.readFileSync(path.join(game,'audio_manifest.json'),'utf8'));
const items=manifest.items||[];
const errors=[];const warnings=[];const review=[];const ids=new Set();
function strip(s){return String(s||'').split('?')[0];}
for(const item of items){
  if(!item.id)errors.push('missing id');
  else if(ids.has(item.id))errors.push('duplicate audio id: '+item.id);
  else ids.add(item.id);
  if(!item.file)errors.push(item.id+': missing file path');
  if(!item.expectedText)errors.push(item.id+': missing expectedText');
  if(!item.expectedPhoneme)warnings.push(item.id+': missing phoneme metadata');
  if(item.qaStatus==='review_required')review.push(item.id);
  const f=strip(item.file);
  if(f&&!fs.existsSync(path.join(game,f)))errors.push(item.id+': missing audio file '+f);
  const m=f.match(/brighter-([aeiou])\./i);
  if(m&&item.expectedText&&m[1].toUpperCase()!==item.expectedText[0].toUpperCase())warnings.push(item.id+': filename and expectedText mismatch');
}
console.log(JSON.stringify({summary:{items:items.length,errors:errors.length,warnings:warnings.length,reviewRequired:review.length},errors,warnings,reviewRequired:review},null,2));
if(errors.length)process.exit(1);
