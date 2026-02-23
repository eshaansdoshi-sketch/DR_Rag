import json
import logging
import os
import re
import time
from typing import Type, TypeVar

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError

from core.cache import llm_cache, make_cache_key
from core.rate_limiter import groq_limiter, retry_with_backoff
from core.structured_logger import EventType, log_event
from core.token_budget import TokenBudget, estimate_tokens


load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    pass


class LLMClient:
    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable not set. Please ensure it is defined in your .env file.")
        
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        max_retries: int = 1,
        token_budget: TokenBudget | None = None,
    ) -> T:
        # Check cache first
        cache_key = make_cache_key("llm", self.model, prompt)
        cached = llm_cache.get(cache_key)
        if cached is not None:
            log_event(logger, logging.DEBUG, EventType.CACHE_HIT,
                      "LLM cache hit", model=self.model)
            return cached

        schema_instruction = (
            f"\n\nRespond ONLY with valid JSON matching the specified schema. No explanations."
        )
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    schema_instruction = (
                        f"\n\nYOU MUST respond ONLY with valid JSON. "
                        f"No markdown, no text, no explanations. "
                        f"Pure JSON only matching the schema provided."
                    )
                
                full_prompt = prompt + schema_instruction

                # Budget check before API call
                if token_budget is not None:
                    estimated = estimate_tokens(full_prompt)
                    token_budget.check_budget(estimated)

                _t0 = time.perf_counter()
                response = retry_with_backoff(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a structured data generator. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ],
                    temperature=0.1,
                    max_retries=3,
                    base_delay=0.5,
                    rate_limiter=groq_limiter,
                    service_name="groq_llm",
                )
                
                raw_output = response.choices[0].message.content
                _latency = (time.perf_counter() - _t0) * 1000

                # Record actual token usage from API response
                usage_info = {}
                if hasattr(response, "usage") and response.usage:
                    usage_info = {
                        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                        "total_tokens": getattr(response.usage, "total_tokens", 0),
                    }
                    if token_budget is not None:
                        token_budget.record_usage(**usage_info)

                log_event(logger, logging.INFO, EventType.LLM_CALL_SUCCESS,
                          "Groq call completed", model=self.model,
                          latency_ms=_latency, **usage_info)

                logger.debug(f"Raw LLM response (attempt {attempt + 1}): {raw_output}")
                
                json_str = self._extract_json(raw_output)
                parsed_data = json.loads(json_str)
                validated_output = response_model.model_validate(parsed_data)

                # Cache the validated result
                llm_cache.put(cache_key, validated_output)

                return validated_output
                
            except (json.JSONDecodeError, ValidationError) as e:
                log_event(logger, logging.WARNING, EventType.LLM_CALL_ERROR,
                          f"Validation failed attempt {attempt + 1}/{max_retries + 1}",
                          retry_count=attempt + 1, error=str(e))
                if attempt >= max_retries:
                    raise StructuredOutputError(
                        f"Failed to generate valid structured output after {max_retries + 1} attempts. "
                        f"Last error: {str(e)}"
                    ) from e
        
        raise StructuredOutputError("Unexpected error in generate_structured")

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        
        json_block_pattern = r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        json_pattern = r"(\{.*\}|\[.*\])"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return text
