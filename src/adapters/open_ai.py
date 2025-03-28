from .provider import ProviderAdapter
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
from datetime import datetime, timezone
from src.schemas import APIType, AttemptMetadata, Choice, Message, Usage, Cost, CompletionTokensDetails, Attempt
from typing import Optional

load_dotenv()


class OpenAIAdapter(ProviderAdapter):


    def init_client(self):
        """
        Initialize the OpenAI client
        """
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = OpenAI()
        return client


    def make_prediction(self, prompt: str, task_id: Optional[str] = None, test_id: Optional[str] = None, pair_index: int = None) -> Attempt:
        """
        Make a prediction with the OpenAI model and return an Attempt object
        
        Args:
            prompt: The prompt to send to the model
            task_id: Optional task ID to include in metadata
            test_id: Optional test ID to include in metadata
        """
        start_time = datetime.now(timezone.utc)
        

        response = self.call_ai_model(prompt)
        
        end_time = datetime.now(timezone.utc)

        # Use pricing from model config
        input_cost_per_token = self.model_config.pricing.input / 1_000_000  # Convert from per 1M tokens
        output_cost_per_token = self.model_config.pricing.output / 1_000_000  # Convert from per 1M tokens
        
        # Get usage data
        usage = self._get_usage(response)
        
        prompt_cost = usage.prompt_tokens * input_cost_per_token
        completion_cost = usage.completion_tokens * output_cost_per_token

        # Convert input messages to choices
        input_choices = [
            Choice(
                index=0,
                message=Message(
                    role="user",
                    content=prompt
                )
            )
        ]

        # Convert OpenAI response to our schema
        response_choices = [
            Choice(
                index=1,
                message=Message(
                    role=self._get_role(response),
                    content=self._get_content(response)
                )
            )
        ]

        # Combine input and response choices
        all_choices = input_choices + response_choices

        # Create metadata
        metadata = AttemptMetadata(
            model=self.model_config.model_name,
            provider=self.model_config.provider,
            start_timestamp=start_time,
            end_timestamp=end_time,
            choices=all_choices,
            kwargs=self.model_config.kwargs,
            usage=usage,
            cost=Cost(
                prompt_cost=prompt_cost,
                completion_cost=completion_cost,
                total_cost=prompt_cost + completion_cost
            ),
            task_id=task_id,
            pair_index=pair_index,
            test_id=test_id
        )

        attempt = Attempt(
            metadata=metadata,
            answer=self._get_content(response)
        )

        return attempt

    def call_ai_model(self, prompt: str):
        """
        Call the appropriate OpenAI API based on the api_type
        """
        messages = [{"role": "user", "content": prompt}]
        if self.model_config.api_type == APIType.CHAT_COMPLETIONS:
            return self.chat_completion(messages)
        else:  # APIType.RESPONSES
            # account for different parameter names between chat completions and responses APIs
            self._normalize_to_responses_kwargs()
            return self.responses(messages)
    
    def chat_completion(self, messages: list) -> str:
        """
        Make a call to the OpenAI Chat Completions API
        """
        return self.client.chat.completions.create(
            model=self.model_config.model_name,
            messages=messages,
            **self.model_config.kwargs
        )
    
    def responses(self, messages: list) -> str:
        """
        Make a call to the OpenAI Responses API
        """
        return self.client.responses.create(
            model=self.model_config.model_name,
            input=messages,
            **self.model_config.kwargs
        )

    def extract_json_from_response(self, input_response: str) -> list[list[int]] | None:
        prompt = f"""
You are a helpful assistant. Extract only the JSON array of arrays from the following response. 
Do not include any explanation, formatting, or additional text.
Return ONLY the valid JSON array of arrays with integers.

Response:
{input_response}

Example of expected output format:
[[1, 2, 3], [4, 5, 6]]

IMPORTANT: Return ONLY the array, with no additional text, quotes, or formatting.
"""
        completion = self.call_ai_model(
            prompt=prompt
        )

        assistant_content = self._get_content(completion)

        # Try to extract JSON from various formats
        # Remove markdown code blocks if present
        if "```" in assistant_content:
            # Extract content between code blocks
            code_blocks = assistant_content.split("```")
            for block in code_blocks:
                if block.strip() and not block.strip().startswith("json"):
                    assistant_content = block.strip()
                    break
        
        # Remove any leading/trailing text that's not part of the JSON
        assistant_content = assistant_content.strip()
        
        # Try to find array start/end if there's surrounding text
        if assistant_content and not assistant_content.startswith("["):
            start_idx = assistant_content.find("[[")
            if start_idx >= 0:
                end_idx = assistant_content.rfind("]]") + 2
                if end_idx > start_idx:
                    assistant_content = assistant_content[start_idx:end_idx]

        try:
            # Try direct parsing first
            json_result = json.loads(assistant_content)
            if isinstance(json_result, list) and all(isinstance(item, list) for item in json_result):
                return json_result
            
            # If we got a dict with a response key, use that
            if isinstance(json_result, dict) and "response" in json_result:
                return json_result.get("response")
                
            return None
        except json.JSONDecodeError:
            # If direct parsing fails, try to find and extract just the array part
            try:
                # Look for array pattern and extract it
                import re
                array_pattern = r'\[\s*\[\s*\d+(?:\s*,\s*\d+)*\s*\](?:\s*,\s*\[\s*\d+(?:\s*,\s*\d+)*\s*\])*\s*\]'
                match = re.search(array_pattern, assistant_content)
                if match:
                    return json.loads(match.group(0))
            except:
                pass
            
            return None
        
    def _get_usage(self, response) -> Usage:
        """
        Extract usage information from the response based on the API type
        """
        if self.model_config.api_type == APIType.CHAT_COMPLETIONS:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            reasoning_tokens = 0
            if hasattr(response.usage, 'completion_tokens_details') and hasattr(response.usage.completion_tokens_details, 'reasoning_tokens'):
                reasoning_tokens = response.usage.completion_tokens_details.reasoning_tokens
        else:  # APIType.RESPONSES
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens
            reasoning_tokens = 0
            if hasattr(response.usage, 'output_tokens_details') and hasattr(response.usage.output_tokens_details, 'reasoning_tokens'):
                reasoning_tokens = response.usage.output_tokens_details.reasoning_tokens
        
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            completion_tokens_details=CompletionTokensDetails(
                reasoning_tokens=reasoning_tokens,
                accepted_prediction_tokens=completion_tokens,
                rejected_prediction_tokens=0
            )
        )

    def _get_content(self, response):
        if self.model_config.api_type == APIType.CHAT_COMPLETIONS:
            return response.choices[0].message.content.strip()
        else:  # APIType.RESPONSES
            return response.output_text.strip()

    def _get_role(self, response):
        if self.model_config.api_type == APIType.CHAT_COMPLETIONS:
            return response.choices[0].message.role
        else:  # APIType.RESPONSES
            return "assistant" # will always be assistant for responses API
        
    def _normalize_to_responses_kwargs(self):
        """
        Normalize kwargs based on API type to handle different parameter names between chat completions and responses APIs
        """
        if self.model_config.api_type == APIType.RESPONSES:
            # Convert max_tokens and max_completion_tokens to max_output_tokens for responses API
            if "max_tokens" in self.model_config.kwargs:
                self.model_config.kwargs["max_output_tokens"] = self.model_config.kwargs.pop("max_tokens")
            if "max_completion_tokens" in self.model_config.kwargs:
                self.model_config.kwargs["max_output_tokens"] = self.model_config.kwargs.pop("max_completion_tokens")