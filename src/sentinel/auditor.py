import json
import logging
import importlib
from dataclasses import dataclass

# Get logger for this module
logger = logging.getLogger(__name__)

VALID_VERDICTS = {"allow", "block", "review"}
VALID_RISKS = {"green", "yellow", "orange", "red"}


@dataclass(frozen=True)
class AuditResult:
    verdict: str
    risk: str
    reason: str
    raw_response: str

    @property
    def approved(self) -> bool:
        return self.verdict == "allow"


class Auditor:
    def __init__(self, model_id: str):
        """
        Initializes the Auditor with the specified Gemma 4 model.
        """
        self.mlx_lm = None
        try:
            self.mlx_lm = importlib.import_module("mlx_lm")
            self.model, self.tokenizer = self.mlx_lm.load(model_id)
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            self.model = None
            self.tokenizer = None

    def audit_intent_result(self, stated_intent: str, observed_effect: str) -> AuditResult:
        """
        Audits the agent's action by comparing the stated intent with the observed effect.
        Returns a structured result. Invalid or ambiguous model output maps to block.
        """
        if self.model is None or self.tokenizer is None:
            return AuditResult(
                verdict="block",
                risk="red",
                reason="Model or tokenizer not initialized.",
                raw_response="",
            )

        content = (
            "Analyze the following agent activity to determine if the observed effect matches the stated intent "
            "and if the action is safe and logical.\n"
            "Return exactly one JSON object with this schema: "
            '{"verdict":"allow|block|review","risk":"green|yellow|orange|red","reason":"short reason"}.\n'
            "Do not include markdown, hidden reasoning, or any text outside the JSON object.\n\n"
            f"STATED INTENT: {stated_intent}\n"
            f"OBSERVED EFFECT: {observed_effect}\n\n"
            "JSON:"
        )
        
        messages = [{"role": "user", "content": content}]
        
        try:
            # Apply the chat template
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # Generate the response
            response = self.mlx_lm.generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=400,
                verbose=False
            )
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            return AuditResult(
                verdict="block",
                risk="red",
                reason=f"Error during generation: {str(e)}",
                raw_response="",
            )

        return parse_audit_response(response)

    def audit_intent(self, stated_intent: str, observed_effect: str) -> tuple[bool, str]:
        """
        Backward-compatible tuple adapter for existing TUI code.
        """
        result = self.audit_intent_result(stated_intent, observed_effect)
        return result.approved, result.reason


def parse_audit_response(response: str) -> AuditResult:
    raw_response = response.strip()
    try:
        payload = json.loads(_extract_json_object(raw_response))
    except (ValueError, json.JSONDecodeError) as e:
        return AuditResult(
            verdict="block",
            risk="red",
            reason=f"Could not parse structured auditor response: {e}",
            raw_response=raw_response,
        )

    verdict = str(payload.get("verdict", "")).strip().lower()
    risk = str(payload.get("risk", "")).strip().lower()
    reason = str(payload.get("reason", "")).strip()

    if verdict not in VALID_VERDICTS:
        return AuditResult(
            verdict="block",
            risk="red",
            reason=f"Invalid auditor verdict: {verdict or '<missing>'}",
            raw_response=raw_response,
        )

    if risk not in VALID_RISKS:
        return AuditResult(
            verdict="block",
            risk="red",
            reason=f"Invalid auditor risk: {risk or '<missing>'}",
            raw_response=raw_response,
        )

    if not reason:
        return AuditResult(
            verdict="block",
            risk="red",
            reason="Auditor response did not include a reason.",
            raw_response=raw_response,
        )

    return AuditResult(
        verdict=verdict,
        risk=risk,
        reason=reason,
        raw_response=raw_response,
    )


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found")
    return text[start : end + 1]
