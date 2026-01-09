import json
import re
from typing import Any, Dict

from core.llm_client import ollama_generate
from core import prompts


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON found")
    return m.group(0)


def _ensure_list_of_strings(x: Any, max_items: int = 8) -> list[str]:
    if not isinstance(x, list):
        return []
    out: list[str] = []
    for item in x[:max_items]:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _sanitize_profile_shadow(obj: Dict[str, Any]) -> Dict[str, Any]:
    profile = obj.get("profile", {}) if isinstance(obj.get("profile"), dict) else {}
    shadow = obj.get("shadow", {}) if isinstance(obj.get("shadow"), dict) else {}

    return {
        "profile": {
            "archetype": str(profile.get("archetype", "")).strip()[:80],
            "traits": _ensure_list_of_strings(profile.get("traits")),
            "motivations": _ensure_list_of_strings(profile.get("motivations")),
            "blind_spots": _ensure_list_of_strings(profile.get("blind_spots")),
        },
        "shadow": {
            "name": str(shadow.get("name", "")).strip()[:60],
            "title": str(shadow.get("title", "")).strip()[:80],
            "description": str(shadow.get("description", "")).strip()[:600],
            "dominant_fear": str(shadow.get("dominant_fear", "")).strip()[:160],
            "self_sabotage_pattern": _ensure_list_of_strings(shadow.get("self_sabotage_pattern")),
        },
    }


def _sanitize_tribunal(obj: Dict[str, Any]) -> Dict[str, Any]:
    tribunal = obj.get("tribunal", []) if isinstance(obj.get("tribunal"), list) else []
    trajectory = obj.get("trajectory", {}) if isinstance(obj.get("trajectory"), dict) else {}
    reflection = obj.get("reflection", {}) if isinstance(obj.get("reflection"), dict) else {}

    cleaned_tribunal = []
    for line in tribunal[:10]:
        if isinstance(line, dict):
            speaker = str(line.get("speaker", "")).strip()
            text = str(line.get("text", "")).strip()
            if speaker and text:
                cleaned_tribunal.append({"speaker": speaker, "text": text})

    if not cleaned_tribunal:
        cleaned_tribunal = [
            {"speaker": "Analyst", "text": "Tradeoffs detected, but structure returned incomplete."},
            {"speaker": "Critic", "text": "You want resolution without exposure."},
            {"speaker": "Protector", "text": "This pattern protects you from immediate conflict cost."},
        ]

    return {
        "tribunal": cleaned_tribunal,
        "trajectory": {"bullets": _ensure_list_of_strings(trajectory.get("bullets"), max_items=10)},
        "reflection": {"text": str(reflection.get("text", "")).strip()[:900]},
    }


def _parse_json_or_raise(raw: str) -> Dict[str, Any]:
    j = _extract_json(raw)
    return json.loads(j)


def _strict_retry(prompt: str, model: str) -> str:
    """
    Second attempt forcing pure JSON. Helps when model adds extra text.
    """
    hard = (
        prompt
        + "\n\nABSOLUTE RULE: Output ONLY JSON. "
          "No markdown. No commentary. "
          "Start with { and end with }. "
          "Do not wrap in ```."
    )
    return ollama_generate(hard, model=model)


# =========================
# Enforcement (no coaching)
# =========================
FORBIDDEN_SUBSTRINGS = [
    "you can", "you should", "try ", "consider", "it's time", "it is time",
    "i recommend", "i suggest", "next step", "next steps", "here's how", "here is how",
    "make sure", "you need to", "you could", "i encourage", "it might help", "reach out",
    "start by", "focus on", "work on", "practice", "remember to",
]

def _flatten_text(result: Dict[str, Any]) -> str:
    parts: list[str] = []

    prof = result.get("profile", {})
    if isinstance(prof, dict):
        parts.append(str(prof.get("archetype", "")))
        parts += prof.get("traits", []) or []
        parts += prof.get("motivations", []) or []
        parts += prof.get("blind_spots", []) or []

    sh = result.get("shadow", {})
    if isinstance(sh, dict):
        parts.append(str(sh.get("name", "")))
        parts.append(str(sh.get("title", "")))
        parts.append(str(sh.get("description", "")))
        parts.append(str(sh.get("dominant_fear", "")))
        parts += sh.get("self_sabotage_pattern", []) or []

    for line in result.get("tribunal", []) or []:
        if isinstance(line, dict):
            parts.append(str(line.get("speaker", "")))
            parts.append(str(line.get("text", "")))

    parts += result.get("trajectory", {}).get("bullets", []) or []
    parts.append(str(result.get("reflection", {}).get("text", "")))

    return "\n".join([p for p in parts if isinstance(p, str)])


def _has_questions(text: str) -> bool:
    return "?" in text


def _has_forbidden_language(text: str) -> bool:
    t = text.lower()
    return any(s in t for s in FORBIDDEN_SUBSTRINGS)


