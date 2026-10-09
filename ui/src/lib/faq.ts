export type FaqEntry = {
  id: string;
  question: string;
  answer: string;
  keywords: string[];
};

export const FAQ: FaqEntry[] = [
  {
    id: "what",
    question: "What is this application?",
    answer:
      "netraOM CSPM Trust Graph is a local prototype. Dashboard loads synthetic fixtures into Postgres (inventory and findings) and Neo4j (trust graph). It is not a production SOC and it is not connected to a live cloud account.",
    keywords: ["netraom", "prototype", "cspm", "trust", "graph", "about"],
  },
  {
    id: "telemetry",
    question: "Is the threat map live telemetry?",
    answer:
      "No. The map is simulated. When findings are loaded, arcs use those findings' severity, titles, and assets, placed on a fixed set of regions. Times and coordinates are synthesized. If nothing is loaded, the map shows a labeled fallback dataset from the shared analytics module.",
    keywords: ["live", "telemetry", "map", "threat", "simulated", "real"],
  },
  {
    id: "load",
    question: "How do I load demo data?",
    answer:
      "On the Dashboard, use Load workspace: enterprise (about 500 assets), the small AWS lab, or AWS + GCP. That calls POST /demo/load and replaces the demo tenant. Inventory, Findings, and Learn counts refresh after the load.",
    keywords: ["load", "demo", "fixture", "enterprise", "scenario", "workspace"],
  },
  {
    id: "postgres",
    question: "What is stored in Postgres?",
    answer:
      "Portal facts: asset rows and finding rows (fingerprint, source, rule, severity, risk score, path metadata). Inventory and Findings read Postgres. The Postgres lab runs guarded SELECT statements.",
    keywords: ["postgres", "sql", "database", "assets", "tables"],
  },
  {
    id: "neo4j",
    question: "What is stored in Neo4j?",
    answer:
      "Trust-graph nodes and TRUST_EDGE relationships. Asset neighborhood and finding attack-path views read the graph. The graph lab runs guarded Cypher. In unit tests the same model can sit on NetworkX.",
    keywords: ["neo4j", "cypher", "graph", "edges", "nodes"],
  },
  {
    id: "cspm-vs-combo",
    question: "What is the difference between CSPM and toxic combinations?",
    answer:
      "CSPM findings are misconfigurations, usually one row for an asset (public bucket, open database, API without auth). Toxic combinations are multi-step paths, such as internet exposure plus a write grant, and they store path edges. Both appear under Findings.",
    keywords: ["cspm", "toxic", "combo", "misconfiguration", "combination", "difference"],
  },
  {
    id: "risk",
    question: "How is the risk score calculated?",
    answer:
      "The attack path engine scores exposure, privilege, exploitability, and impact from 0 to 25 each. The final score is their sum, capped at 100. Bands are critical at 90 or above, high at 70, medium at 40, otherwise low. The Findings panel shows the breakdown.",
    keywords: ["risk", "score", "exposure", "privilege", "exploitability", "impact", "severity"],
  },
  {
    id: "algorithms",
    question: "Does the backend run BFS, DFS, or Dijkstra?",
    answer:
      "Finding scoring calls assess_finding_path, which uses find_rank_paths_dijkstra: a bounded heap search ordered by traversal cost, then ranked by risk score. It is Dijkstra-style. Comments mention A*, but there is no heuristic, so it is not A*. find_candidate_paths_bfs exists and is unit-tested, but finding scoring does not call it. DFS is named in the module docstring and is not implemented. The Learn attack-path page explains BFS, DFS, and Dijkstra as education and labels what this app actually runs.",
    keywords: ["bfs", "dfs", "dijkstra", "algorithm", "astar", "a*", "traversal", "path"],
  },
  {
    id: "no-path",
    question: "What happens when no attack path is found?",
    answer:
      "The engine still returns a factor score for the finding nodes and leaves the attack route empty. The Findings graph then shows neighborhood context instead of a highlighted route. A standalone public bucket is an example.",
    keywords: ["missing", "no path", "empty", "route", "standalone"],
  },
  {
    id: "learn",
    question: "What do the Learn labs cover?",
    answer:
      "Overview of Postgres versus Neo4j, raw collector JSON versus the normalized trust-graph bundle, a Postgres SQL lab, a Neo4j Cypher lab, a query cookbook, and an Attack Path Analysis diagram. They teach this prototype. They do not change a production account.",
    keywords: ["learn", "lab", "inventory", "cookbook", "training", "student"],
  },
  {
    id: "assistant",
    question: "Is the Security Assistant an LLM?",
    answer:
      "No. It is a rule-based FAQ. Your question is normalized and matched on keywords. If confidence is low, it shows related suggestions instead of inventing an answer. No AI API is called.",
    keywords: ["assistant", "chat", "llm", "ai", "faq", "bot"],
  },
  {
    id: "resolve",
    question: "Can I resolve or mitigate a finding?",
    answer:
      "Not on the server. Prototype findings have no resolve workflow. Dashboard statuses New, Investigating, Mitigated, and Resolved are an analyst workflow stored in this browser only. Exports label them the same way.",
    keywords: ["resolve", "mitigate", "status", "acknowledge", "workflow", "close"],
  },
  {
    id: "pdf",
    question: "What is in the PDF export?",
    answer:
      "A client-side PDF built with jsPDF from the same analytics model as the dashboard: KPIs, severity, category, the simulated 7-day trend, the risk list, and simulated map events. Findings have no timestamps, so the trend is labeled simulated. The report does not invent extra security products or integrations.",
    keywords: ["pdf", "export", "report", "download", "print"],
  },
  {
    id: "filters",
    question: "How do Findings filters work?",
    answer:
      "Findings has tabs for misconfigurations and toxic combinations, plus severity, rule, and text search in the URL. Chart clicks on the dashboard open /findings with a tab or severity query. Existing filters stay in the query string.",
    keywords: ["filter", "findings", "search", "severity", "tab", "query"],
  },
  {
    id: "neighborhood",
    question: "How does the asset graph work?",
    answer:
      "Open an asset to load its graph neighborhood. Clicking a node looks up the inventory asset for that graph id when one exists. Network-only nodes may not have an inventory row.",
    keywords: ["neighborhood", "asset", "graph", "node", "click", "inventory"],
  },
  {
    id: "api-down",
    question: "Why are the counts empty?",
    answer:
      "Either the demo API is down (default http://localhost:8000, override with VITE_API_URL) or no scenario has been loaded. The shell, Learn pages, assistant, and simulated map fallback still render. Errors stay visible instead of fake totals.",
    keywords: ["api", "down", "empty", "error", "localhost", "counts"],
  },
  {
    id: "fixtures",
    question: "Which clouds are in the fixtures?",
    answer:
      "The small labs are synthetic AWS and GCP stories (public buckets, SSH, roles). Enterprise is a generated estate of about 500 assets with repeated toxic combinations. Clicking Load does not call live AWS or GCP APIs.",
    keywords: ["aws", "gcp", "azure", "cloud", "fixture", "synthetic", "enterprise"],
  },
  {
    id: "theme",
    question: "Where is the theme stored?",
    answer:
      "The header toggle switches dark and light and stores the choice in localStorage under netraom-theme. Tokens cover the shell, pages, charts, dialogs, forms, and the graph canvas. Motion is reduced when the browser requests it.",
    keywords: ["theme", "dark", "light", "mode", "color"],
  },
  {
    id: "notifications",
    question: "Are notifications real alerts?",
    answer:
      "They are seeded from loaded findings, or from the simulated fallback when the API is down. Unread, dismiss, and status live in this browser. Toasts for critical and high items are rate-limited and start only after the first snapshot in the session, so opening the page does not toast every historical finding.",
    keywords: ["notification", "bell", "toast", "alert", "unread"],
  },
  {
    id: "visualization",
    question: "Where do I see an attack path?",
    answer:
      "Open Findings, select an alert, and the side panel draws the graph with React Flow. Stored attack-path nodes and edges are highlighted when the engine found a route. The Learn attack-path page is a separate educational flowchart, not that graph.",
    keywords: ["visualization", "react flow", "highlight", "canvas", "see path"],
  },
];

