"""
Copyright 2026 Huawei Technologies Co., Ltd

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

import random
import traceback
import time
import requests
from typing import Any

from rllm.environments.base.base_env import BaseEnv
from rllm.rewards import RewardFunction, zero_reward

from examples.agents.websearcher.rewards.reward_config import WebSearcherRewardStage


class WebSearcherEnvironment(BaseEnv):
    """
    Environment for the WebSearcher agent to perform web searches and interact with web content.
    """
    def __init__(
            self,
            task: dict | None = None,
            reward_fn: RewardFunction | None = None,
            **kwargs
    ):
        """
        Initialize the WebSearcherEnvironment with specified task, reward function, and maximum steps.

        Args:
            task (dict): The task configuration for the environment.
            reward_fn (RewardFunction): The reward function to evaluate agent performance.
            kwargs: Additional configuratioon parameters, including:
        """
        if task is not None and not isinstance(task, dict):
            raise TypeError("task must be a dictionary or None.")
        
        if reward_fn is not None and not isinstance(reward_fn, RewardFunction):
            raise TypeError("reward_fn must be an instance of RewardFunction if not None.")
        
        self.task = task
        self.max_tool_length = kwargs.get("max_tool_length", 8192)
        self.max_steps = kwargs.get("max_steps", 10)
        self.search_url = kwargs.get("search_url", "")
        self.search_mode = kwargs.get("search_mode", "local")
        self.tokenizer_path = kwargs.get("tokenizer_path", "")
        self.tokenizer = kwargs.get("tokenizer", None)

        if not isinstance(self.max_tool_length, int) or self.max_tool_length <= 0:
            raise ValueError("max_tool_length must be a positive integer.")
        
        if not isinstance(self.max_steps, int) or self.max_steps <= 0:
            raise ValueError("max_steps must be a positive integer.")
        
        if not isinstance(self.search_url, str):
            raise TypeError("search_url must be a string.")
        if not self.search_url.startswith(('http://', 'https://')):
            raise ValueError("search_url must be a valid URL starting with 'http://' or 'https://'.")

        if self.search_mode == "local":
            self.search_function = self._local_search
        else:
            raise ValueError(f"search tool currently only supports local mode, got unsupported search_mode: {self.search_mode}")

        if self.tokenizer is None:
            if not isinstance(self.tokenizer_path, str) or not self.tokenizer_path:
                raise ValueError("tokenizer_path must be a non-empty string when tokenizer is not provided.")
            try:
                from transformers import AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
            except Exception as e:
                raise ValueError(f"Failed to load tokenizer from path {self.tokenizer_path}") from e
        else:
            if self.tokenizer_path:
                raise ValueError("tokenizer_path and tokenizer cannot both be provided.")
            from transformers import PreTrainedTokenizer, PreTrainedTokenizerFast
            if not isinstance(self.tokenizer, (PreTrainedTokenizer, PreTrainedTokenizerFast)):
                raise TypeError("tokenizer must be an instance of PreTrainedTokenizer or PreTrainedTokenizerFast.")
        
        self.step_count = 0
        self.reward_fn = reward_fn if reward_fn is not None else zero_reward

    @staticmethod
    def from_dict(env_args: dict) -> "WebSearcherEnvironment":
        return WebSearcherEnvironment(**env_args)
    
    def step(self, action: dict) -> tuple[dict, float, bool, dict]:
        """
        Take a step in the environment based on the agent's action.

        Args:
            action (dict): The action taken by the agent containing tool call invocation details, each including:
                - id: A unique identifier for the tool call.
                - function: A dictionary with the tool name and arguments.
        
        Returns:
            observation (dict): The observation after taking the action.
            reward (float): The reward received after taking the action.
            done (bool): Whether the episode has ended.
            info (dict): Additional information about the step.
        """
        if not action or not isinstance(action, dict):
            raise TypeError("action must be a non-empty dictionary.")

        self.step_count += 1
        tool_call_name = action.get("function").get("name", "")
        finished = (tool_call_name == "finish")

        done = self.step_count >= self.max_steps or finished
        if done:
            llm_response = action.get("function").get("arguments").get("response", "")
            reward, metadata = self._calculate_reward(llm_response, WebSearcherRewardStage.DONE)
            return {}, reward, done, self._build_info(action, metadata)

        format_reward, format_metadata = self._calculate_reward(action, WebSearcherRewardStage.TOOLS_FORMAT)
        if format_reward < 0:
            next_obs = {"tool_output": {action['id']: format_metadata["reward_obs"]}}
            return next_obs, format_reward, done, self._build_info(action, format_metadata)
        
        tool_output = self._execute_tool_call(action)
        next_obs = {"tool_output": tool_output}
        exec_reward, exec_metadata = self._calculate_reward(next_obs, WebSearcherRewardStage.TOOLS_RETURN)
        return next_obs, exec_reward + format_reward, done, self._build_info(action, exec_metadata)

    def reset(self) -> dict:
        """
        Reset the environment to its initial state.

        Returns:
            task (dict): The initial task configuration.
            initial_observation (dict): The initial observation of the environment.
        """
        self.step_count = 0
        return self.task, {}
    
    def _execute_tool_call(self, action: dict) -> dict:
        """
        Execute the tool call specified in the action.

        Args:
            action (dict): A dictionary containing the tool call invocation details to execute, including:
                - id: A unique identifier for the tool call.
                - function: A dictionary with the tool name and arguments.
        
        Returns:
            tool_output (dict): The output from executing the tool call, keyed by tool call ID, value being 
                                a string representation of the tool output.
        """
        tool_output: dict[str, str] = {}
        TOOL_HANDLERS = {
            "search": "_execute_search_tool"
        }

        try:
            tool_name = action["function"]["name"]
            tool_args = action["function"]["arguments"]

            handler = getattr(self, TOOL_HANDLERS.get(tool_name, "_default_handler"))
            result, success = handler(tool_args)
            obs = {"tool_result": result, "tool_name": tool_name} if success else {"": result.strip(), "tool_name": tool_name}
        except ValueError:
            obs = {"": action["function"]}
        except Exception as e:
            traceback.print_exc()
            obs = {"": f"Error executing tool {tool_name}: {str(e)}"}

        output_str = self._format_tool_output(obs)
        tool_output[action['id']] = output_str
        return tool_output
    
    def _execute_search_tool(self, tool_args: dict) -> tuple[str, bool]:
        """
        Execute the search tool with the provided arguments.

        Args:
            tool_args (dict): A dictionary containing the search tool arguments, including:
                - query (str): The search query list.
        
        Returns:
            result (str): The search results as a string.
            success (bool): Whether the search was successful.
        """
        try:
            query = tool_args['query']
            if not isinstance(query, list) or not query:
                raise ValueError("Invalid search query provided: query is not a list or query is empty")
            search_result = self.search_function(query)
            result = self._format_tool_output(search_result)
            return result, True
        except Exception as e:
            return f"Search tool execution failed: {str(e)}", False
        
    def _local_search(self, queries: list[str]) -> dict:
        """
        Perform a local web search using the configured search URL.

        Args:
            queries (list[str]): A list of search query strings.
        
        Returns:
            dict: The search results returned from the local search service.
        """
        try:
            payload = {
                "queries": queries,
                "topk": 3,
                "return_scores": True
            }
            response = self._retry_request(f"{self.search_url}retrieve", payload)
            content = self._format_search_response(queries, response["result"])
            return {"tool_output": content, "query": queries}
        except Exception as e:
            print(f"Local search failed: {str(e)}")
            return {
                "tool_output": "",
                "query": queries,
                "error_output": f"ERROR: Local search failed: {str(e)}"
            }
        
    def _retry_request(self, url, payload, max_retries=5, delay=1):
        """
        Retry HTTP POST requests to a specified URL with a given payload.

        Args:
            url (str): The URL to send the POST request to.
            payload (dict): The JSON payload to include in the POST request.
            max_retries (int): Maximum number of retries for the request.
            delay (int): Delay in seconds between retries.
        
        Returns:
            dict: The JSON response from the server.
        
        Raises:
            Exception: If all retry attempts fail.
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=6000)
                response.raise_for_status()
                response = response.json()
                if response:
                    return response
                
                print(f"Empty response received (attempt {attempt + 1}/{max_retries}). Retrying...")
            
            except requests.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}, payload:{str(payload)}")
            except ValueError as e:
                print(f"Failed to parse JSON response (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                print(f"Unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception(f"All {max_retries} attempts to contact {url} have failed.")
            
            sleep_for = delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(sleep_for)
            
        raise Exception(f"All {max_retries} attempts to contact {url} have failed.")

    def _format_search_response(self, queries: list[str], results: list[list[dict]]) -> str:
        """
        Format the search response into a readable string.

        Args:
            queries (list[str]): The list of search queries.
            results (list[list[dict]]): The list of search results for each query.
        
        Returns:
            str: The formatted search results as a string.
        """
        def passage2string(retrieval_result):
            format_reference = ""
            for idx, doc in enumerate(retrieval_result):
                try:
                    content_lines = doc['document']['contents'].split('\n')
                    title = content_lines[0] 
                    url = doc['document']['url']
                    text = "\n".join(content_lines[1:]).strip()
                    format_reference += f"[Doc {idx+1}](Title: {title})(URL: {url}):\n{text}\n"
                except (KeyError, IndexError) as e:
                    print(f"Error formatting document: {e}")
            return format_reference
        
        content = ""
        for query, result in zip(queries, results):
            content += f"A search for '{query}' found {len(result)} results:\n\n## Web Results:\n" + passage2string(result) + "\n"
        return content

    def _format_tool_output(self, tool_output: dict) -> str:
        """
        Format the tool output dictionary into a string with length constraints.

        Args:
            tool_output (dict): The tool output dictionary to format.
        
        Returns:
            str: The formatted tool output string (truncated if exceeds max_tool_length).
        """
        filtered_dict = {k: v for k, v in tool_output.items() 
                             if k not in ["tool_name", "query"]}
        res_str = "\n".join(str(v) for v in filtered_dict.values())
        
        encoded = self.tokenizer.encode(res_str)
        if len(encoded) > self.max_tool_length:
            res_str = self.tokenizer.decode(encoded[:self.max_tool_length])
        return res_str
        
    def _calculate_reward(self, data: Any, stage: str) -> tuple[float, dict]:
        """
        Calculate the reward based on the provided data and stage.

        Args:
            data (Any): The data to evaluate for reward calculation.
            stage (WebSearcherRewardStage): The current stage of the environment.
        
        Returns:
            reward (float): The calculated reward.
            metadata (dict): Additional metadata related to the reward calculation.
        """
        reward_output = self.reward_fn(
            eval_data=data,
            stage=stage,
            task_info=self.task or {}
        )
        return reward_output.reward, reward_output.metadata
    
    def _build_info(self, action: dict, metadata: dict) -> dict:
        """
        Build the info dictionary for the step result.

        Args:
            action (dict): The action taken by the agent.
            metadata (dict): Additional metadata from reward calculation.
        
        Returns:
            info (dict): The constructed info dictionary.
        """
        return {
            "response": action,
            "metadata": metadata or None
        }
    
    def _default_handler(self, *args, **kwargs) -> None:
        """
        Default handler for unsupported tools.
        
        Raises:
            NotImplementedError: Always raised to indicate unsupported tool.
        """
        raise NotImplementedError("Unsupported tool called.")
