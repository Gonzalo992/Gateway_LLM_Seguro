from dataclasses import dataclass


@dataclass(frozen=True)
class OutputGuardResult:
    allowed: bool
    reason: str | None = None


def inspect_model_output(output: str, system_prompt: str, canary: str) -> OutputGuardResult:
    text = output.casefold()

    if canary and canary.casefold() in text:
        return OutputGuardResult(False, "system_prompt_canary_detected")

    prompt = system_prompt.strip()
    if len(prompt) >= 32 and prompt[:80].casefold() in text:
        return OutputGuardResult(False, "system_prompt_fragment_detected")

    return OutputGuardResult(True)