const STOP = new Set([
  "the",
  "a",
  "an",
  "is",
  "are",
  "of",
  "to",
  "and",
  "or",
  "in",
  "on",
  "for",
  "what",
  "how",
  "does",
  "do",
  "this",
  "app",
  "i",
  "me",
  "my",
  "with",
  "about",
  "can",
  "you",
]);

export function normalizeQuestion(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9*\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokens(value: string) {
  return normalizeQuestion(value)
    .split(" ")
    .filter((token) => token.length > 1 && !STOP.has(token));
}

export type FaqMatch = {
  entry: FaqEntry | null;
  confidence: number;
  suggestions: FaqEntry[];
};

export function matchFaq(query: string): FaqMatch {
  const normalized = normalizeQuestion(query);
  const queryTokens = tokens(query);
  if (!normalized) {
    return { entry: null, confidence: 0, suggestions: FAQ.slice(0, 4) };
  }

  const scored = FAQ.map((entry) => {
    const keywordBlob = normalizeQuestion(`${entry.question} ${entry.keywords.join(" ")}`);
    const answerBlob = normalizeQuestion(entry.answer);
    let score = 0;
    if (normalized.length > 6 && (keywordBlob.includes(normalized) || entry.question.toLowerCase().includes(query.trim().toLowerCase()))) {
      score += 0.62;
    }
    if (queryTokens.length) {
      const hits = queryTokens.filter((token) => keywordBlob.includes(token) || answerBlob.includes(token)).length;
      score += (hits / queryTokens.length) * 0.72;
      const keywordHits = queryTokens.filter((token) => entry.keywords.some((keyword) => keyword.includes(token) || token.includes(keyword))).length;
      score += (keywordHits / queryTokens.length) * 0.28;
    }
    return { entry, score };
  }).sort((a, b) => b.score - a.score);

  const suggestions = scored.slice(0, 3).map((item) => item.entry);
  const best = scored[0];
  if (!best || best.score < 0.45) {
    return { entry: null, confidence: best?.score ?? 0, suggestions };
  }
  return { entry: best.entry, confidence: Math.min(0.99, best.score), suggestions };
}

export const SUGGESTED_QUESTIONS = [
  FAQ[0].question,
  FAQ[2].question,
  FAQ[5].question,
  FAQ[6].question,
  FAQ[7].question,
  FAQ[11].question,
];
