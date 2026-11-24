import fs from 'node:fs/promises';
import {FileBlob,PresentationFile}from'@oai/artifact-tool';
const[file,out]=process.argv.slice(2);
try{const p=await PresentationFile.importPptx(await FileBlob.load(file));const r={source:file,full_deck_imported:true,slides:p.slides.items.length};await fs.writeFile(out,JSON.stringify(r,null,2));console.log(JSON.stringify(r));}
catch(e){const r={source:file,full_deck_imported:false,error:String(e),stack:String(e.stack).slice(-5000)};await fs.writeFile(out,JSON.stringify(r,null,2));console.log(JSON.stringify(r));process.exitCode=1;}
