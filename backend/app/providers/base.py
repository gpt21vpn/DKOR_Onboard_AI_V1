from abc import ABC, abstractmethod

class BaseProvider(ABC):
    name='base'
    model=''

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str: ...
