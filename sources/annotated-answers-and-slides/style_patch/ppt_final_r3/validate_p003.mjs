import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root='/workspace/scratch/1facfb035d44/detail_work';
const out=path.join(root,'style_patch/ppt_final_r3');
const skill='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const name='小学四上同步素养卷第1册讲解课件答案.pptx';
await fs.mkdir(path.join(out,'validated'),{recursive:true});
await fs.mkdir(path.join(out,'qa'),{recursive:true});
const result=await finalizePresentation({
  workspaceDir:root,
  candidatePath:path.join(out,name),
  finalPath:path.join(out,'validated',name),
  pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:426,
  requiredNativeTableOwnerSlides:[],
  requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:['Droid Sans Fallback','Cambria Math']},
  verifyArtifactToolImport:true,
  receiptPath:path.join(out,'qa/finalizer_receipt.json'),
});
console.log(JSON.stringify({finalSha256:result.finalSha256,slideCount:result.firstPartyImport?.slideCount,packageStatus:result.packageIntegrity?.status,layoutFindingCount:result.presentationLayout?.findingCount,firstPartyImport:result.firstPartyImport}));
