---
name: ai-content-verifier
description: Detect AI-generated text, analyze content credibility (credible/suspicious/fabricated), and verify resource accessibility (URLs, citations, package names). Use when users want to check if text is AI-written, verify facts in AI-generated content, validate links and references, or assess the trustworthiness of generated content.
---

# AI Content Verifier

Detect AI-generated text, analyze content credibility, and verify resource accessibility.

## When to Use This Skill

Use this skill when the user:

- Asks "is this text AI-generated?" or "was this written by ChatGPT/Claude?"
- Wants to verify facts or claims in AI-generated content
- Wants to check if links, citations, or references in text are real and accessible
- Requests a credibility analysis of any text content
- Mentions "AI detection", "fact check", "verify content", "check if real"
- Wants to audit AI-generated documentation, reports, or research
- Needs to distinguish credible vs fabricated content in AI outputs

## Capabilities

1. **AI Generation Detection** — Determine if text is AI-generated with confidence score
2. **Content Credibility Analysis** — Extract and classify claims as credible/suspicious/fabricated
3. **Resource Accessibility Verification** — Check if URLs, DOIs, packages are real and accessible
4. **Layered Analysis** — Quick scan (default) or deep verification mode

## Input Methods

The skill accepts text via three methods:

| Method | How to Use |
|--------|------------|
| Direct paste | User pastes text directly in the message |
| File path | User provides a local file path (e.g., `/path/to/file.md`) |
| URL | User provides a web URL (use `webfetch` to retrieve) |

If input is a file path, read the file first. If input is a URL, use `webfetch` to retrieve the content first.

## Analysis Pipeline

Execute the following three stages in order. Each stage builds on the previous.

### Stage 1: AI Generation Detection

**Step 1.1: Heuristic Signal Analysis**

Scan the text for these AI-typical patterns. Count occurrences and note locations.

| Signal | What to Look For | Weight |
|--------|-----------------|--------|
| Cliché phrases | "在当今时代", "值得注意的是", "综上所述", "总而言之", "delve into", "it's worth noting", "in today's digital age", "landscape", "leveraging", "game-changer", "robust", "cutting-edge" | High |
| Format consistency | Overly uniform list formatting, paragraph lengths within ±10% of each other, perfect heading hierarchy | Medium |
| Flat tone | No slang, no personal anecdotes, no emotional variation, no humor | Medium |
| Redundant modifiers | Excessive use of "comprehensive", "significant", "crucial", "innovative", "seamless" | Medium |
| Template structure | Every paragraph starts with a topic sentence, rigid "intro-body-conclusion" pattern | Low |
| Low information density | Appears detailed but lacks specific numbers, dates, first-hand experience, or unique insights | High |
| Hedging overload | "It's important to note", "As mentioned earlier", "This is a complex topic" | Medium |

Compute a heuristic score (0-100) based on the density and weight of detected signals.

**Step 1.2: LLM Reasoning Analysis**

Analyze the text using your own reasoning. For each paragraph or section:

1. List evidence suggesting AI generation
2. List evidence suggesting human writing
3. Note writing style markers (vocabulary level, sentence structure variation, personal voice)

Provide an LLM judgment score (0-100) for AI generation likelihood.

**Step 1.3: Combined Score**

```
Final AI Confidence = 0.4 × Heuristic Score + 0.6 × LLM Judgment Score
```

Classification:
- **>80%**: Highly Suspected AI-Generated
- **50-80%**: Possibly Contains AI-Generated Content
- **<50%**: Likely Human-Written

### Stage 2: Content Credibility Analysis

**Step 2.1: Extract Claims**

Identify and extract all verifiable claims from the text. Classify each by type:

| Claim Type | Examples |
|------------|----------|
| Data/Statistics | "500 million users worldwide", "95% accuracy rate" |
| Event/Timeline | "OpenAI released GPT-4 in 2023" |
| Causal relationship | "Policy X led to outcome Y" |
| Attribution/Citation | "According to a Gartner report..." |
| Definition/Concept | "X is a technology used for Y" |
| Executable instruction | "Run `pip install xxx` to install" |
| Existence claim | "The openai.ContentVerifier module provides..." |

**Step 2.2: Classify Each Claim**

For each extracted claim, assign one of these labels:

| Label | Meaning | Criteria |
|-------|---------|----------|
| ✅ Credible | Verified as true | Matches known facts or common knowledge |
| ⚠️ Suspicious | Cannot confirm | Plausible but unverifiable with available info |
| ❌ Fabricated | Confirmed false | Contradicts known facts or references non-existent things |
| ❓ Unknown | Insufficient info | Not enough context to judge |

**Step 2.3: Verification Method**

- **Quick mode**: Use your own knowledge to judge each claim. Note that this may be inaccurate for recent events.
- **Deep mode**: For each Suspicious claim, use `websearch` to search for confirming or contradicting evidence. Report the search results and updated classification.

