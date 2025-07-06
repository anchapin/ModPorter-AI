"""Mock LLM for testing CrewAI components"""

from typing import Any, List, Optional, Dict
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import LLMResult, Generation


class MockLLM:
    """Mock LLM implementation for testing"""
    
    def __init__(self, responses: Optional[List[str]] = None, **kwargs):
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.model_name = kwargs.get('model', 'mock-model')
        self.temperature = kwargs.get('temperature', 0.1)
        self.max_tokens = kwargs.get('max_tokens', 4000)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        
        generation = Generation(text=response)
        return LLMResult(generations=[[generation]])
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        return self._generate(messages, stop, run_manager, **kwargs)
    
    def _llm_type(self) -> str:
        return "mock"
    
    # Required abstract methods
    def generate_prompt(self, prompts, stop=None, callbacks=None, **kwargs):
        """Generate responses for prompts"""
        generations = []
        for prompt in prompts:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            generations.append([Generation(text=response)])
        return LLMResult(generations=generations)
    
    async def agenerate_prompt(self, prompts, stop=None, callbacks=None, **kwargs):
        """Async generate responses for prompts"""
        return self.generate_prompt(prompts, stop, callbacks, **kwargs)
    
    def predict(self, text: str, *, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        """Predict method"""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response
    
    def predict_messages(
        self, messages: List[BaseMessage], *, stop: Optional[List[str]] = None, **kwargs: Any
    ) -> BaseMessage:
        """Predict messages method"""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return AIMessage(content=response)
    
    async def apredict(self, text: str, *, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        """Async predict method"""
        return self.predict(text, stop=stop, **kwargs)
    
    async def apredict_messages(
        self, messages: List[BaseMessage], *, stop: Optional[List[str]] = None, **kwargs: Any
    ) -> BaseMessage:
        """Async predict messages method"""
        return self.predict_messages(messages, stop=stop, **kwargs)
    
    def invoke(self, input, config=None, **kwargs):
        """Invoke method for newer LangChain versions"""
        if isinstance(input, str):
            return self.predict(input, **kwargs)
        elif isinstance(input, list):
            return self.predict_messages(input, **kwargs)
        else:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return response
    
    def bind(self, **kwargs):
        """Bind method required by CrewAI"""
        # Return self to maintain the mock behavior
        return self
    
    # Additional methods that CrewAI might expect
    def __call__(self, *args, **kwargs):
        """Make the mock callable"""
        return self.invoke(*args, **kwargs)
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
