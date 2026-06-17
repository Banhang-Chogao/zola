/**
 * Prompt Support v2 — client-side prompt optimizer for AI coding agents.
 * Compact, professional, token-efficient prompts with task-type templates.
 */
(function () {
  "use strict";

  const REPO_SLUG = "Banhang-Chogao/zola";
  const REPO_RULES_DEFAULT = [
    "Create a separate branch.",
    "Open a PR for review.",
    "Do not commit directly to `main`.",
    "Do not auto-merge unless explicitly allowed.",
    "Run `zola build` before finalizing.",
    "Update `CLAUDE.md` if a reusable lesson/rule is learned.",
  ];

  const FILLER_PATTERNS = [
    /\b(xin hãy|giúp tôi|tôi muốn|bạn có thể|cho tôi|nhờ bạn|làm ơn|cảm ơn|thanks|thank you)\b/gi,
    /\b(please|could you|can you|i want|i need|help me|would you|kindly|just|maybe|perhaps)\b/gi,
    /\b(được không|nhé|ạ|ơi|nha|gấp|giúp coi|kiểm tra giúp|thử xem|hình như|có vẻ)\b/gi,
    /\b(i think|i feel|it seems|looks like|probably)\b/gi,
  ];

  const VAGUE_PATTERNS = [
    /\b(thử xem|có thể|maybe|perhaps|hình như|có vẻ|kiểm tra giúp)\b/gi,
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
  const generateBtn = root.querySelector("[data-psupport-generate]");
  const copyBtn = root.querySelector("[data-psupport-copy]");
  const compareBtn = root.querySelector("[data-psupport-compare]");
  const statusEl = root.querySelector("[data-psupport-status]");
  const metaEl = root.querySelector("[data-psupport-meta]");
  const scoresEl = root.querySelector("[data-psupport-scores]");
  const compareEl = root.querySelector("[data-psupport-compare-panel]");
  const tipsEl = root.querySelector("[data-psupport-tips]");
  const taskBadge = root.querySelector("[data-psupport-task-type]");

  const modeEl = root.querySelector("[data-psupport-mode]");
  const targetEl = root.querySelector("[data-psupport-target]");
  const tokenSaverEl = root.querySelector("[data-psupport-token-saver]");
  const repoRulesEl = root.querySelector("[data-psupport-repo-rules]");
  const claudeMdEl = root.querySelector("[data-psupport-claude-md]");
  const acceptanceEl = root.querySelector("[data-psupport-acceptance]");

  let lastPrompt = "";
  let lastRaw = "";
  let compareVisible = false;

  function normalize(text) {
    return text.replace(/\r\n/g, "\n").trim();
  }

  function estimateTokens(text) {
    return Math.max(0, Math.ceil((text || "").length / 4));
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

  function blocksDirectMain(text) {
    return /\b(không|do not|don't|no)\s+(commit|push|merge).{0,20}main/i.test(text);
  }

  function buildRepoRules(text, includeRepo, includeClaudeMd) {
    if (!includeRepo) return [];
    const rules = [...REPO_RULES_DEFAULT];
    let out = rules;
    if (wantsAutoMerge(text)) {
      out = out.filter((r) => !/auto-merge unless/i.test(r));
    }
    if (!includeClaudeMd) {
      out = out.filter((r) => !/CLAUDE\.md/i.test(r));
    }
    return out;
  }

  function parseInput(raw, opts) {
    const { prose, blocks } = extractCodeBlocks(raw);
    const lines = splitLines(prose);
    const requirements = [];
    const constraints = [];
    const acceptance = [];
    const context = [];
    const symptoms = [];
    let taskLead = [];

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
    if (urls.length && opts.tokenSaver) {
      context.push("URL: " + urls[0] + (urls.length > 1 ? " (+" + (urls.length - 1) + " more)" : ""));
    } else if (urls.length) {
      urls.forEach((u) => context.push(u));
    }

    const files = extractFilePaths(raw);
    if (blocks.length && !opts.tokenSaver) {
      context.push("```\n" + blocks.join("\n\n") + "\n```");
    } else if (blocks.length === 1 && blocks[0].length < 200) {
      context.push("Snippet: " + blocks[0].split("\n")[0]);
    }

    return {
      task: dedupe(taskLead).join(" ").slice(0, 280),
      context: dedupe(context),
      requirements: dedupe(requirements),
      constraints: dedupe(constraints),
      acceptance: dedupe(acceptance),
      symptoms: dedupe(symptoms),
      files: dedupe(files),
      codeBlocks: blocks,
    };
  }

  function templateExtras(taskType, parsed) {
    const extras = { requirements: [], constraints: [], acceptance: [] };

    switch (taskType.id) {
      case "bug_fix":
        if (parsed.symptoms.length && !parsed.context.length) {
          extras.context = parsed.symptoms;
        }
        if (!parsed.acceptance.length) {
          extras.acceptance.push("Bug resolved; regression check passes");
        }
        break;
      case "workflow":
        if (!parsed.files.some((f) => f.includes("workflows"))) {
          extras.requirements.push("Inspect `.github/workflows/*`");
        }
        if (!parsed.constraints.some((c) => /auto-merge|main/i.test(c))) {
          extras.constraints.push("Do not auto-merge unless explicitly allowed");
        }
        break;
      case "security":
        extras.requirements.push("No secrets in client/static output");
        extras.constraints.push("Access control enforced server-side where applicable");
        break;
      case "parser":
        extras.requirements.push("Define input format, parsing rules, output schema");
        extras.acceptance.push("Edge cases handled; validation included");
        break;
      case "feature":
        if (!parsed.acceptance.length) {
          extras.acceptance.push("Feature works end-to-end per requirements");
        }
        break;
      default:
        break;
    }
    return extras;
  }

  function mergeLists(base, extra) {
    return dedupe([...base, ...extra]);
  }

  function isSimpleTask(parsed, raw) {
    return (
      raw.length < 220 &&
      parsed.requirements.length <= 2 &&
      parsed.constraints.length <= 2 &&
      parsed.files.length <= 2
    );
  }

  function section(title, items, bullet) {
    if (!items.length) return [];
    const out = [title];
    items.forEach((item) => out.push((bullet ? "- " : "") + item));
    return out;
  }

  function formatCompact(parsed, taskType, opts, repoRules) {
    const lines = ["Task:", parsed.task || "Implement requested change."];
    const reqs = mergeLists(parsed.requirements, templateExtras(taskType, parsed).requirements);
    const acc = opts.includeAcceptance
      ? mergeLists(parsed.acceptance, templateExtras(taskType, parsed).acceptance)
      : parsed.acceptance;

    if (reqs.length) {
      lines.push("", "Requirements:");
      reqs.forEach((r) => lines.push("- " + r));
    }
    if (parsed.constraints.length) {
      lines.push("", "Constraints:");
      parsed.constraints.forEach((c) => lines.push("- " + c));
    }
    if (acc.length) {
      lines.push("", "Acceptance:");
      acc.forEach((a) => lines.push("- " + a));
    }
    if (repoRules.length) {
      lines.push("", "Repo:");
      repoRules.slice(0, 4).forEach((r) => lines.push("- " + r));
    }
    return lines.join("\n");
  }

  function formatStructured(parsed, taskType, opts, repoRules, mode) {
    const extras = templateExtras(taskType, parsed);
    const task = parsed.task || "Implement requested change.";
    const ctx = mergeLists(parsed.context, extras.context || []);
    const reqs = mergeLists(parsed.requirements, extras.requirements);
    const cons = mergeLists(parsed.constraints, extras.constraints);
    const files = parsed.files;
    const acc = opts.includeAcceptance
      ? mergeLists(parsed.acceptance, extras.acceptance)
      : parsed.acceptance;

    const parts = [];
    if (opts.target !== "generic" && mode === "full") {
      parts.push(TARGET_HINTS[opts.target] || "", "");
    }

    parts.push("# Task", task, "");

    if (ctx.length) {
      parts.push("# Context");
      ctx.forEach((c) => parts.push("- " + c));
      parts.push("");
    }

    if (taskType.id === "bug_fix" && parsed.symptoms.length) {
      parts.push("# Symptom");
      parsed.symptoms.forEach((s) => parts.push("- " + s));
      parts.push("");
    }

    if (reqs.length) {
      parts.push("# Requirements");
      reqs.forEach((r) => parts.push("- " + r));
      parts.push("");
    }

    if (cons.length) {
      parts.push("# Constraints");
      cons.forEach((c) => parts.push("- " + c));
      parts.push("");
    }

    if (files.length) {
      parts.push("# Files/Areas");
      files.forEach((f) => parts.push("- " + f));
      parts.push("");
    }

    if (mode === "full") {
      if (taskType.id === "workflow") {
        parts.push("# Workflow Notes");
        parts.push("- Identify failing job/check name");
        parts.push("- Preserve intended merge/review policy");
        parts.push("");
      }
      if (taskType.id === "security") {
        parts.push("# Threat Model");
        parts.push("- Unauthorized access to protected resources");
        parts.push("- Secret leakage via static/client bundle");
        parts.push("");
      }
      if (taskType.id === "parser") {
        parts.push("# Parsing");
        parts.push("- Input format + field mapping");
        parts.push("- Output schema + validation rules");
        parts.push("");
      }
    }

    if (acc.length) {
      parts.push("# Acceptance Criteria");
      acc.forEach((a) => parts.push("- " + a));
      parts.push("");
    }

    if (repoRules.length) {
      parts.push("# Repo Rules");
      repoRules.forEach((r) => parts.push("- " + r));
      parts.push("");
    }

    if (opts.includeClaudeMd && !repoRules.some((r) => /CLAUDE\.md/i.test(r))) {
      parts.push("# Learning");
      parts.push("- Append reusable rule to `CLAUDE.md` if applicable");
      parts.push("");
    }

    return parts.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function buildPrompt(raw, options) {
    const parsed = parseInput(raw, options);
    const taskType = detectTaskType(raw);
    const repoRules = buildRepoRules(raw, options.includeRepoRules, options.includeClaudeMd);
    const simple = isSimpleTask(parsed, raw) && options.mode !== "full";

    let output;
    if (options.mode === "compact" || simple) {
      output = formatCompact(parsed, taskType, options, repoRules);
    } else {
      output = formatStructured(parsed, taskType, options, repoRules, options.mode);
    }

    if (options.tokenSaver) {
      output = output
        .split("\n")
        .map((l) => cleanFiller(l, true))
        .filter(Boolean)
        .join("\n");
    }

    return { output, parsed, taskType };
  }

  function scoreClarity(text) {
    let s = 40;
    if (/^#\s/m.test(text) || /^Task:/m.test(text)) s += 15;
    if (/^-\s/m.test(text)) s += Math.min(25, (text.match(/^-\s/gm) || []).length * 4);
    if (!FILLER_PATTERNS.some((re) => re.test(text))) s += 10;
    if (!VAGUE_PATTERNS.some((re) => re.test(text))) s += 10;
    return Math.min(100, s);
  }

  function scoreReadiness(text, parsed, opts) {
    let s = 20;
    if (parsed.task) s += 15;
    if (parsed.files.length) s += 15;
    if (parsed.constraints.length) s += 15;
    if (parsed.requirements.length) s += 15;
    if ((opts.includeAcceptance && /acceptance/i.test(text)) || parsed.acceptance.length) s += 20;
    return Math.min(100, s);
  }

  function scoreTokenEfficiency(inTok, outTok) {
    if (!inTok) return 0;
    const ratio = outTok / inTok;
    if (ratio <= 0.45) return 95;
    if (ratio <= 0.7) return Math.round(90 - (ratio - 0.45) * 40);
    if (ratio <= 1) return Math.round(75 - (ratio - 0.7) * 80);
    return Math.max(20, 50 - Math.round((ratio - 1) * 30));
  }

  function computeScores(raw, output, parsed, opts) {
    const inTok = estimateTokens(raw);
    const outTok = estimateTokens(output);
    const tokenEfficiency = scoreTokenEfficiency(inTok, outTok);
    const clarity = scoreClarity(output);
    const readiness = scoreReadiness(output, parsed, opts);
    const quality = Math.round((tokenEfficiency + clarity + readiness) / 3);
    return { quality, tokenEfficiency, clarity, readiness, inTok, outTok };
  }

  function improvementTips(scores, parsed) {
    const tips = [];
    if (scores.clarity < 70) tips.push("Thêm section rõ (# Task, # Requirements) hoặc bullet thay câu dài.");
    if (scores.readiness < 70) {
      if (!parsed.files.length) tips.push("Ghi file/path khu vực cần sửa (vd `.github/workflows/qa.yml`).");
      if (!parsed.acceptance.length) tips.push("Bổ sung acceptance criteria — pass khi nào.");
    }
    if (scores.tokenEfficiency < 70) tips.push("Bật Token Saver hoặc rút gọn mô tả; bỏ câu xã giao.");
    if (!parsed.constraints.length) tips.push("Nêu rõ constraint (không auto-merge, không push main, …).");
    return dedupe(tips).slice(0, 4);
  }

  function setStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = "psupport__status" + (type ? " psupport__status--" + type : "");
  }

  function renderScores(scores) {
    scoresEl.hidden = false;
    scoresEl.innerHTML =
      '<div class="psupport__score-grid">' +
      scoreItem("Prompt Quality", scores.quality) +
      scoreItem("Token Efficiency", scores.tokenEfficiency) +
      scoreItem("Clarity", scores.clarity) +
      scoreItem("Implementation Readiness", scores.readiness) +
      "</div>";
  }

  function scoreItem(label, value) {
    const cls = value >= 75 ? "good" : value >= 55 ? "mid" : "low";
    return (
      '<div class="psupport__score psupport__score--' +
      cls +
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

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function getOptions() {
    return {
      mode: modeEl ? modeEl.value : "standard",
      target: targetEl ? targetEl.value : "grok",
      tokenSaver: tokenSaverEl ? tokenSaverEl.checked : true,
      includeRepoRules: repoRulesEl ? repoRulesEl.checked : true,
      includeClaudeMd: claudeMdEl ? claudeMdEl.checked : false,
      includeAcceptance: acceptanceEl ? acceptanceEl.checked : true,
    };
  }

  function generate() {
    const raw = normalize(inputEl.value);
    if (!raw) {
      setStatus("Nhập yêu cầu trước.", "err");
      copyBtn.disabled = true;
      return;
    }

    const opts = getOptions();
    const { output, parsed, taskType } = buildPrompt(raw, opts);
    const scores = computeScores(raw, output, parsed, opts);
    const tips = improvementTips(scores, parsed);

    lastPrompt = output;
    lastRaw = raw;
    outputCode.textContent = output;
    copyBtn.disabled = false;

    if (taskBadge) {
      taskBadge.textContent = taskType.label;
      taskBadge.hidden = false;
    }

    metaEl.hidden = false;
    metaEl.textContent =
      "in ~" +
      scores.inTok +
      " → out ~" +
      scores.outTok +
      " tok (−" +
      Math.max(0, scores.inTok - scores.outTok) +
      ")";

    renderScores(scores);
    renderTips(scores.quality < 75 || scores.readiness < 65 ? tips : []);

    if (compareVisible && compareEl) {
      compareEl.querySelector("[data-psupport-before]").textContent = raw;
      compareEl.querySelector("[data-psupport-after]").textContent = output;
    }

    setStatus("Đã tạo prompt.", "ok");
  }

  async function copyPrompt() {
    if (!lastPrompt) return;
    try {
      await navigator.clipboard.writeText(lastPrompt);
      setStatus("Đã copy.", "ok");
    } catch {
      const ta = document.createElement("textarea");
      ta.value = lastPrompt;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setStatus("Đã copy.", "ok");
    }
  }

  function toggleCompare() {
    compareVisible = !compareVisible;
    compareEl.hidden = !compareVisible;
    compareBtn.setAttribute("aria-pressed", compareVisible ? "true" : "false");
    if (compareVisible && lastRaw) {
      compareEl.querySelector("[data-psupport-before]").textContent = lastRaw;
      compareEl.querySelector("[data-psupport-after]").textContent = lastPrompt || "";
    }
  }

  generateBtn.addEventListener("click", generate);
  copyBtn.addEventListener("click", copyPrompt);
  compareBtn.addEventListener("click", toggleCompare);

  inputEl.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      generate();
    }
  });
})();