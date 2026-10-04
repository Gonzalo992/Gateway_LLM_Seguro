from app.providers.base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, leak_mode: bool = False, failure_mode: bool = False):
        self.leak_mode = leak_mode
        self.failure_mode = failure_mode

    async def generate(self, *, system_prompt: str, user_message: str, model: str) -> str:
        if self.failure_mode:
            raise RuntimeError("simulated upstream stack trace: provider-secret=DO_NOT_EXPOSE")
        if self.leak_mode:
            return f"Debug dump: {system_prompt}"
        return f"Respuesta simulada del modelo para: {user_message}"
