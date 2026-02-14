import json
import logging
import os
import re
from typing import Type, TypeVar

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError


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
        max_retries: int = 1
    ) -> T:
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
                
                response = self.client.chat.completions.create(
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
                )
                
                raw_output = response.choices[0].message.content
                logger.debug(f"Raw LLM response (attempt {attempt + 1}): {raw_output}")
                
                json_str = self._extract_json(raw_output)
                parsed_data = json.loads(json_str)
                validated_output = response_model.model_validate(parsed_data)
                
                return validated_output
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    f"Validation failed on attempt {attempt + 1}/{max_retries + 1}: {e}"
                )
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
