/**
 * Prompt Support v3 — Token Optimization Engine for coding agents.
 * Pipeline: Raw → Detect task → Extract intent/constraints → Dedupe → Compress → Template → Generate → Score
 */
(function () {
  "use strict";

  const OUTPUT_PLACEHOLDER = "Cải thiện ngay hoặc Generate Prompt để xem kết quả.";

  const REPO_SLUG = "Banhang-Chogao/zola";
  const REPO_RULES_SHORT = [
    "Branch + PR only.",
    "No direct main commit.",
    "Run `zola build`.",
    "Update `CLAUDE.md` if reusable lesson.",
  ];

  const MODES = {
    auto: { id: "auto", label: "Auto Token Saver" },
    ultra: { id: "ultra", label: "Ultra Compact", wordMin: 80, wordMax: 150 },
    compact: { id: "compact", label: "Compact", wordMin: 150, wordMax: 300 },
    standard: { id: "standard", label: "Standard", wordMin: 300, wordMax: 600 },
    full: { id: "full", label: "Full Spec", wordMin: 600, wordMax: 1200 },
  };

  const FILLER_PATTERNS = [
    /\b(xin hãy|giúp tôi|tôi muốn|bạn có thể|cho tôi|nhờ bạn|làm ơn|cảm ơn|thanks|thank you)\b/gi,
    /\b(please|could you|can you|i want|i need|help me|would you|kindly|just|maybe|perhaps)\b/gi,
    /\b(được không|nhé|ạ|ơi|nha|giúp coi|kiểm tra giúp|thử xem|hình như|có vẻ)\b/gi,
    /\b(i think|i feel|it seems|looks like|probably)\b/gi,
  ];

  const VAGUE_PATTERNS = [
    /\b(thử xem|có thể|maybe|perhaps|hình như|có vẻ|kiểm tra giúp|nếu được thì)\b/gi,
  ];

  const SYNONYM_GROUPS = [
    {
      key: "Priority: urgent",
      patterns: [/\b(fix gấp|sửa ngay|urgent|làm liền|asap|gấp lắm|ngay lập tức)\b/gi],
    },
    {
      key: "No auto-merge",
      patterns: [/\b(không auto[- ]?merge|don't auto[- ]?merge|do not auto[- ]?merge|no auto[- ]?merge)\b/gi],
    },
    {
      key: "No direct main commit",
      patterns: [
        /\b(không commit main|don't commit.*main|no direct main|không push main|do not push.*main)\b/gi,
      ],
    },
    {
      key: "Separate PR required",
      patterns: [/\b(tạo pr|open pr|separate pr|branch riêng|nhánh riêng|pull request)\b/gi],
    },
  ];

  const TASK_TYPES = [
    {
      id: "workflow",
      label: "Workflow / GitHub Actions",
      weight: 1.4,
      patterns: [
        /\b(workflow|github actions?|ci\/?cd|\.github\/workflows|check run|status check|auto[- ]?merge|manual[- ]?approval|deploy\.yml|qa\.yml)\b/i,
      ],
    },
    {
      id: "security",
      label: "Security / Paywall",
      weight: 1.4,
      patterns: [
        /\b(security|paywall|oauth|jwt|xss|csrf|secret|credential|auth(?:entication)?|authorization|admin|whitelist)\b/i,
      ],
    },
    {
      id: "parser",
      label: "Data parser",
      weight: 1.3,
      patterns: [
        /\b(parser|parse|parsing|schema|csv|xlsx|excel|json output|dedupe|normalize|extract)\b/i,
      ],
    },
    {
      id: "dashboard",
      label: "Dashboard",
      weight: 1.2,
      patterns: [/\b(dashboard|chart|indexeddb|insights|build-dashboard|merge-report)\b/i],
    },
    {
      id: "compliance",
      label: "Compliance / Checker",
      weight: 1.2,
      patterns: [/\b(compliance|qa gate|qa_check|checker|audit|lint|policy)\b/i],
    },
    {
      id: "ui",
      label: "UI / UX",
      weight: 1.1,
      patterns: [
        /\b(ui|ux|giao diện|responsive|scss|css|component|layout|navbar|button|mobile|a11y|accessibility)\b/i,
      ],
    },
    {
      id: "seo",
      label: "SEO",
      weight: 1.1,
      patterns: [/\b(seo|meta tag|sitemap|canonical|structured data|lighthouse|og:|schema\.org)\b/i],
    },
    {
      id: "performance",
      label: "Performance",
      weight: 1.1,
      patterns: [/\b(performance|lcp|fcp|cls|ttfb|lazy load|optimize|bundle size|web-vitals)\b/i],
    },
    {
      id: "content",
      label: "Content / Article",
      weight: 1,
      patterns: [/\b(article|bài viết|markdown|frontmatter|content\/|blog post|changelog)\b/i],
    },
    {
      id: "admin",
      label: "Admin tool",
      weight: 1,
      patterns: [/\b(cms|editor\/|admin|mini cms|\/editor\/)\b/i],
    },
    {
      id: "bug_fix",
      label: "Bug fix",
      weight: 1.2,
      patterns: [
        /\b(fix|bug|lỗi|broken|fail(?:ed|ing)?|error|crash|regression|không hoạt động|doesn't work)\b/i,
      ],
    },
    {
      id: "feature",
      label: "Feature",
      weight: 1,
      patterns: [/\b(feature|feat|implement|thêm|add|create|build|new)\b/i],
    },
  ];

  const TARGET_HINTS = {
    grok: "Agent: Grok Build — execute commands yourself; do not tell the user what to run.",
    claude: "Agent: Claude Code — implement directly in repo; verify with project commands.",
    generic: "Agent: Coding agent — implement, test, and summarize changes.",
  };

  const root = document.querySelector("[data-prompt-support]");
  if (!root) return;

  const inputEl = root.querySelector("[data-psupport-input]");
  const outputCode = root.querySelector("[data-psupport-code]");
  const improveBtn = root.querySelector("[data-psupport-improve]");
  const generateBtn = root.querySelector("[data-psupport-generate]");
  const lintBtn = root.querySelector("[data-psupport-lint]");
  const copyPrimaryBtn = root.querySelector("[data-psupport-copy]");
  const compareBtn = root.querySelector("[data-psupport-compare]");
  const statusEl = root.querySelector("[data-psupport-status]");
  const budgetEl = root.querySelector("[data-psupport-budget]");
  const scoresEl = root.querySelector("[data-psupport-scores]");
  const lintResultsEl = root.querySelector("[data-psupport-lint-results]");
  const compareEl = root.querySelector("[data-psupport-compare-panel]");
  const tipsEl = root.querySelector("[data-psupport-tips]");
  const taskBadge = root.querySelector("[data-psupport-task-type]");
  const modeBadge = root.querySelector("[data-psupport-mode-badge]");

  const modeEl = root.querySelector("[data-psupport-mode]");
  const targetEl = root.querySelector("[data-psupport-target]");
  const tokenSaverEl = root.querySelector("[data-psupport-token-saver]");
  const repoRulesEl = root.querySelector("[data-psupport-repo-rules]");
  const claudeMdEl = root.querySelector("[data-psupport-claude-md]");
  const acceptanceEl = root.querySelector("[data-psupport-acceptance]");

  const copyBtns = {
    ultra: root.querySelector("[data-psupport-copy-ultra]"),
    compact: root.querySelector("[data-psupport-copy-compact]"),
    standard: root.querySelector("[data-psupport-copy-standard]"),
    full: root.querySelector("[data-psupport-copy-full]"),
  };

  let lastRaw = "";
  let lastActiveMode = "standard";
  let modeOutputs = {};
  let lastParsed = null;
  let lastRemovals = [];
  let compareVisible = false;

  function normalize(text) {
    return text.replace(/\r\n/g, "\n").trim();
  }

  function estimateTokens(text) {
    return Math.max(0, Math.ceil((text || "").length / 4));
  }

  function countWords(text) {
    return (text || "").split(/\s+/).filter(Boolean).length;
  }

  function cleanFiller(text, aggressive) {
    let out = text;
    FILLER_PATTERNS.forEach((re) => {
      out = out.replace(re, " ");
    });
    if (aggressive) {
      VAGUE_PATTERNS.forEach((re) => {
        out = out.replace(re, " ");
      });
      out = out.replace(/\b(very|really|quite|actually|basically|literally)\b/gi, " ");
    }
    return out.replace(/\s{2,}/g, " ").trim();
  }

  function extractCodeBlocks(text) {
    const blocks = [];
    const prose = text.replace(/```[\s\S]*?```/g, (block) => {
      blocks.push(block.replace(/^```\w*\n?/, "").replace(/```$/, "").trim());
      return "\n";
    });
    return { prose, blocks };
  }

  function extractUrls(text) {
    const urls = text.match(/https?:\/\/[^\s)>"]+/gi) || [];
    return [...new Set(urls.map((u) => u.replace(/[.,;]+$/, "")))];
  }

  function extractFilePaths(text) {
    const paths = new Set();
    const patterns = [
      /\.github\/workflows\/[\w.-]+/gi,
      /(?:^|[\s(])([\w.-]+\/)+[\w.-]+\.(?:py|js|ts|tsx|yml|yaml|md|scss|html|toml|json)/gim,
      /`([^`]+\.(?:py|js|yml|md|scss|html|toml|json))`/gi,
      /\b(CLAUDE\.md|config\.toml|render\.yaml)\b/gi,
    ];
    patterns.forEach((re) => {
      let m;
      const r = new RegExp(re.source, re.flags);
      while ((m = r.exec(text)) !== null) {
        const p = (m[1] || m[0]).replace(/^[\s(]+/, "").trim();
        if (p.length > 2 && p.length < 120) paths.add(p);
      }
    });
    if (/\.github\/workflows/i.test(text)) paths.add(".github/workflows/*");
    return [...paths];
  }

  function splitLines(text) {
    return text
      .split(/\n+/)
      .flatMap((line) => line.split(/(?<=[.!?;])\s+/))
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function isConstraintLine(line) {
    return /\b(phải|bắt buộc|không được|chỉ|only|must|should not|don't|do not|required|không|no auto|forbidden|đừng|dừng|tránh)\b/i.test(
      line
    );
  }

  function isAcceptanceLine(line) {
    return /\b(acceptance|tiêu chí|pass khi|đảm bảo|verify|kiểm tra|phải pass|should)\b/i.test(line);
  }

  function compressBullet(line, tokenSaver) {
    let s = cleanFiller(line, tokenSaver);
    s = s.replace(/^[-*•]\s+/, "");
    s = s.replace(/^\d+[.)]\s+/, "");
    s = s.replace(/\s+/g, " ").trim();
    if (!s) return "";
    s = s.replace(/\.$/, "");
    if (tokenSaver) {
      s = s.replace(/\b(in order to|so that|because)\b/gi, "→");
    }
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function dedupe(items) {
    const seen = new Set();
    return items.filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function applySynonymDedup(text) {
    let out = text;
    const extracted = [];
    SYNONYM_GROUPS.forEach(({ key, patterns }) => {
      let hit = false;
      patterns.forEach((re) => {
        if (re.test(out)) hit = true;
        out = out.replace(re, " ");
      });
      if (hit) extracted.push(key);
    });
    return { text: out.replace(/\s{2,}/g, " ").trim(), extracted: dedupe(extracted) };
  }

  function detectTaskType(text) {
    const scores = {};
    TASK_TYPES.forEach(({ id, weight, patterns }) => {
      let score = 0;
      patterns.forEach((re) => {
        const m = text.match(new RegExp(re.source, "gi"));
        if (m) score += m.length * weight;
      });
      if (score > 0) scores[id] = score;
    });
    const ranked = Object.entries(scores).sort((a, b) => b[1] - a[1]);
    if (!ranked.length) return { id: "feature", label: "Feature" };
    const hit = TASK_TYPES.find((t) => t.id === ranked[0][0]);
    return { id: hit.id, label: hit.label };
  }

  function repoRelated(text) {
    return new RegExp(REPO_SLUG.replace("/", "\\/") + "|\\bzola\\b|banhang-chogao", "i").test(text);
  }

  function wantsAutoMerge(text) {
    return /\bauto[- ]?merge\b/i.test(text) && !/\b(không|do not|don't|no)\s+auto[- ]?merge/i.test(text);
  }

  function buildRepoRules(text, includeRepo, includeClaudeMd) {
    if (!includeRepo || !repoRelated(text)) return [];
    let rules = [...REPO_RULES_SHORT];
    if (wantsAutoMerge(text)) {
      rules = rules.filter((r) => !/No direct main/i.test(r));
    }
    if (!includeClaudeMd) {
      rules = rules.filter((r) => !/CLAUDE\.md/i.test(r));
    }
    return rules;
  }

  function assessComplexity(raw, parsed, taskType) {
    const wordCount = countWords(raw);
    const itemCount =
      parsed.requirements.length +
      parsed.constraints.length +
      parsed.acceptance.length +
      parsed.files.length;
    let score = 0;
    score += Math.min(40, wordCount / 15);
    score += itemCount * 8;
    score += parsed.codeBlocks.length * 10;
    if (taskType.id === "bug_fix" && wordCount < 180 && itemCount <= 4) score -= 25;
    if (taskType.id === "workflow") score += 10;
    if (taskType.id === "feature" && wordCount > 400) score += 20;
    return { score, wordCount, itemCount };
  }

  function selectAutoMode(raw, parsed, taskType) {
    const { score, wordCount } = assessComplexity(raw, parsed, taskType);
    if (taskType.id === "bug_fix" && wordCount < 200 && parsed.requirements.length <= 2) return "ultra";
    if (taskType.id === "workflow" || (score >= 25 && score < 45)) return "compact";
    if (score >= 55 || wordCount > 500 || parsed.files.length > 4) return "full";
    if (score >= 35) return "standard";
    return "compact";
  }

  function parseInput(raw, opts) {
    const { prose, blocks } = extractCodeBlocks(raw);
    const deduped = applySynonymDedup(prose);
    const lines = splitLines(deduped.text);
    const requirements = [];
    const constraints = [];
    const acceptance = [];
    const context = [];
    const symptoms = [];
    let taskLead = [];

    if (deduped.extracted.length) {
      deduped.extracted.forEach((e) => {
        if (/Priority|urgent/i.test(e)) constraints.push(e);
        else constraints.push(e);
      });
    }

    lines.forEach((line) => {
      const c = compressBullet(line, opts.tokenSaver);
      if (!c) return;
      if (isAcceptanceLine(line)) {
        acceptance.push(c);
      } else if (isConstraintLine(line)) {
        constraints.push(c);
      } else if (/\b(lỗi|fail|error|broken|symptom|hiện|đang|shows?|displays?)\b/i.test(line)) {
        symptoms.push(c);
        context.push(c);
      } else if (taskLead.length < 2) {
        taskLead.push(c);
      } else {
        requirements.push(c);
      }
    });

    const urls = extractUrls(raw);
    if (urls.length) {
      context.push("URL: " + urls[0] + (urls.length > 1 ? " (+" + (urls.length - 1) + ")" : ""));
    }

    const files = extractFilePaths(raw);
    if (files.length) context.push("Files: " + files.slice(0, 4).join(", "));

    if (blocks.length === 1 && blocks[0].length < 200 && opts.tokenSaver) {
      context.push("Snippet: " + blocks[0].split("\n")[0].slice(0, 80));
    } else if (blocks.length && !opts.tokenSaver) {
      context.push("```\n" + blocks.join("\n\n") + "\n```");
    }

    return {
      task: dedupe(taskLead).join(" ").slice(0, 320),
      context: dedupe(context),
      requirements: dedupe(requirements),
      constraints: dedupe(constraints),
      acceptance: dedupe(acceptance),
      symptoms: dedupe(symptoms),
      files: dedupe(files),
      codeBlocks: blocks,
      intent: dedupe(taskLead).join(" ").slice(0, 120) || "Implement requested change",
    };
  }

  function templateExtras(taskType, parsed, mode) {
    const extras = { requirements: [], constraints: [], acceptance: [], context: [] };

    switch (taskType.id) {
      case "bug_fix":
        if (!parsed.acceptance.length) extras.acceptance.push("Bug resolved; regression check passes");
        break;
      case "workflow":
        if (!parsed.files.some((f) => f.includes("workflows"))) {
          extras.requirements.push("Inspect `.github/workflows/*`");
        }
        break;
      case "security":
        if (mode !== "ultra") {
          extras.constraints.push("No secrets in client/static output");
        }
        break;
      case "parser":
        if (mode === "full" || mode === "standard") {
          extras.requirements.push("Define input format, parsing rules, output schema");
          extras.acceptance.push("Edge cases handled; validation included");
        }
        break;
      case "feature":
        if (!parsed.acceptance.length) extras.acceptance.push("Feature works end-to-end per requirements");
        break;
      default:
        break;
    }
    return extras;
  }

  function mergeLists(base, extra) {
    return dedupe([...base, ...(extra || [])]);
  }

  function isTinyTask(parsed, raw) {
    return (
      raw.length < 180 &&
      parsed.requirements.length <= 1 &&
      parsed.constraints.length <= 1 &&
      parsed.context.length <= 1
    );
  }

  function trimToWordBudget(text, maxWords) {
    const words = text.split(/\s+/);
    if (words.length <= maxWords) return text;
    return words.slice(0, maxWords).join(" ") + "…";
  }

  function formatPrompt(parsed, taskType, opts, repoRules, mode) {
    const extras = templateExtras(taskType, parsed, mode);
    const task = parsed.task || parsed.intent || "Implement requested change.";
    const ctx = mergeLists(parsed.context, extras.context);
    const reqs = mergeLists(parsed.requirements, extras.requirements);
    const cons = mergeLists(parsed.constraints, extras.constraints);
    const acc = opts.includeAcceptance
      ? mergeLists(parsed.acceptance, extras.acceptance)
      : parsed.acceptance;
    const files = parsed.files;
    const tiny = isTinyTask(parsed, opts._raw || "") && (mode === "ultra" || mode === "compact");

    const parts = [];

    if (opts.target !== "generic" && mode === "full") {
      parts.push(TARGET_HINTS[opts.target], "");
    }

    parts.push("Task:", task);

    if (!tiny && ctx.length && mode !== "ultra") {
      parts.push("", "Context:");
      ctx.slice(0, mode === "compact" ? 3 : 6).forEach((c) => parts.push("- " + c));
    } else if (ctx.length && mode === "ultra" && ctx.length === 1) {
      parts.push("", "Context:", "- " + ctx[0]);
    }

    if (reqs.length && mode !== "ultra") {
      parts.push("", "Requirements:");
      const limit = mode === "compact" ? 4 : mode === "standard" ? 8 : 12;
      reqs.slice(0, limit).forEach((r) => parts.push("- " + r));
    } else if (reqs.length && mode === "ultra") {
      parts.push("", "Requirements:", "- " + reqs.slice(0, 2).join("; "));
    }

    if (cons.length) {
      parts.push("", "Constraints:");
      const limit = mode === "ultra" ? 3 : mode === "compact" ? 5 : 8;
      cons.slice(0, limit).forEach((c) => parts.push("- " + c));
    }

    if (files.length && (mode === "standard" || mode === "full")) {
      parts.push("", "Files/Areas:");
      files.forEach((f) => parts.push("- " + f));
    }

    if (mode === "full") {
      if (taskType.id === "workflow") {
        parts.push("", "Workflow Notes:", "- Identify failing job/check name", "- Preserve merge/review policy");
      }
      if (taskType.id === "security") {
        parts.push("", "Threat Model:", "- Unauthorized access", "- Secret leakage via static bundle");
      }
      if (taskType.id === "parser") {
        parts.push("", "Parsing:", "- Input format + field mapping", "- Output schema + validation");
      }
    }

    if (acc.length) {
      parts.push("", "Acceptance:");
      const limit = mode === "ultra" ? 2 : mode === "compact" ? 4 : 8;
      acc.slice(0, limit).forEach((a) => parts.push("- " + a));
    }

    if (repoRules.length && mode !== "ultra") {
      parts.push("", "Repo:");
      repoRules.forEach((r) => parts.push("- " + r));
    } else if (repoRules.length && mode === "ultra") {
      parts.push("", "Repo:", "- " + repoRules.slice(0, 2).join("; "));
    }

    let output = parts.join("\n").replace(/\n{3,}/g, "\n\n").trim();

    if (opts.tokenSaver) {
      output = output
        .split("\n")
        .map((l) => cleanFiller(l, true))
        .filter(Boolean)
        .join("\n");
    }

    const budget = MODES[mode];
    if (budget && budget.wordMax) {
      output = trimToWordBudget(output, budget.wordMax);
    }

    return output;
  }

  function runEngine(raw, opts) {
    const taskType = detectTaskType(raw);
    const parsed = parseInput(raw, opts);
    const activeMode = opts.mode === "auto" ? selectAutoMode(raw, parsed, taskType) : opts.mode;
    const repoRules = buildRepoRules(raw, opts.includeRepoRules, opts.includeClaudeMd);

    const outputs = {};
    ["ultra", "compact", "standard", "full"].forEach((m) => {
      const o = { ...opts, _raw: raw };
      outputs[m] = formatPrompt(parsed, taskType, o, repoRules, m);
    });

    const output = outputs[activeMode];
    const removals = analyzeRemovals(raw, output, parsed);

    return { output, outputs, parsed, taskType, activeMode, repoRules, removals };
  }

  function analyzeRemovals(raw, output, parsed) {
    const removals = [];
    const rawLines = splitLines(raw);
    const outLower = output.toLowerCase();

    rawLines.forEach((line) => {
      const cleaned = cleanFiller(line, true);
      if (!cleaned || cleaned.length < 8) return;
      const key = cleaned.toLowerCase().slice(0, 40);
      if (outLower.includes(key.slice(0, 20))) return;

      let reason = "irrelevant";
      if (FILLER_PATTERNS.some((re) => re.test(line)) || VAGUE_PATTERNS.some((re) => re.test(line))) {
        reason = "verbose";
      } else if (
        SYNONYM_GROUPS.some((g) => g.patterns.some((re) => re.test(line))) ||
        parsed.constraints.some((c) => c.toLowerCase().includes(key.slice(0, 15)))
      ) {
        reason = "duplicate";
      } else if (/https?:\/\//.test(line) && parsed.context.some((c) => c.includes("URL:"))) {
        reason = "duplicate";
      }

      removals.push({ text: line.trim(), reason });
    });

    return removals.slice(0, 12);
  }

  function scoreClarity(text) {
    let s = 40;
    if (/^Task:/m.test(text)) s += 20;
    if (/^-\s/m.test(text)) s += Math.min(25, (text.match(/^-\s/gm) || []).length * 4);
    if (!FILLER_PATTERNS.some((re) => re.test(text))) s += 8;
    if (!VAGUE_PATTERNS.some((re) => re.test(text))) s += 12;
    return Math.min(100, s);
  }

  function scoreReadiness(text, parsed, opts) {
    let s = 20;
    if (parsed.task) s += 15;
    if (parsed.files.length) s += 15;
    if (parsed.constraints.length) s += 15;
    if (parsed.requirements.length) s += 10;
    if (/Acceptance:/i.test(text) || parsed.acceptance.length) s += 25;
    return Math.min(100, s);
  }

  function scoreRiskCoverage(text, taskType, parsed) {
    let s = 30;
    if (parsed.constraints.length) s += 20;
    if (/Acceptance:/i.test(text)) s += 20;
    if (taskType.id === "security" && /secret|auth|access/i.test(text)) s += 15;
    if (taskType.id === "workflow" && /workflow|main|merge/i.test(text)) s += 15;
    if (parsed.files.length) s += 10;
    return Math.min(100, s);
  }

  function scoreTokenEfficiency(inTok, outTok) {
    if (!inTok) return 0;
    const ratio = outTok / inTok;
    if (ratio <= 0.38) return 98;
    if (ratio <= 0.5) return 92;
    if (ratio <= 0.7) return Math.round(88 - (ratio - 0.5) * 60);
    if (ratio <= 1) return Math.round(72 - (ratio - 0.7) * 80);
    return Math.max(15, 45 - Math.round((ratio - 1) * 25));
  }

  function computeScores(raw, output, parsed, taskType, opts) {
    const inTok = estimateTokens(raw);
    const outTok = estimateTokens(output);
    const saved = Math.max(0, inTok - outTok);
    const savedPct = inTok ? Math.round((saved / inTok) * 100) : 0;
    const compressionRatio = inTok ? (outTok / inTok).toFixed(2) : "1.00";

    const tokenEfficiency = scoreTokenEfficiency(inTok, outTok);
    const clarity = scoreClarity(output);
    const readiness = scoreReadiness(output, parsed, opts);
    const riskCoverage = scoreRiskCoverage(output, taskType, parsed);
    const overall = Math.round((clarity + tokenEfficiency + readiness + riskCoverage) / 4);

    return {
      clarity,
      tokenEfficiency,
      readiness,
      riskCoverage,
      overall,
      inTok,
      outTok,
      saved,
      savedPct,
      compressionRatio,
    };
  }

  function lintPrompt(output, parsed, raw) {
    const issues = [];
    const wordCount = countWords(output);

    if (wordCount > 650) issues.push({ level: "warn", msg: "Prompt quá dài (" + wordCount + " từ) — cân nhắc Compact/Ultra." });
    if (!/Acceptance:/i.test(output)) issues.push({ level: "err", msg: "Thiếu Acceptance criteria." });
    if (!parsed.constraints.length && !/Constraints:/i.test(output)) {
      issues.push({ level: "warn", msg: "Thiếu Constraints — thêm ràng buộc nếu có." });
    }
    if (!parsed.files.length && raw.length > 250) {
      issues.push({ level: "warn", msg: "Thiếu file/area cần sửa — agent khó định vị." });
    }
    if (VAGUE_PATTERNS.some((re) => re.test(output))) {
      issues.push({ level: "err", msg: "Còn từ mơ hồ (thử xem, nếu được…) — thay bằng mệnh lệnh rõ." });
    }

    const bullets = (output.match(/^-\s+(.+)$/gm) || []).map((b) => b.replace(/^-\s+/, "").toLowerCase());
    const dupes = bullets.filter((b, i) => bullets.indexOf(b) !== i);
    if (dupes.length) issues.push({ level: "warn", msg: "Lặp ý: " + dupes[0].slice(0, 50) });

    const hasNoMerge = /no auto[- ]?merge|không auto/i.test(raw);
    const hasAutoMerge = /\bauto[- ]?merge\b/i.test(output) && !/no auto|không auto/i.test(output);
    if (hasNoMerge && hasAutoMerge) {
      issues.push({ level: "err", msg: "Mâu thuẫn: input cấm auto-merge nhưng output gợi ý auto-merge." });
    }

    const inTok = estimateTokens(raw);
    const outTok = estimateTokens(output);
    if (outTok >= inTok) {
      issues.push({ level: "warn", msg: "Token waste: output ≥ input — chưa nén hiệu quả." });
    }

    if (!issues.length) issues.push({ level: "ok", msg: "Prompt lint pass — sẵn sàng cho coding agent." });
    return issues;
  }

  function improvementTips(scores, parsed) {
    const tips = [];
    if (scores.clarity < 70) tips.push("Dùng Task:/Requirements:/Acceptance: thay câu dài.");
    if (scores.readiness < 70) {
      if (!parsed.files.length) tips.push("Ghi file/path (vd `.github/workflows/qa.yml`).");
      if (!parsed.acceptance.length) tips.push("Bổ sung acceptance — pass khi nào.");
    }
    if (scores.tokenEfficiency < 70) tips.push("Bật Token Saver hoặc chọn Ultra/Compact.");
    if (!parsed.constraints.length) tips.push("Nêu constraint (no main commit, no auto-merge…).");
    return dedupe(tips).slice(0, 4);
  }

  function setStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = "psupport__status" + (type ? " psupport__status--" + type : "");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderBudget(scores) {
    budgetEl.hidden = false;
    budgetEl.innerHTML =
      '<div class="psupport__budget-grid">' +
      '<span><strong>Input tokens:</strong> ~' +
      scores.inTok +
      "</span>" +
      '<span><strong>Output tokens:</strong> ~' +
      scores.outTok +
      "</span>" +
      '<span><strong>Saved:</strong> ' +
      scores.savedPct +
      "%</span>" +
      '<span><strong>Compression ratio:</strong> ' +
      scores.compressionRatio +
      "x</span>" +
      "</div>";
  }

  function renderScores(scores) {
    scoresEl.hidden = false;
    scoresEl.innerHTML =
      '<div class="psupport__score-grid">' +
      scoreItem("Clarity", scores.clarity) +
      scoreItem("Token Efficiency", scores.tokenEfficiency) +
      scoreItem("Implementation Readiness", scores.readiness) +
      scoreItem("Risk Coverage", scores.riskCoverage) +
      scoreItem("Overall", scores.overall, true) +
      "</div>";
  }

  function scoreItem(label, value, wide) {
    const cls = value >= 75 ? "good" : value >= 55 ? "mid" : "low";
    return (
      '<div class="psupport__score psupport__score--' +
      cls +
      (wide ? " psupport__score--wide" : "") +
      '">' +
      '<span class="psupport__score-label">' +
      label +
      "</span>" +
      '<span class="psupport__score-value">' +
      value +
      "</span></div>"
    );
  }

  function renderTips(tips) {
    if (!tips.length) {
      tipsEl.hidden = true;
      return;
    }
    tipsEl.hidden = false;
    tipsEl.innerHTML =
      "<strong>Gợi ý cải thiện</strong><ul>" +
      tips.map((t) => "<li>" + escapeHtml(t) + "</li>").join("") +
      "</ul>";
  }

  function renderLint(issues) {
    lintResultsEl.hidden = false;
    lintResultsEl.innerHTML =
      "<strong>Prompt Lint</strong><ul>" +
      issues
        .map(
          (i) =>
            '<li class="psupport__lint psupport__lint--' +
            i.level +
            '">' +
            escapeHtml(i.msg) +
            "</li>"
        )
        .join("") +
      "</ul>";
  }

  function renderCompareDiff(removals) {
    const diffEl = compareEl.querySelector("[data-psupport-diff]");
    if (!diffEl) return;
    if (!removals.length) {
      diffEl.innerHTML = "<p class='psupport__diff-empty'>Không có phần bị loại đáng kể.</p>";
      return;
    }
    diffEl.innerHTML =
      "<ul class='psupport__diff-list'>" +
      removals
        .map(
          (r) =>
            "<li><span class='psupport__diff-reason'>" +
            r.reason +
            "</span> " +
            escapeHtml(r.text.slice(0, 120)) +
            (r.text.length > 120 ? "…" : "") +
            "</li>"
        )
        .join("") +
      "</ul>";
  }

  function getOptions() {
    return {
      mode: modeEl ? modeEl.value : "auto",
      target: targetEl ? targetEl.value : "grok",
      tokenSaver: tokenSaverEl ? tokenSaverEl.checked : true,
      includeRepoRules: repoRulesEl ? repoRulesEl.checked : true,
      includeClaudeMd: claudeMdEl ? claudeMdEl.checked : false,
      includeAcceptance: acceptanceEl ? acceptanceEl.checked : true,
    };
  }

  function isPlaceholderOutput(text) {
    const t = (text || "").trim();
    return !t || t === OUTPUT_PLACEHOLDER || t === "Generate Prompt để xem kết quả.";
  }

  function getActiveOutputText() {
    const fromMode = modeOutputs[lastActiveMode];
    if (fromMode && !isPlaceholderOutput(fromMode)) return fromMode;
    const fromDom = outputCode ? outputCode.textContent : "";
    return isPlaceholderOutput(fromDom) ? "" : fromDom.trim();
  }

  function setCopyButtonsEnabled(enabled) {
    if (copyPrimaryBtn) copyPrimaryBtn.disabled = !enabled;
    Object.values(copyBtns).forEach((btn) => {
      if (btn) btn.disabled = !enabled;
    });
  }

  function generate(statusMsg) {
    const raw = normalize(inputEl.value);
    if (!raw) {
      setStatus("Nhập yêu cầu trước.", "err");
      setCopyButtonsEnabled(false);
      return;
    }

    const opts = getOptions();
    const result = runEngine(raw, opts);
    const { output, outputs, parsed, taskType, activeMode, removals } = result;

    lastRaw = raw;
    lastParsed = parsed;
    lastActiveMode = activeMode;
    modeOutputs = outputs;
    lastRemovals = removals;

    const scores = computeScores(raw, output, parsed, taskType, opts);
    const tips = improvementTips(scores, parsed);
    const lintIssues = lintPrompt(output, parsed, raw);

    outputCode.textContent = output;
    setCopyButtonsEnabled(true);

    if (taskBadge) {
      taskBadge.textContent = taskType.label;
      taskBadge.hidden = false;
    }
    if (modeBadge) {
      const modeLabel = opts.mode === "auto" ? "Auto → " + MODES[activeMode].label : MODES[activeMode].label;
      modeBadge.textContent = modeLabel;
      modeBadge.hidden = false;
    }

    renderBudget(scores);
    renderScores(scores);
    renderLint(lintIssues);
    renderTips(scores.overall < 75 || scores.readiness < 65 ? tips : []);

    if (compareVisible && compareEl) {
      compareEl.querySelector("[data-psupport-before]").textContent = raw;
      compareEl.querySelector("[data-psupport-after]").textContent = output;
      renderCompareDiff(removals);
    }

    setStatus(statusMsg || "Đã tạo prompt (" + MODES[activeMode].label + ").", "ok");
  }

  function improveNow() {
    generate("Đã cải thiện prompt — bấm Copy Prompt để dùng.");
  }

  function runLintOnly() {
    const raw = normalize(inputEl.value);
    if (!raw) {
      setStatus("Nhập yêu cầu trước.", "err");
      return;
    }
    const opts = getOptions();
    const result = runEngine(raw, opts);
    const issues = lintPrompt(result.output, result.parsed, raw);
    renderLint(issues);
    setStatus("Lint xong.", "ok");
  }

  async function copyText(text, triggerBtn) {
    if (!text || isPlaceholderOutput(text)) {
      setStatus("Cải thiện ngay trước khi copy.", "err");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      setStatus("Đã copy prompt.", "ok");
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setStatus("Đã copy prompt.", "ok");
    }

    if (triggerBtn && typeof triggerBtn.blur === "function") {
      triggerBtn.blur();
    }
    if (window.getSelection) {
      const sel = window.getSelection();
      if (sel && sel.removeAllRanges) sel.removeAllRanges();
    }
  }

  function copyActivePrompt(triggerBtn) {
    const text = getActiveOutputText();
    if (!text) {
      setStatus("Cải thiện ngay trước khi copy.", "err");
      return;
    }
    copyText(text, triggerBtn);
  }

  function toggleCompare() {
    compareVisible = !compareVisible;
    compareEl.hidden = !compareVisible;
    compareBtn.setAttribute("aria-pressed", compareVisible ? "true" : "false");
    if (compareVisible && lastRaw) {
      compareEl.querySelector("[data-psupport-before]").textContent = lastRaw;
      compareEl.querySelector("[data-psupport-after]").textContent = modeOutputs[lastActiveMode] || "";
      renderCompareDiff(lastRemovals);
    }
  }

  if (improveBtn) improveBtn.addEventListener("click", improveNow);
  if (generateBtn) generateBtn.addEventListener("click", () => generate());
  if (lintBtn) lintBtn.addEventListener("click", runLintOnly);
  if (compareBtn) compareBtn.addEventListener("click", toggleCompare);

  if (copyPrimaryBtn) {
    copyPrimaryBtn.addEventListener("click", () => copyActivePrompt(copyPrimaryBtn));
  }

  Object.entries(copyBtns).forEach(([mode, btn]) => {
    if (!btn) return;
    btn.addEventListener("click", () => {
      const text = modeOutputs[mode];
      if (text) copyText(text, btn);
      else setStatus("Cải thiện ngay trước khi copy.", "err");
    });
  });

  inputEl.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      improveNow();
    }
  });
})();