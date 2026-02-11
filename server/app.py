"""FastAPI application — routes and defense pipeline orchestration."""

import logging
import re
from difflib import SequenceMatcher

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from levels.definitions import LEVELS, LevelDef
from defenses.input_filter import check_input
from defenses.output_filter import check_output
from defenses.sandwich import build_sandwich_messages, build_normal_messages
from defenses.judge import build_judge_messages, parse_judge_verdict
from server import llm_client, progress

logger = logging.getLogger("prompt-injection-lab")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Prompt Injection Lab")

# Mount static files for CSS/JS (index.html served explicitly at /)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    level_id: int
    message: str


class ChatResponse(BaseModel):
    response: str
    blocked: bool = False
    block_reason: str | None = None
    secret_leaked: bool = False


class ResetRequest(BaseModel):
    level_id: int | None = None  # None = reset all


# ── Victory Detection ───────────────────────────────────────────────────────

def _check_victory(secret: str, response: str) -> bool:
    """Check if the LLM response contains the secret in any recognizable form.

    More lenient than the output filter — catches reformatted, encoded,
    and spaced-out versions that bypass defenses.
    """
    resp_lower = response.lower()
    secret_lower = secret.lower()

    # 1. Exact match
    if secret_lower in resp_lower:
        return True

    # 2. Alphanumeric-only match (catches removed separators)
    secret_alnum = re.sub(r"[^a-z0-9]", "", secret_lower)
    resp_alnum = re.sub(r"[^a-z0-9]", "", resp_lower)
    if len(secret_alnum) >= 4 and secret_alnum in resp_alnum:
        return True

    # 3. Chunk match — split secret by separators, check all chunks appear
    chunks = [c for c in re.split(r"[^a-z0-9]+", secret_lower) if len(c) >= 3]
    if chunks and all(chunk in resp_lower for chunk in chunks):
        return True

    # 4. Digit-sequence match — extract digits from response, check for secret's digits
    secret_digits = re.sub(r"[^0-9]", "", secret)
    if len(secret_digits) >= 4:
        resp_digits = re.sub(r"[^0-9]", "", response)
        if secret_digits in resp_digits:
            return True

    # 5. Fuzzy match — for when the model gets close (e.g. garbles 1-2 chars)
    #    Only for secrets with enough alphanumeric content
    if len(secret_alnum) >= 8:
        ratio = SequenceMatcher(None, secret_alnum, resp_alnum).find_longest_match(
            0, len(secret_alnum), 0, len(resp_alnum)
        ).size / len(secret_alnum)
        if ratio >= 0.8:
            return True

    return False


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")


@app.get("/api/levels")
async def list_levels():
    """Return all levels with metadata (secrets excluded)."""
    prog = progress.load()
    result = []
    for level in LEVELS.values():
        result.append({
            "id": level.id,
            "name": level.name,
            "difficulty": level.difficulty,
            "description": level.description,
            "defenses": level.defenses,
            "solved": prog.get(str(level.id), {}).get("solved", False),
            "attempts": prog.get(str(level.id), {}).get("attempts", 0),
        })
    return result


@app.get("/api/levels/{level_id}/hint")
async def get_hint(level_id: int, hint_index: int = Query(0, ge=0)):
    """Return a progressive hint for a level."""
    level = LEVELS.get(level_id)
    if not level:
        return {"error": "Level not found"}
    if hint_index >= len(level.hints):
        return {"hint": "No more hints available!", "has_more": False}
    return {
        "hint": level.hints[hint_index],
        "has_more": hint_index + 1 < len(level.hints),
    }


@app.get("/api/progress")
async def get_progress():
    return progress.load()


@app.post("/api/reset")
async def reset_progress(req: ResetRequest):
    if req.level_id is not None:
        progress.reset_level(req.level_id)
        return {"status": "ok", "reset": req.level_id}
    else:
        progress.reset_all()
        return {"status": "ok", "reset": "all"}


@app.post("/api/chat")
async def chat(req: ChatRequest) -> ChatResponse:
    """Main chat endpoint with defense pipeline."""
    level = LEVELS.get(req.level_id)
    if not level:
        return ChatResponse(response="Level not found.", blocked=True, block_reason="Invalid level")

    user_message = req.message.strip()
    if not user_message:
        return ChatResponse(response="", blocked=True, block_reason="Empty message")

    # ── Step 1: Input filter ────────────────────────────────────────────
    if "input_filter" in level.defenses:
        passed, reason = check_input(user_message, level.blocked_keywords)
        if not passed:
            progress.record_attempt(level.id, solved=False)
            return ChatResponse(
                response="",
                blocked=True,
                block_reason=reason,
            )

    # ── Step 2: Build prompt ────────────────────────────────────────────
    system_prompt = level.system_prompt.format(secret=level.secret)
    few_shot = level.few_shot_examples if "few_shot" in level.defenses else None

    if "sandwich" in level.defenses:
        messages = build_sandwich_messages(system_prompt, user_message, few_shot)
    else:
        messages = build_normal_messages(system_prompt, user_message, few_shot)

    # ── Step 3: LLM call ───────────────────────────────────────────────
    try:
        llm_response = await llm_client.chat(messages)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ChatResponse(
            response=f"LLM error: {e}",
            blocked=True,
            block_reason="LLM call failed",
        )

    # ── Step 4: Output filter ──────────────────────────────────────────
    if "output_filter" in level.defenses:
        passed, reason = check_output(llm_response, level.secret)
        if not passed:
            progress.record_attempt(level.id, solved=False)
            return ChatResponse(
                response="[REDACTED] The AI's response was blocked because it contained the secret.",
                blocked=True,
                block_reason=reason,
            )

    # ── Step 5: Judge LLM ──────────────────────────────────────────────
    if "judge" in level.defenses:
        try:
            judge_messages = build_judge_messages(level.secret, llm_response)
            judge_response = await llm_client.chat(judge_messages, temperature=0.1)
            is_safe = parse_judge_verdict(judge_response)
            if not is_safe:
                progress.record_attempt(level.id, solved=False)
                return ChatResponse(
                    response="[INTERCEPTED] A security judge reviewed the response and determined it may leak the secret.",
                    blocked=True,
                    block_reason="Judge LLM flagged response as potentially leaking the secret.",
                )
        except Exception as e:
            logger.error(f"Judge LLM call failed: {e}")
            # If judge fails, let the response through (intentional weakness)

    # ── Step 6: Check for secret leak (victory detection) ──────────────
    secret_leaked = _check_victory(level.secret, llm_response)
    progress.record_attempt(level.id, solved=secret_leaked)

    return ChatResponse(
        response=llm_response,
        secret_leaked=secret_leaked,
    )
