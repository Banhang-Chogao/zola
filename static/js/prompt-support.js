/**
 * Prompt Support — client-side prompt optimizer.
 * Phân tích yêu cầu coding, nhận vai trò AI, rút gọn token, giữ ngữ cảnh kỹ thuật.
 */
(function () {
  "use strict";

  const ROLE_RULES = [
    {
      role: "Security Engineer",
      weight: 1.4,
      patterns: [
        /\b(security|bảo mật|oauth|jwt|xss|csrf|sql injection|encryption|mã hóa|vulnerability|lỗ hổng|penetration|auth(?:entication)?|authorization|csp|helmet|sanitize|token leak|secret|credential)\b/i,
      ],
    },
    {
      role: "DevOps Engineer",
      weight: 1.3,
      patterns: [
        /\b(devops|ci\/?cd|github actions?|workflow|docker|kubernetes|k8s|deploy|pipeline|terraform|ansible|nginx|vercel|aws|gcp|azure|infra|monitoring|helm)\b/i,
      ],
    },
    {
      role: "Mobile Engineer",
      weight: 1.3,
      patterns: [
        /\b(mobile|ios|android|react native|flutter|swift|kotlin|xcode|gradle|app store|play store|expo)\b/i,
      ],
    },
    {
      role: "QA Engineer",
      weight: 1.2,
      patterns: [
        /\b(qa|test(?:ing)?|unit test|e2e|integration test|pytest|jest|playwright|cypress|coverage|assertion|regression|tdd|bdd)\b/i,
      ],
    },
    {
      role: "Frontend Engineer",
      weight: 1,
      patterns: [
        /\b(frontend|front-end|react|vue|angular|svelte|next\.?js|nuxt|css|scss|sass|tailwind|html|jsx|tsx|component|ui|ux|giao diện|responsive|navbar|layout|dom|browser|accessibility|a11y)\b/i,
      ],
    },
    {
      role: "Backend Engineer",
      weight: 1,
      patterns: [
        /\b(backend|back-end|api|rest|graphql|database|sql|postgres|mysql|mongodb|redis|server|endpoint|middleware|orm|fastapi|django|flask|express|node\.?js|python|rust|go\b|java\b|microservice)\b/i,
      ],
    },
  ];

  const FILLER_PATTERNS = [
    /\b(xin hãy|giúp tôi|tôi muốn|bạn có thể|cho tôi|nhờ bạn|làm ơn|cảm ơn|thanks|thank you)\b/gi,
    /\b(please|could you|can you|i want|i need|help me|would you|kindly)\b/gi,
    /\b(được không|nhé|ạ|ơi|nha)\b/gi,
  ];

  const CONSTRAINT_MARKERS = [
    /\b(phải|bắt buộc|không được|chỉ|only|must|should not|don't|do not|required|yêu cầu|constraint|ràng buộc|không dùng|no auto|forbidden|bắt buộc phải)\b/i,
    /^[-*•]\s+/,
    /^\d+[.)]\s+/,
  ];

  const root = document.querySelector("[data-prompt-support]");
  if (!root) return;

  const inputEl = root.querySelector("[data-psupport-input]");
  const outputCode = root.querySelector("[data-psupport-code]");
  const generateBtn = root.querySelector("[data-psupport-generate]");
  const copyBtn = root.querySelector("[data-psupport-copy]");
  const statusEl = root.querySelector("[data-psupport-status]");
  const metaEl = root.querySelector("[data-psupport-meta]");

  let lastPrompt = "";

  function normalize(text) {
    return text.replace(/\r\n/g, "\n").trim();
  }

  function extractCodeBlocks(text) {
    const blocks = [];
    const prose = text.replace(/```[\s\S]*?```/g, (block) => {
      blocks.push(block.trim());
      return "\n";
    });
    return { prose, blocks };
  }

  function cleanFiller(text) {
    let out = text;
    FILLER_PATTERNS.forEach((re) => {
      out = out.replace(re, " ");
    });
    return out.replace(/\s{2,}/g, " ").trim();
  }

  function splitSentences(text) {
    return text
      .split(/\n+/)
      .flatMap((line) => line.split(/(?<=[.!?])\s+/))
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function isConstraintLine(line) {
    return CONSTRAINT_MARKERS.some((re) => re.test(line));
  }

  function compressLine(line) {
    let s = cleanFiller(line);
    s = s.replace(/^[-*•]\s+/, "");
    s = s.replace(/^\d+[.)]\s+/, "");
    s = s.replace(/\s+/g, " ").trim();
    if (!s) return "";
    if (!/[.!?]$/.test(s) && s.length > 20) s += ".";
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function dedupeLines(lines) {
    const seen = new Set();
    const out = [];
    lines.forEach((line) => {
      const key = line.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        out.push(line);
      }
    });
    return out;
  }

  function detectRole(text) {
    const scores = {};
    ROLE_RULES.forEach(({ role, weight, patterns }) => {
      let score = 0;
      patterns.forEach((re) => {
        const matches = text.match(new RegExp(re.source, "gi"));
        if (matches) score += matches.length * weight;
      });
      if (score > 0) scores[role] = score;
    });

    const fe = scores["Frontend Engineer"] || 0;
    const be = scores["Backend Engineer"] || 0;
    if (fe >= 2 && be >= 2) return "Fullstack Engineer";

    const ranked = Object.entries(scores).sort((a, b) => b[1] - a[1]);
    if (ranked.length) return ranked[0][0];
    return "Fullstack Engineer";
  }

  function buildTask(prose, codeBlocks) {
    const lines = splitSentences(prose);
    const taskLines = [];
    const constraintLines = [];

    lines.forEach((raw) => {
      const line = raw.trim();
      if (!line) return;
      if (isConstraintLine(line)) {
        const c = compressLine(line);
        if (c) constraintLines.push(c);
      } else {
        const t = compressLine(line);
        if (t) taskLines.push(t);
      }
    });

    let task = dedupeLines(taskLines).join("\n");
    if (codeBlocks.length) {
      const snippet = codeBlocks
        .map((b) => b.replace(/^```\w*\n?/, "").replace(/```$/, "").trim())
        .filter(Boolean)
        .join("\n\n");
      if (snippet) {
        task = task ? task + "\n\n```\n" + snippet + "\n```" : "```\n" + snippet + "\n```";
      }
    }

    return {
      task: task.trim(),
      constraints: dedupeLines(constraintLines),
    };
  }

  function formatPrompt(role, task, constraints) {
    const parts = [
      "[ROLE]: " + role,
      "",
      "[TASK]:",
      task || "(Mô tả mục tiêu và chức năng cần thực hiện.)",
    ];

    if (constraints.length) {
      parts.push("", "[CONSTRAINTS]:");
      constraints.forEach((c) => parts.push("- " + c.replace(/\.$/, "")));
    }

    parts.push("", "[CODE STYLE]:", "Clean, pretty");
    return parts.join("\n");
  }

  function estimateTokens(text) {
    return Math.ceil(text.length / 4);
  }

  function setStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = "psupport__status" + (type ? " psupport__status--" + type : "");
  }

  function generate() {
    const raw = normalize(inputEl.value);
    if (!raw) {
      setStatus("Nhập yêu cầu trước.", "err");
      copyBtn.disabled = true;
      return;
    }

    const { prose, blocks } = extractCodeBlocks(raw);
    const role = detectRole(raw);
    const { task, constraints } = buildTask(prose, blocks);
    const prompt = formatPrompt(role, task, constraints);

    lastPrompt = prompt;
    outputCode.textContent = prompt;
    copyBtn.disabled = false;

    const inTok = estimateTokens(raw);
    const outTok = estimateTokens(prompt);
    const saved = Math.max(0, inTok - outTok);
    metaEl.hidden = false;
    metaEl.textContent = "~" + outTok + " tok (−" + saved + ")";
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

  generateBtn.addEventListener("click", generate);
  copyBtn.addEventListener("click", copyPrompt);

  inputEl.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      generate();
    }
  });
})();