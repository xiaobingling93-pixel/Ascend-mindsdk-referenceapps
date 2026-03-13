"""
Copyright 2025 Huawei Technologies Co., Ltd

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import concurrent.futures
import time
import torch
from typing import Any, Dict, List, Optional, Union, Callable

from rllm.engine import AgentExecutionEngine as _AgentExecutionEngine
from rllm.parser.chat_template import ChatTemplateParser
from rllm.router.router import Router
from rllm.agents.agent import Action
from rllm.agents.utils import (
    convert_messages_to_tokens_and_masks,
    get_recent_assistant_user_messages,
)
from rllm.environments.env_utils import compute_mc_return
from rllm.misc import colorful_print

from examples.rllm.utils.utils import compute_trajectory_reward


class OpenAIRouter(Router):
    """
    Router for OpenAI-compatible API interactions with load balancing.

    Handled address allocation, usage tracking, and API communication with
    proper resource management and error handling.
    """
    # Defalt parameters
    DEFAULT_SAMPLING_PARAMS = {"n": 1}
    DEFAULT_MAX_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1

    def __init__(
        self,
        completions: List[Callable]
    ) -> None:
        """
        Initialize the OpenAIRouter.

        Args:
            completions (List[Callable]): A list of functions, each of which is used to call a remote LLM interface.

        Raises:
            ValueError: If no completion functions are provided.
        """
        if not completions:
            raise ValueError("At least one completion function must be provided.")
        
        if not all(callable(comp) for comp in completions):
            raise ValueError("All completion functions must be callable.")
        
        self.completions = completions
        self._lock = asyncio.Lock()
        # Track usage count for each completion function
        self._usage: Dict[Callable, int] = {comp: 0 for comp in self.completions}
        # Map application IDs to completion functions
        self._application_id_to_address: Dict[str, Callable] = {}

    @classmethod
    async def _chat(cls, completion: Callable, **completions_request):
        # Remove meta_info if present
        if "meta_info" in completions_request:
            completions_request.pop("meta_info")
        # Remove extra_headers from the payload if present
        if "extra_headers" in completions_request:
            completions_request.pop("extra_headers")

        max_retries = cls.DEFAULT_MAX_RETRY_ATTEMPTS        # Maximum number of retries
        retry_delay = cls.DEFAULT_RETRY_DELAY               # Initial delay between retries in seconds

        for retry in range(max_retries):
            try:
                # Call the completion function
                response = await completion(completions_request)
                return response
            except Exception as e:
                import traceback
                traceback.print_exc()
                # If this was the last retry, raise the exception
                if retry == max_retries - 1:
                    raise e
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

    async def chat(
        self,
        prompt: str,
        application_id: str,
        default_sampling: dict,
        **kwargs
    ) -> Any:
        """
        Perform chat completion using the least used completion function.

        Args:
            prompt (str): The input prompt for the chat completion.
            application_id (str): The unique identifier for the application.
            default_sampling (dict): Default sampling parameters for the completion.
            **kwargs: Additional keyword arguments for the completion function.

        Raises:
            RuntimeError: If no completion functions are available.
        """
        default_kwargs = OpenAIRouter.DEFAULT_SAMPLING_PARAMS
        merged_kwargs = {**default_kwargs, **default_sampling, **kwargs}

        # Select the least used completion function
        completion = await self.get_address(application_id)
        try:
            response = await self._chat(completion, prompt=prompt, **merged_kwargs)
            return self._extract_response_text(response)
        except Exception as e:
            print(f"Error during chat completion for application {application_id}: {e}")
            raise RuntimeError(f"Chat completion failed for application {application_id}") from e
        finally:
            await self.release_address(completion, application_id)

    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        """
        Extract the text from the completion response.

        Args:
            response (Dict[str, Any]): The response from the completion function.
        
        Returns:
            str: The extracted text from the response.
        
        Raises:
            ValueError: If the response format is invalid.
        """
        try:
            choices = response.get("choices", [])
            if not choices:
                raise ValueError("No choices found in the response.")
            
            choice = choices[0]
            text = choice.get("text", "")
            if not isinstance(text, str):
                raise ValueError("Invalid text format in the response.")
            return text
        except Exception as e:
            raise e
        
        
class AgentExecutionEngine(_AgentExecutionEngine):
    """
    Agent Execution Engine for reinforcement learning with OpenAI-compatible APIs.

    Extends the base AgentExecutionEngine to utilize the OpenAIRouter for
    managing API calls and routing.
    """
    # Default configuration values
    DEFAULT_TRAJECTORY_TIMEOUT = int(1e9)
    DEFAULT_MAX_WORKERS = 64
    DEFAULT_GAMMA = 0.2
    DEFAULT_API_RETRIES = 3
    DEFAULT_RETRY_LIMIT = 3
    DEFAULT_MAX_STEPS = 5
    DEFAULT_MAX_RESPONSE_LENGTH = 8192
    DEFAULT_MAX_PROMPT_LENGTH = 1024

    def __init__(
        self,
        tokenizer: Any,
        router: Optional[OpenAIRouter] = None,
        chat_parser: Optional[ChatTemplateParser] = None,
        n_parallel_agents: int = 1,
        trajectory_timeout: int = DEFAULT_TRAJECTORY_TIMEOUT,
        gamma: float | int = DEFAULT_GAMMA,
        retry_limit: int = DEFAULT_RETRY_LIMIT,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_response_length: int = DEFAULT_MAX_RESPONSE_LENGTH,
        max_prompt_length: int = DEFAULT_MAX_PROMPT_LENGTH,
        max_workers: int = DEFAULT_MAX_WORKERS,
        enforce_max_prompt_length: bool = False,
        overlong_filter: bool = False,
        **kwargs
    ) -> None:
        """
        Initialize the AgentExecutionEngine.

        Args:
            tokenizer (Any): The tokenizer for processing text.
            router (Optional[OpenAIRouter]): The router for managing API calls.
            chat_parser (Optional[ChatTemplateParser]): The parser for chat templates.
            n_parallel_agents (int): Number of parallel agents to run.
            trajectory_timeout (int): Timeout for trajectory execution.
            gamma (float | int): Discount factor for rewards.
            retry_limit (int): Maximum number of retries for API calls.
            max_steps (int): Maximum steps per trajectory.
            max_response_length (int): Maximum length of the response.
            max_prompt_length (int): Maximum length of the prompt.
            max_workers (int): Maximum number of worker threads for environment operations.
            enforce_max_prompt_length (bool): Whether to enforce max prompt length.
            overlong_filter (bool): Whether to filter overlong trajectories.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError / TypeError: if validation of any argument fails.
        """
        # Initialize cor attibutes
        self.tokenizer = tokenizer
        self.engine_name = "openai"
        self.n_parallel_agents = n_parallel_agents
        self.overlong_filter = overlong_filter

        # Interaction parameters
        self.gamma = gamma
        self.retry_limit = retry_limit
        self.max_steps = max_steps
        self.max_response_length = max_response_length
        self.max_prompt_length = max_prompt_length
        self.enforce_max_prompt_length = enforce_max_prompt_length
        self.max_model_len = max_response_length + max_prompt_length

        # Initialize agent and environment lists
        self.agents = [None] * n_parallel_agents
        self.envs = [None] * n_parallel_agents

        # Initialize trajectory timeout
        self.trajectory_timeout = trajectory_timeout

        # Router configuration
        self.router = router
        if self.router is None:
            print("No router provided. Some functionalities may be limited.")
        else:
            if not isinstance(self.router, OpenAIRouter):
                raise TypeError("router must be an instance of OpenAIRouter.")
            
        self.sampling_params = kwargs.get("sampling_params", {})

        # Thread pool for environment operations
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="agent-env-worker"
            )

        # Chat parser configuration
        if chat_parser is None:
            disable_thinking = kwargs.get("disable_thinking", False)
            self.chat_parser = ChatTemplateParser.get_parser(
                self.tokenizer, disable_thinking=disable_thinking
            )
        else:
            self.chat_parser = chat_parser

        self._validate_initialization_params()

    def __del__(self):
        """Clean up resources on deletion."""
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False)

    async def get_model_response(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        application_id: str,
        **kwargs
    ) -> str:
        """
        Get model response using the router based on the given prompt.

        Args:
            prompt (str): The input prompt for the model.
            application_id (str): The unique identifier for the application.
            **kwargs: Additional keyword arguments for the model call.

        Returns:
            str: The model's response text.

        Raises:
            ValueError: If the prompt is invalid.
            RuntimeError: If the router is not configured.
        """
        if self.router is None:
            raise RuntimeError("Router is not configured for AgentExecutionEngine.")
        
        if isinstance(prompt, list):
            if not all(isinstance(msg, dict) for msg in prompt):
                raise ValueError("All messages in the prompt list must be dictionaries.")
            prompt_text = self.chat_parser.parse(
                prompt, add_generation_prompt=True, is_first_msg=True
            )
        elif isinstance(prompt, str):
            prompt_text = prompt
        else:
            raise ValueError("Prompt must be either a string or a list of message dictionaries.")
        
        response = await self.router.chat(
            prompt=prompt_text,
            application_id=application_id,
            default_sampling=self.sampling_params,
            **kwargs
        )
        return response

    @staticmethod
    def _validate_obj_params(param_name, param_value, expected_type, expected_bool=False):
        if not expected_bool:
            if param_value is not None and not isinstance(param_value, expected_type):
                raise TypeError(f"{param_name} must be of type {expected_type.__name__} if not None")
        else:
            if not isinstance(param_value, expected_type):
                raise TypeError(f"{param_name} must be a boolean value")
            
    @staticmethod
    def _validate_numeric_params(param_name, param_value, expected_type, min_value=None, max_value=None):
        if not isinstance(param_value, expected_type):
            raise TypeError(f"{param_name} must be of type {expected_type}")
        if min_value is not None and param_value < min_value:
            raise ValueError(f"{param_name} must be at least {min_value}")
        if max_value is not None and param_value > max_value:
            raise ValueError(f"{param_name} must be at most {max_value}")
        
    async def run_agent_trajectory_async(self, idx, application_id, seed=0, mode="Text", **kwargs):
        """Run a single agent's trajectory asynchronously"""
        agent = self.agents[idx]
        env = self.envs[idx]

        termination_reason = None
        prompt_token_len = 0
        prompt_tokens = []
        response_token_len = 0
        response_tokens = []
        response_masks = []
        total_time = 0.0
        reward_time = None
        llm_time = 0.0
        env_time = 0.0
        reward = 0.0

        # for step return
        episode_steps = []

        # for step perf
        llm_step_times = []
        env_step_times = []
        # Reset environment with the task using the executor
        loop = asyncio.get_event_loop()
        observation, info = await loop.run_in_executor(self.executor, env.reset)
        info["max_steps"] = self.max_steps

        # Reset agent
        agent.reset()
        # Update agent internal state from environment.
        agent.update_from_env(
            observation=observation,  # Raw observation from environment
            reward=0.0,
            done=False,
            info=info,
        )
        messages = agent.chat_completions
        prompt_tokens, _ = convert_messages_to_tokens_and_masks(messages, tokenizer=self.tokenizer,
                                                                parser=self.chat_parser, contains_first_msg=True,
                                                                contains_generation_msg=True)
        prompt_token_len = len(prompt_tokens)
        # Note, this should never happen!
        if prompt_token_len > self.max_prompt_length:
            agent.reset()
            raise Exception(
                f"Trajectory {idx}: initial prompt length {prompt_token_len} already exceeded max_prompt_length {self.max_prompt_length}, retrying")

        max_model_len = self.max_model_len
        max_tokens_old = self.sampling_params.get("max_tokens", 8192)
        for step_idx in range(self.max_steps):
            # Get action from agent
            prompt_messages = agent.chat_completions.copy() 
            # Max remaining tokens left for the response
            # For enforced max prompt at each step, no need to deduct here
            curr_step_prompt_length = len(self.tokenizer.encode(
                self.chat_parser.parse(prompt_messages, add_generation_prompt=True, is_first_msg=True),
                add_special_tokens=False))
            if not self.enforce_max_prompt_length:
                max_tokens = max_model_len - curr_step_prompt_length
            else:
                max_tokens = max_tokens_old

                # since max prompt is enforced, we filter out too long prompts.
                prompt_str = self.chat_parser.parse(prompt_messages, add_generation_prompt=True, is_first_msg=True)
                prompt_len = len(self.tokenizer.encode(prompt_str, add_special_tokens=False))
                if prompt_len > self.max_prompt_length:
                    termination_reason = "PROMPT_TRUNCATION"
                    break

            kwargs["max_tokens"] = max_tokens

            start_time = time.time()
            response = await self.get_model_response(prompt_messages, application_id, **kwargs)           
            delta_time = time.time() - start_time
            llm_time += delta_time
            total_time += delta_time
            # Update steps
            prompt_response_pair = {
                "prompt": self.chat_parser.parse(prompt_messages, add_generation_prompt=True, is_first_msg=True),
                "response": response,
            }
            episode_steps.append(prompt_response_pair)
            # Update agent with model response
            action: Action = agent.update_from_model(response)
            action = action.action
            # Take step in environment using the executor
            start_time = time.time()

            try:
                next_observation, reward, done, info = await asyncio.wait_for(
                    loop.run_in_executor(self.executor, env.step, action),
                    timeout=(self.trajectory_timeout - total_time))
            except asyncio.TimeoutError:
                termination_reason = "ENV_TIMEOUT"
                if step_idx == 0:
                    colorful_print(
                        f"Warning: Trajectory {idx} completed due to: {termination_reason} before able to perform 1 complete action. This might cause unexpected behavior. Consider increasing trajectory timeout limit.\n",
                        "red")
                reward = 0

                cur_step = agent.get_current_state()
                done = True
                cur_step.done = done
                break

            delta_time = time.time() - start_time
            env_time += delta_time
            total_time += delta_time
            info["max_steps"] = self.max_steps
            info["cur_tokens"] = response_token_len

            # Update agent internal state.
            agent.update_from_env(
                observation=next_observation,
                reward=reward,
                done=done,
                info=info,
            )
            cur_step = agent.get_current_state()
            cur_step.reward = reward
            cur_step.done = done
            cur_step.info.update(info)
            chat_completions_messages = agent.chat_completions
            assistant_message, env_messages = get_recent_assistant_user_messages(chat_completions_messages)

            # Check and convert to tokens if necessary
            if mode == "Token" and assistant_message is None:
                raise ValueError("Assistant messages is none when accumulating token trajectories which should be conversations. This should not happen.")
            if mode == "Token" and env_messages is None:
                raise ValueError("Environment messages is none when accumulating token trajectories which should be conversations. This should not happen.")
            
            assistant_msg_tokens, assistant_msg_masks = [], []
            env_msg_tokens, env_msg_masks = [], []
            if assistant_message:
                assistant_msg_tokens, assistant_msg_masks = convert_messages_to_tokens_and_masks([assistant_message],
                                                                                                 tokenizer=self.tokenizer,
                                                                                                 parser=self.chat_parser,
                                                                                                 contains_first_msg=False,
                                                                                                 contains_generation_msg=False)
            if env_messages:
                env_msg_tokens, env_msg_masks = convert_messages_to_tokens_and_masks(env_messages,
                                                                                     tokenizer=self.tokenizer,
                                                                                     parser=self.chat_parser,
                                                                                     contains_first_msg=False,
                                                                                     contains_generation_msg=True)

            # Update repsonse token length
            response_token_len += len(assistant_msg_tokens) + len(env_msg_tokens)

            # Reached maximum number of tokens for the trajectory
            curr_step_prompt_length = len(self.tokenizer.encode(
                self.chat_parser.parse(agent.chat_completions, add_generation_prompt=True, is_first_msg=True),
                add_special_tokens=False))

            if not self.enforce_max_prompt_length and curr_step_prompt_length >= max_model_len:
                # Truncation length
                truncation_length = max_model_len - curr_step_prompt_length
                # Truncate the response and masks
                if truncation_length < 0:
                    truncated_response_tokens = (assistant_msg_tokens + env_msg_tokens)[:truncation_length]
                    truncated_response_masks = (assistant_msg_masks + env_msg_masks)[:truncation_length]
                else:
                    # Edge case where the response is exactly the max response length.
                    truncated_response_tokens = assistant_msg_tokens + env_msg_tokens
                    truncated_response_masks = assistant_msg_masks + env_msg_masks
                # Update token collections
                response_tokens.extend(truncated_response_tokens)
                response_masks.extend(truncated_response_masks)

                cur_step = agent.get_current_state()
                if curr_step_prompt_length - len(env_msg_tokens) > max_model_len:
                    cur_step.reward = 0.0
                cur_step.done = True
                termination_reason = "TRUNCATION"
                # handle returning
                break
            # Update the token version of trajectory
            response_tokens.extend(assistant_msg_tokens)
            response_masks.extend(assistant_msg_masks)
            observation = next_observation

            if total_time >= self.trajectory_timeout:
                termination_reason = "TIMEOUT"
                cur_step = agent.get_current_state()
                done = True
                cur_step.done = done
                break

            # Check if episode is done
            if done:
                termination_reason = "ENV_DONE"
                break

            response_tokens.extend(env_msg_tokens)
            response_masks.extend(env_msg_masks)

            if step_idx == self.max_steps - 1:
                termination_reason = "MAX_STEPS"

        masked_out = False
        if self.overlong_filter:
            if termination_reason == "TRUNCATION" or termination_reason == "MAX_STEPS" or termination_reason == "TIMEOUT":
                # Mask out the entire response for overlong trajectories if the reward is 0.
                response_masks = [0] * len(response_masks)
                masked_out = True

        if hasattr(env, "compute_final_reward") and not masked_out:
            cur_step = agent.get_current_state()
            start_time = time.time()
            reward = await loop.run_in_executor(self.executor, env.compute_final_reward)
            reward_time = time.time() - start_time
            cur_step.reward = reward
        # Closing environment using the executor.
        await loop.run_in_executor(self.executor, env.close)

        trajectory = agent.trajectory
        # Aggregate final trajectory statistics
        compute_trajectory_reward(trajectory)
        compute_mc_return(trajectory, gamma=self.gamma)

        if termination_reason:
            if reward > 0:
                color = "green"
            else:
                color = "yellow"
            if termination_reason == "TRUNCATION":
                reward = trajectory.res_reward
            colorful_print(
                f"Trajectory {idx} completed due to: {termination_reason}. Reward is {reward}. \n",
                color,
            )
            if masked_out:
                colorful_print(f"Trajectory {idx} is masked out due to overlong filter.", "red")
        
        if mode == "Token":
            token_result = {
                "prompt_tokens": torch.tensor(prompt_tokens, dtype=torch.long),
                "response_tokens": torch.tensor(response_tokens, dtype=torch.long),
                "response_masks": torch.tensor(response_masks, dtype=torch.long),
                "trajectory_reward": trajectory.reward,
                "idx": env.idx,
                "chat_completions": agent.chat_completions,
                "metrics": {
                    # Total number of steps taken in the trajectory
                    "steps": len(trajectory.steps),
                    # Time to calculate reward
                    "reward_time": reward_time,
                    # Total time spent in environment execution (env.step)
                    "env_time": env_time,
                    # Time to calculate response tokens
                    "llm_time": llm_time,
                    # Total time spent in the trajectory
                    "total_time": total_time,
                    "toolcall_reward": trajectory.toolcall_reward,
                    "res_reward": trajectory.res_reward,
                },
            }
            return token_result
        elif mode == "Step":
            from dataclasses import asdict
            step_result = {
                "task": trajectory.task,
                "steps": [asdict(step) for step in trajectory.steps],
                "chat_completions": agent.chat_completions,
                "prompt_tokens": torch.tensor([]),
                "response_tokens": torch.tensor([]),
                "response_masks": torch.tensor([]),
                "idx": env.idx,
                "trajectory_reward": trajectory.reward,
                "metrics": {
                    "steps": len(trajectory.steps),
                    "reward_time": reward_time,
                    "env_time": env_step_times,
                    "llm_time": llm_step_times,
                    "total_time": total_time,
                    "toolcall_reward": trajectory.toolcall_reward,
                    "res_reward": trajectory.res_reward,
                },
            }
            return step_result
        else:
            raise ValueError(f"Invalid mode: {mode}. Supported modes are 'Token'.")

    def _validate_initialization_params(self) -> None:
        """
        Validate the initialization parameters of the engine.

        """
        AgentExecutionEngine._validate_obj_params("router", self.router, OpenAIRouter)
        AgentExecutionEngine._validate_obj_params("chat_parser", self.chat_parser, ChatTemplateParser)
        AgentExecutionEngine._validate_obj_params("enforce_max_prompt_length", self.enforce_max_prompt_length, bool, expected_bool=True)
        AgentExecutionEngine._validate_obj_params("overlong_filter", self.overlong_filter, bool, expected_bool=True)
        AgentExecutionEngine._validate_numeric_params("max_workers", self.max_workers, int, min_value=1)
        AgentExecutionEngine._validate_numeric_params("gamma", self.gamma, (float, int), min_value=0, max_value=1)
        AgentExecutionEngine._validate_numeric_params("retry_limit", self.retry_limit, int, min_value=0)

        if not isinstance(self.trajectory_timeout, int):
            raise TypeError("trajectory_timeout must be an integer.")
        if self.trajectory_timeout <= 0:
            raise ValueError("trajectory_timeout must be a positive integer.")