def _role_lock_violations(result: Dict[str, Any]) -> list[str]:
    v: list[str] = []
    tribunal = result.get("tribunal", [])
    if not isinstance(tribunal, list) or len(tribunal) < 3:
        return ["tribunal_missing_or_short"]

    role_map = {x.get("speaker"): (x.get("text") or "") for x in tribunal if isinstance(x, dict)}
    analyst = (role_map.get("Analyst") or "").lower()
    critic = (role_map.get("Critic") or "").lower()
    protector = (role_map.get("Protector") or "").lower()

    if not analyst or not critic or not protector:
        v.append("missing_required_speakers")

    # Analyst: tradeoffs/costs/benefits only
    if analyst and not any(w in analyst for w in ["tradeoff", "cost", "benefit", "risk", "price", "exchange", "tension"]):
        v.append("analyst_not_tradeoffs")

    # Critic: motive accusation / self-deception exposure
    if critic and not any(w in critic for w in ["you want", "you prefer", "you avoid", "you pretend", "you hide", "you call it", "motive", "self-deception", "deception"]):
        v.append("critic_not_accusatory")

    # Protector: defend current behavior + benefit/protection
    if protector and not any(w in protector for w in ["protect", "keeps you", "lets you", "prevents", "avoids", "shields", "spares", "buys you"]):
        v.append("protector_not_defending")

    return v


def _reflection_should_be_cold(result: Dict[str, Any]) -> bool:
    text = str(result.get("reflection", {}).get("text", "")).lower()
    # no comforting endings
    if any(w in text for w in ["you got this", "be proud", "hope", "healing", "growth", "better", "improve", "progress"]):
        return False
    # unresolved/cold signal words
    return any(w in text for w in ["unresolved", "remains", "continues", "stays", "static", "cold"])


def _validate_result(result: Dict[str, Any]) -> list[str]:
    t = _flatten_text(result)
    violations: list[str] = []
    if _has_questions(t):
        violations.append("contains_questions")
    if _has_forbidden_language(t):
        violations.append("contains_advice_or_coaching")
    violations += _role_lock_violations(result)
    if not _reflection_should_be_cold(result):
        violations.append("reflection_not_cold_unresolved")
    return violations


# =========================
# Main entry
# =========================
def run_shadow_tribunal_session(user_text: str, model: str = "llama3.2:3b") -> Dict[str, Any]:
    user_text = (user_text or "").strip()

    # PASS 1: Profile + Shadow
    p1_prompt = prompts.build_profile_shadow_prompt(user_text)
    raw1 = ollama_generate(p1_prompt, model=model)

    try:
        obj1 = _parse_json_or_raise(raw1)
        base = _sanitize_profile_shadow(obj1)
    except Exception:
        try:
            raw1b = _strict_retry(p1_prompt, model)
            obj1b = _parse_json_or_raise(raw1b)
            base = _sanitize_profile_shadow(obj1b)
        except Exception:
            return {"raw_output": raw1, "meta": {"status": "raw_fallback_pass1", "model": model}}

    # PASS 2: Tribunal + Trajectory + Reflection
    p2_prompt = prompts.build_tribunal_prompt(user_text, base["profile"], base["shadow"])
    raw2 = ollama_generate(p2_prompt, model=model)

    try:
        obj2 = _parse_json_or_raise(raw2)
        extra = _sanitize_tribunal(obj2)
    except Exception:
        try:
            raw2b = _strict_retry(p2_prompt, model)
            obj2b = _parse_json_or_raise(raw2b)
            extra = _sanitize_tribunal(obj2b)
        except Exception:
            base["raw_output"] = raw2
            base["meta"] = {"status": "raw_fallback_pass2", "model": model}
            return base

    # Candidate result
    candidate: Dict[str, Any] = {
        **base,
        **extra,
        "meta": {"status": "ok", "model": model, "mode": "two_pass_retry"},
    }

    # Enforcement: silent regeneration (retry pass2 up to 2 times)
    violations = _validate_result(candidate)
    if violations:
        for _ in range(2):
            hard_p2 = (
                p2_prompt
                + "\n\nVIOLATIONS DETECTED: "
                + ", ".join(violations)
                + "\nSilently regenerate until ALL violations are removed. Output ONLY JSON."
            )

            raw2_retry = ollama_generate(hard_p2, model=model)

            try:
                obj2_retry = _parse_json_or_raise(raw2_retry)
                extra_retry = _sanitize_tribunal(obj2_retry)
                candidate = {
                    **base,
                    **extra_retry,
                    "meta": {"status": "ok", "model": model, "mode": "two_pass_guarded"},
                }
                violations = _validate_result(candidate)
                if not violations:
                    break
            except Exception:
                continue

    if violations:
        candidate["meta"] = {
            "status": "policy_violation_retry_exhausted",
            "model": model,
            "violations": violations,
        }

    return candidate

