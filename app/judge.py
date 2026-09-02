import os
import json
import re
import logging
import google.generativeai as genai

logger = logging.getLogger("judge")

PROMPT_TEMPLATE = """You are an expert venture analyst evaluating whether a company is a high-value potential customer or strategic partner for an AI automation agency.

Analyze the evidence gathered from multiple independent intelligence signals (HTTP telemetry, Playwright browser rendering, domain metadata).

Company Name: {company_name}
Website URL: {website}

Signal 1 (HTTP Telemetry):
{signal_http}

Signal 2 (Playwright Browser Rendered Content):
{signal_browser}

Signal 3 (Domain & Protocol Security):
{signal_domain}

Evaluation Criteria:
1. Active Reachability & Operational Status: Is the site accessible, live, and functional?
2. Product & Value Proposition: Does the rendered content show an active business, product, or software/tech service?
3. Strategic Fit: Is this company a suitable fit for enterprise AI automation / AI agent solutions?

Perform deep evidence-based reasoning. Compare the signals. Do NOT simply summarize the website text.

Respond ONLY with a valid JSON object matching this exact schema (no markdown, no backticks, no trailing text):
{{
  "fit": true or false,
  "confidence": a float between 0.0 and 1.0,
  "follow_up_question": "One specific, highly targeted discovery question to ask this company's leadership next",
  "reasoning": "2-3 sentences of clear reasoning directly connecting the evidence signals to your fit decision"
}}
"""


def judge_company(company_name: str, website: str, signal_http: str, signal_browser: str, signal_domain: str = "") -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    def _heuristic_verdict():
        is_http_ok = "status=200" in signal_http or "status=3" in signal_http
        has_browser_content = "title=" in signal_browser and "browser_error" not in signal_browser
        fit = is_http_ok and has_browser_content
        confidence = 0.85 if fit else 0.40
        followup = (
            f"What specific workflow or automation bottleneck is {company_name} prioritizing this quarter?"
            if fit else f"Is {company_name}'s website currently undergoing maintenance or domain migration?"
        )
        reasoning = (
            f"HTTP status and Playwright browser rendering confirmed {company_name} is active online with accessible content."
            if fit else f"Signals indicate reachability or browser rendering issues for {company_name} ({website})."
        )
        return {
            "fit": fit,
            "confidence": confidence,
            "follow_up_question": followup,
            "reasoning": reasoning
        }

    if not api_key:
        logger.warning(f"No GEMINI_API_KEY configured. Using heuristic fallback evaluation for {company_name}.")
        return _heuristic_verdict()

    try:
        genai.configure(api_key=api_key)

        model_names = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
        ]

        prompt = PROMPT_TEMPLATE.format(
            company_name=company_name,
            website=website,
            signal_http=signal_http,
            signal_browser=signal_browser,
            signal_domain=signal_domain or "N/A"
        )

        last_error = None
        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                text = response.text.strip()

                # Clean markdown fences if model outputs them despite prompt
                text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
                text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE).strip()

                data = json.loads(text)

                return {
                    "fit": bool(data.get("fit", False)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "follow_up_question": str(data.get("follow_up_question", "What are your top automation priorities?")),
                    "reasoning": str(data.get("reasoning", f"Evaluated by Gemini ({m_name})."))
                }
            except Exception as model_err:
                last_error = model_err
                logger.warning(f"Gemini model '{m_name}' error for {company_name}: {model_err}")
                continue

        # If all models failed (e.g. quota limit), fall back to heuristic
        logger.warning(f"All Gemini models exhausted for {company_name} ({last_error}). Falling back to heuristic judgment.")
        fallback = _heuristic_verdict()
        fallback["reasoning"] += f" (LLM quota fallback: {type(last_error).__name__})"
        return fallback

    except Exception as e:
        logger.error(f"LLM judgment failed for {company_name}: {e}")
        return _heuristic_verdict()

