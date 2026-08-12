import fs from 'fs';

const { lessons } = await import('../hub/lessons.mjs');
const { questions } = await import('../quiz/questions.mjs');

let guidePaths = {};
lessons.forEach(l => {
  guidePaths[l.id] = l.material || "";
});

const subjects = lessons.map(l => {
  const matchingQuestions = questions.filter(q => q.source && q.source.url && q.source.url.includes(l.material || 'NONEXISTENT'));
  
  const mappedQuiz = matchingQuestions.map(q => ({
    q: q.prompt,
    options: q.options,
    answer: q.correct.length === 1 ? q.correct[0] : q.correct
  }));

  return {
    id: l.id,
    level: l.level,
    step: l.step,
    title: l.title,
    description: l.summary,
    time: "45-60 min",
    outcome: l.outcome,
    lesson: l.detail || l.summary,
    exercise: l.run || l.summary,
    failures: [],
    notebook: l.notebook || l.lab || "",
    refs: l.refs || [],
    code: "",
    quiz: mappedQuiz
  };
});

let out = `
type Level = "Beginner" | "Intermediate" | "Advanced" | "Enterprise Agent";
type Subject = { id:string; level:Level; step:string; title:string; description:string; time:string; outcome:string; lesson:string; exercise:string; failures:string[]; notebook:string; refs:string[]; code:string; quiz:{q:string; options:string[]; answer:number | number[]}[] };

const guidePaths:Record<string,string> = ${JSON.stringify(guidePaths, null, 2)};

const subjects:Subject[] = ${JSON.stringify(subjects, null, 2)};
`;

fs.writeFileSync('app/page-data.tsx', out);
console.log('Migrated page data to app/page-data.tsx');