### Stage 3: Resource Accessibility Verification

**Step 3.1: Extract Resources**

Scan the text for:

- HTTP/HTTPS URLs
- DOI identifiers (format: `10.XXXX/...`)
- File paths
- Package/library names (in install commands like `pip install X`, `npm install Y`)

**Step 3.2: Verify Each Resource**

Use the verifier script for batch parallel verification:

```bash
python scripts/verifier.py --text "<input_text>"
```

If the text contains quotes or special characters, save it to a temporary file first and use the file path:
```bash
python scripts/verifier.py /path/to/temp.txt
```

Or if the input is already a file:
```bash
python scripts/verifier.py /path/to/file.md
```

The script extracts and verifies URLs, DOIs, and packages in parallel, returning JSON results. Capture stdout (JSON) and ignore stderr logs. Parse the JSON output to get verification results for each resource. Example JSON structure:
```json
{
  "summary": { "urls_found": N, "urls_accessible": M, ... },
  "urls": [ { "url": "...", "accessible": true/false, ... } ],
  "dois": [ ... ],
  "packages": { "pip": [...], "npm": [...] }
}
```

If the script fails (e.g., missing dependencies like `httpx`), fall back to manual verification:

For each extracted resource:
| Resource Type | Verification Method |
|---------------|-------------------|
| HTTP/HTTPS URL | Use `webfetch` to check accessibility. Record HTTP status. |
| DOI | Construct URL `https://doi.org/{DOI}` and use `webfetch` |
| Package name (pip) | Use `webfetch` on `https://pypi.org/project/{name}/` |
| Package name (npm) | Use `webfetch` on `https://www.npmjs.com/package/{name}` |
| File path | Check if path exists on local system (for local files only) |

**Step 3.3: Cross-reference Content**

For accessible URLs, compare the referenced content with what the text claims. Note any discrepancies.

## Report Output

Generate a structured Markdown report using the template below. Output the report directly to the user.

### Report Template

```markdown
# 🔍 AI Content Verification Report

## 📊 Summary

| Metric | Result |
|--------|--------|
| AI Generation Probability | {score}% {classification} |
| Total Claims Analyzed | {count} |
| ✅ Credible | {count} |
| ⚠️ Suspicious | {count} |
| ❌ Fabricated | {count} |
| 🔗 Resources Checked | {accessible}/{total} accessible |

## 🤖 AI Detection Details

**Confidence: {score}%** — {classification}

**Detected AI Signals:**
- {signal_1}: {details}
- {signal_2}: {details}
- ...

**Human-like Signals (if any):**
- {signal_1}: {details}
- ...

## ⚠️ Suspicious Claims

For each suspicious claim:
1. "{claim text}"
   → Reason: {why it's suspicious}
   → {Deep mode: websearch verification result if available}

## ❌ Fabricated Content

For each fabricated claim:
1. "{claim text}"
   → Evidence: {why it's confirmed false}

## 🔗 Resource Verification

| Resource | Status | Notes |
|----------|--------|-------|
| {url/package} | ✅ Accessible / ❌ Inaccessible / ⚠️ Content mismatch | {details} |

## 📝 Recommendations

- {recommendation_1}
- {recommendation_2}
- ...

## ⚠️ Disclaimer

This analysis is probabilistic and for reference only. AI detection is not 100% accurate. False positives and false negatives may occur. This does not constitute a final judgment on content authenticity.
```

## Mode Selection

- **Quick mode** (default): Triggered by "analyze", "check", "scan", "快速", "分析"
  - Stage 1: Full heuristic + LLM analysis
  - Stage 2: Extract claims, classify using own knowledge only
  - Stage 3: Batch URL accessibility check

- **Deep mode**: Triggered by "deep verify", "detailed analysis", "深度验证", "详细分析"
  - Stage 1: Full analysis
  - Stage 2: Extract claims + `websearch` verification for each suspicious claim
  - Stage 3: URL accessibility + content cross-reference

## Error Handling

| Scenario | Response |
|----------|----------|
| Empty input | Prompt: "Please provide text content to analyze." |
| Text too short (<50 chars) | Proceed but note: "Short text — AI detection accuracy is limited." |
| URL inaccessible | Mark as "Inaccessible" with status code |
| websearch fails | Fall back to own knowledge, label as "Unverified externally" |
| LLM output malformed | Retry once, then output raw analysis |

## Limitations (Always Include in Report Disclaimer)

1. AI detection is probabilistic — no tool guarantees 100% accuracy
2. LLM knowledge has a cutoff date — recent events may be inaccurate
3. Web search results are not authoritative sources
4. Heavily edited AI text may evade detection
5. Very short texts (<100 words) have low detection reliability

## Tags

#ai-detection #fact-checking #content-verification #credibility #hallucination #link-checker #text-analysis #safety #trust
