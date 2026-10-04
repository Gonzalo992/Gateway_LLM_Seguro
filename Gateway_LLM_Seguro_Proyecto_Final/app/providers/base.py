from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, *, system_prompt: str, user_message: str, model: str) -> str:
        raise NotImplementedError
