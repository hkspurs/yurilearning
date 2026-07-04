#!/usr/bin/env node
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),cp=require('child_process');
const root=path.resolve(__dirname,'..'),game=path.join(root,'phonics-game');
const manifestPath=path.join(game,'audio_manifest.json'),cfg2=path.join(game,'level2-clips-config.js'),assets=path.join(game,'assets');
const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8')),items=manifest.items||[];
const errors=[],warnings=[],review=[];const strip=s=>String(s||'').split('?')[0];
function loadCfg(file,key){const box={window:{}};vm.createContext(box);vm.runInContext(fs.readFileSync(file,'utf8'),box,{filename:file});return box.window[key]||{};}
function has(cmd){try{cp.execFileSync(cmd,['-version'],{stdio:'ignore'});return true}catch{return false}}
function durMs(file){try{const s=cp.execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',file],{encoding:'utf8'}).trim();return Math.round(Number(s)*1000)}catch{return null}}
function volume(file){try{cp.execFileSync('ffmpeg',['-hide_banner','-nostats','-i',file,'-af','volumedetect','-f','null','-'],{stdio:['ignore','ignore','pipe']});return {}}catch(e){const t=String(e.stderr||'');const mean=t.match(/mean_volume:\s*(-?\d+(?:\.\d+)?) dB/);const max=t.match(/max_volume:\s*(-?\d+(?:\.\d+)?) dB/);return {rmsDb:mean?+mean[1]:null,peakDb:max?+max[1]:null}}}
function walk(dir){let out=[];if(!fs.existsSync(dir))return out;for(const n of fs.readdirSync(dir)){const p=path.join(dir,n),st=fs.statSync(p),rel=path.relative(game,p).replace(/\\/g,'/');if(st.isDirectory())out=out.concat(walk(p));else if(/\.(mp3|mp4|m4a|wav|ogg)$/i.test(n))out.push(rel)}return out}
const ids=new Set(),manifestFiles=new Set();
for(const it of items){
  if(!it.id)errors.push('manifest item missing id');else if(ids.has(it.id))errors.push('duplicate audio id: '+it.id);else ids.add(it.id);
  if(!it.file)errors.push((it.id||'?')+': missing file path');
  if(!it.expectedText)errors.push((it.id||'?')+': missing expectedText');
  if(!it.expectedPhoneme)warnings.push((it.id||'?')+': missing phoneme metadata');
  if(it.qaStatus==='review_required')review.push(it.id);
  const f=strip(it.file);if(f)manifestFiles.add(f);
  if(f&&!fs.existsSync(path.join(game,f)))errors.push(it.id+': missing audio file '+f);
  const m=f.match(/brighter-([aeiou])\./i);if(m&&it.relatedLetter&&m[1].toUpperCase()!==String(it.relatedLetter).toUpperCase())warnings.push(it.id+': filename and relatedLetter mismatch');
}
const cfg=loadCfg(cfg2,'PHONICS_LEVEL2_CLIPS'),usedFiles=new Set(),refs=[];
for(const [rowName,row] of Object.entries(cfg)){
  const file=strip(row.audio||'');usedFiles.add(file);const labels=Object.keys(row.clips||{});refs.push({rowName,file,labels});
  if(!fs.existsSync(path.join(game,file)))errors.push('game config references missing audio file: '+file);
  const item=items.find(x=>strip(x.file)===file);
  if(!item)warnings.push('referenced audio file missing from manifest: '+file);else{
    const missing=labels.filter(x=>!(item.clipLabels||[]).includes(x)),extra=(item.clipLabels||[]).filter(x=>!labels.includes(x));
    if(missing.length)errors.push(item.id+': manifest missing clip labels '+missing.join(','));
    if(extra.length)warnings.push(item.id+': manifest has extra clip labels '+extra.join(','));
    if(item.clipCount!==labels.length)errors.push(item.id+': clipCount '+item.clipCount+' mismatches config '+labels.length);
  }
}
for(const f of manifestFiles)if(!usedFiles.has(f))warnings.push('manifest audio file not used by current game config: '+f);
for(const f of walk(assets))if(!usedFiles.has(f)&&!manifestFiles.has(f))warnings.push('unused audio asset: '+f);
const canProbe=has('ffprobe'),canFfmpeg=has('ffmpeg'),technical=[];
for(const f of new Set([...usedFiles,...manifestFiles])){const p=path.join(game,f);if(!fs.existsSync(p))continue;const o={file:f};if(canProbe){o.durationMs=durMs(p);if(!o.durationMs||o.durationMs<=0)errors.push('silent or zero duration file: '+f)}if(canFfmpeg){Object.assign(o,volume(p));if(o.peakDb!==null&&o.peakDb>-0.1)warnings.push('possible clipping or too loud audio: '+f+' peak '+o.peakDb+' dB')}technical.push(o)}
const report={summary:{manifestItems:items.length,gameReferencedAudioFiles:usedFiles.size,gameReferencedRows:refs.length,errors:errors.length,warnings:warnings.length,reviewRequired:review.length,ffprobe:canProbe,ffmpegVolumedetect:canFfmpeg},errors,warnings,reviewRequired:review,technical};
console.log(JSON.stringify(report,null,2));if(errors.length)process.exit(1);
