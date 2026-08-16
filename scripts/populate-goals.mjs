import fs from 'fs';
import path from 'path';

const pageDataPath = path.join(process.cwd(), 'app', 'page-data.tsx');
let content = fs.readFileSync(pageDataPath, 'utf8');

const guidePaths = {
  "b1": "curriculum/beginner/01-ai-agent-foundations/README.md",
  "b2": "curriculum/beginner/02-agent-loop/README.md",
  "b3": "curriculum/beginner/03-workflow-or-agent/README.md",
  "b4": "curriculum/beginner/04-agent-development-frameworks/README.md",
  "b5": "curriculum/beginner/05-computer-using-agents/README.md",
  "i1": "curriculum/intermediate/01-tool-engineering/README.md",
  "i2": "curriculum/intermediate/02-context-engineering/README.md",
  "i3": "curriculum/intermediate/03-human-approval-permissions/README.md",
  "i4": "curriculum/intermediate/04-guardrails-untrusted-content/README.md",
  "i5": "curriculum/intermediate/05-agent-evaluation/README.md",
  "i6": "curriculum/intermediate/06-trajectory-optimization/README.md",
  "i8": "curriculum/intermediate/08-planning-task-decomposition/README.md",
  "i9": "curriculum/intermediate/09-agentic-rag/README.md",
  "i10": "curriculum/intermediate/10-langgraph-state-memory/README.md",
  "a1": "curriculum/advanced/01-single-vs-multi-agent/README.md",
  "a2": "curriculum/advanced/02-autogen-selector-teams/README.md",
  "a3": "curriculum/advanced/03-crewai-teams/README.md",
  "a4": "curriculum/advanced/04-hybrid-production-architecture/README.md",
  "a5": "curriculum/advanced/05-incident-response/README.md",
  "a6": "curriculum/advanced/06-agent-memory/README.md",
  "a7": "curriculum/advanced/07-world-models-environment-modeling/README.md",
  "a8": "curriculum/advanced/08-proactive-agents/README.md",
  "a9": "curriculum/advanced/09-model-routing/README.md",
  "a10": "curriculum/advanced/10-long-running-asynchronous-agents/README.md",
  "a11": "curriculum/advanced/11-llm-as-judge-agent-judges/README.md",
  "a12": "curriculum/advanced/12-agent-benchmarks/README.md",
  "a13": "curriculum/advanced/13-mcp-model-context-protocol/README.md",
  "a14": "curriculum/advanced/14-agent-skills/README.md",
  "a15": "curriculum/advanced/15-designing-reliable-agentic-systems/README.md",
  "a16": "curriculum/advanced/16-human-multi-agent-organizations/README.md",
  "a17": "curriculum/advanced/17-agentic-enterprise-architecture/README.md",
  "a18": "curriculum/advanced/18-agentic-software-engineering/README.md",
  "a19": "curriculum/advanced/19-embodied-agents-robotics/README.md",
  "a20": "curriculum/advanced/20-multimodal-agents/README.md",
  "a21": "curriculum/advanced/21-cost-latency-agent-economics/README.md",
  "a22": "curriculum/advanced/22-production-agent-architecture/README.md",
  "a23": "curriculum/advanced/23-agent-governance-responsible-ai/README.md",
  "a24": "curriculum/advanced/24-guardrails-policy-enforcement/README.md",
  "a25": "curriculum/advanced/25-agent-identity-authorization/README.md",
  "a26": "curriculum/advanced/26-agent-security/README.md",
  "a27": "curriculum/advanced/27-agent-observability/README.md",
  "a28": "curriculum/advanced/28-human-agent-collaboration/README.md",
  "a29": "curriculum/advanced/29-agent-orchestration/README.md",
  "a30": "curriculum/advanced/30-agent-communication-coordination/README.md",
  "a31": "curriculum/advanced/31-agent-protocol-stack/README.md",
};

// Split content into blocks
let blocks = content.split('{\n    "id": "');

for (let i = 1; i < blocks.length; i++) {
  let block = blocks[i];
  let idMatch = block.match(/^([^"]+)"/);
  if (idMatch) {
    let id = idMatch[1];
    let readmePath = guidePaths[id];
    let goals = [];
    if (readmePath && fs.existsSync(readmePath)) {
      let readme = fs.readFileSync(readmePath, 'utf8');
      
      let stepByStepMatch = readme.match(/## Step-by-step training([\s\S]*?)(?=##|$)/);
      if (stepByStepMatch) {
        let items = stepByStepMatch[1].match(/^\d+\.\s+(.*)$/gm);
        if (items) {
           goals = items.map(x => x.replace(/^\d+\.\s+/, '').trim());
        }
      }
      
      if (goals.length === 0) {
         let outcomeMatch = readme.match(/## Outcomes([\s\S]*?)(?=##|$)/);
         if (outcomeMatch) {
            let outText = outcomeMatch[1].replace(/After this module you can\s*/i, '').trim();
            let parts = outText.split(/;\s*and\s*|;\s*|\.\s*/).filter(x => x.length > 5);
            goals = parts.map(x => {
              let txt = x.trim().replace(/^and\s+/, '');
              return txt.charAt(0).toUpperCase() + txt.slice(1);
            });
         }
      }
      
      if (goals.length === 0) {
         goals = [
           "Review the theoretical concepts and architecture.",
           "Open the companion notebook and execute the cells.",
           "Trace the execution and observe the output.",
           "Identify the boundary constraints and failure points."
         ];
      }
    }
    
    let goalsStr = JSON.stringify(goals);
    
    // Check if goals already exists
    if (block.includes('"goals":')) {
       block = block.replace(/"goals":\s*\[[\s\S]*?\],/, `"goals": ${goalsStr},`);
    } else {
       block = block.replace(/"code":\s*"",/, `"code": "",\n    "goals": ${goalsStr},`);
    }
    
    blocks[i] = block;
  }
}

let newContent = blocks.join('{\n    "id": "');
fs.writeFileSync(pageDataPath, newContent);
console.log('Goals populated correctly.');
