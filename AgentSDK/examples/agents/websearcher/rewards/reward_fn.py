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

import ast
import re
from typing import Any

from rllm.rewards.reward_fn import RewardOutput

from examples.agents.websearcher.websearcher_tool_parser import WebSearcherKeyword
from examples.agents.websearcher.rewards.reward_config import WebSearcherRewardStage, WebSearcherRewardFnConfig, WebSearcherResultDocs
from examples.agents.websearcher.rewards.utils import f1_score


def websearcher_reward_fn(eval_data: Any, stage: WebSearcherRewardStage, task_info=None):
    reward_config = WebSearcherRewardFnConfig()
    reward_fn = WebSearcherRewardFn(reward_config)
    return reward_fn(eval_data, stage, task_info)


class WebSearcherRewardFn:
    def __init__(self, config: WebSearcherRewardFnConfig):
        self.config = config
    
    def __call__(self, eval_data: dict | str, stage: WebSearcherRewardStage, task_info: dict):
        if not isinstance(eval_data, (dict, str)):
            raise ValueError(f"eval_data must be a dict or str, but got {type(eval_data)}")
        if not isinstance(stage, WebSearcherRewardStage):
            raise ValueError(f"stage must be a WebSearcherRewardStage, but got {type(stage)}")
        if not isinstance(task_info, dict):
            raise ValueError(f"task_info must be a dict, but got {type(task_info)}")
        
        if stage == WebSearcherRewardStage.TOOLS_FORMAT:
            reward, obs = self._handle_tool_format(eval_data)
        elif stage == WebSearcherRewardStage.TOOLS_RETURN:
            reward, obs = self._handle_tool_return(eval_data)
        elif stage == WebSearcherRewardStage.DONE:
            reward, obs = self._handle_answer(eval_data, task_info)
        else:
            raise ValueError(f"Unsupported stage: {stage}")

        return RewardOutput(reward=reward, metadata={"reward_obs": obs})
    
    @staticmethod
    def _verify_tool(tool_name: str, tool_args: str):
        """Validate the format of tool and query parameters."""
        # 1. Check if tool in the expected tool list
        from examples.agents.websearcher.websearcher_tools import websearcher_tools as tools_all
        if tool_name not in tools_all:
            if tool_name == "error_tool":
                return False, f"Tool parsing error, unable to extract correct tool name and parameters"
            else:
                return False, f"Error, invalid tool, '{tool_name}' is not in the given tool list."

        # 2. Check the format of query
        if not tool_args or not isinstance(tool_args, dict):
            return False, "Error, invalid query, the JSON format is incorrect and cannot be parsed."

        def get_type_from_string(tool_arg_type: str):
            """Converts a type string to its corresponding Python type object."""
            base_type = tool_arg_type.split("[")[0].lower() if "[" in tool_arg_type else tool_arg_type
            type_map = {
                "int": int,
                "str": str,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "any": Any,
            }
            if base_type not in type_map:
                raise ValueError(f"Unsupported type: {tool_arg_type}")
            return type_map[base_type]

        # 3、Validate parameters of tool
        tool_info = tools_all[tool_name]
        tool_args_expected = tool_info['parameters']['properties']
        for arg_name, arg_value in tool_args.items():
            if arg_name not in tool_args_expected:
                return False, f"'{arg_name}' is not in the expected tool arguments."
            tool_arg_info = tool_args_expected[arg_name]
            tool_arg_type = get_type_from_string(tool_arg_info["type"])

            if not isinstance(arg_value, tool_arg_type):
                return False, f"error, invalid value type. The {arg_name} should be of the {tool_arg_type}."
        return True, ""
    
    @staticmethod
    def _extract_answer(text: str):
        """
        Extracts and normalizes text using regex pattern matching.
        
        Args:
            text: Input text containing potential answer.
            
        Returns:
            Normalized answer string or empty string if no match found.
        """
        zh_colon = WebSearcherKeyword.ZH_COLON
        en_colon = WebSearcherKeyword.EN_COLON
        zh_comma = WebSearcherKeyword.ZH_COMMA
        en_comma = WebSearcherKeyword.EN_COMMA
        answer_pattern = WebSearcherKeyword.ANSWER_PATTERN

        matches = re.findall(answer_pattern, text)
        if not matches:
            return ""
        answer = matches[0].replace(zh_colon, en_colon).replace(zh_comma, en_comma)
        return answer
    
    @staticmethod
    def _verify_result(ground_truth: str, model_response: str):
        """
        Verifies the model's response against ground truth and returns reward and observation.

        Args:
            ground_truth: Expected answer in either of two formats:
                        1. List format (e.g. ["Enid Blyton", "author"])
                        2. String representation of list (e.g. "['Enid Blyton']")
            model_response: String containing the model's generated response to be checked

        Returns:
            A tuple containing:
            - reward: Reward value indicating answer correctness
            - obs: Observation string describing correctness level
        """
        # Process model response: convert to lowercase, extract list content, 
        # and split into multiple responses
        model_response = WebSearcherRewardFn._process_model_response(model_response)
        # Process ground truth: unify into list format, convert elements to 
        # lowercase, and strip whitespace
        ground_truth = WebSearcherRewardFn._process_ground_truth(ground_truth)
        # Reward for the model_response
        reward, obs = WebSearcherRewardFn._calculate_reward(model_response, ground_truth)
        return reward, obs
    
    @staticmethod
    def _process_model_response(model_response: str):
        """
        Processes the raw model response string.

        Args:
            model_response: Original model response string

        Returns:
            List of processed response items where each item is:
            - Convert to lowercase
            - Stripped of leading/trailing whitespace
            - Extracted from list brackets if present
        """
        model_response = model_response.lower()
        if '[' in model_response:
            model_response = model_response.split('[')[1]
        if ']' in model_response:
            model_response = model_response.split(']')[0]
        return [item.strip() for item in model_response.split(',')]
    
    @staticmethod
    def _process_ground_truth(ground_truth: str | list):
        """
        Processes ground truth into standardized format.

        Args:
            ground_truth: Input in either:
                        - List format
                        - String representation of list
                        - normal string format

        Returns:
            Standardized list of ground truth items where each item is:
            - Convert to lowercase
            - Stripped of leading/trailing whitespace
        """
        if isinstance(ground_truth, list):
            return [str(item).lower().strip() for item in ground_truth]
        
        if isinstance(ground_truth, str) and ground_truth.startswith('[') and ground_truth.endswith(']'):
            try:
                parsed = ast.literal_eval(ground_truth)
                return [str(item).lower().strip() for item in parsed]
            except Exception as e:
                raise ValueError(f"Invalid ground_truth format:{ground_truth}") from e
        
        if isinstance(ground_truth, str):
            return [str(ground_truth).lower().strip()]
        
        raise ValueError(f"Unsupported ground_truth format:{ground_truth}")
    
    @staticmethod
    def _calculate_reward(model_response: list, ground_truth: list):
        """
        Calculates reward based on model response and ground truth.

        Args:
            model_response: Processed model response
            ground_truth: Processed ground truth

        Returns:
            Tuple containing:
            - Reward value based on similarity score
            - Observation string describing correctness level (e.g. CORRECT, PARTIALLY_CORRECT)

        Reward calculation logic:
        1. Handles empty response/correct cases
        2. Calculates F1 score between response and each ground truth
        3. Applies reward multipliers based on match quality
        4. Ensures reward within [error_reward, correct_reward] range
        """
        # Initialize reward parameters
        ERROR_REWARD = WebSearcherRewardFnConfig.res_incorrect
        NULL_REWARD = WebSearcherRewardFnConfig.res_null
        CORRECT_REWARD = WebSearcherRewardFnConfig.res_correct
        EPS_LOWER = 0.2
        EPS_UPPER = 0.00001

        # Handle edge cases
        if not model_response:
            return NULL_REWARD, WebSearcherResultDocs.RESPONSE_EMPTY.value
        if not ground_truth:
            return 0, WebSearcherResultDocs.GROUND_TRUTH_EMPTY.value
        
        # Special case: invalid question
        gt_invalid = "the question is invalid." in ground_truth
        resp_invalid = "the question is invalid." in model_response
        
        if gt_invalid != resp_invalid:
            return ERROR_REWARD, WebSearcherResultDocs.INCORRECT.value
        if gt_invalid:
            return CORRECT_REWARD, WebSearcherResultDocs.CORRECT.value
        
        # Compute similarity-based reward
        per_answer_true = CORRECT_REWARD / len(ground_truth)
        per_answer_false = ERROR_REWARD / len(model_response)
        reward = 0
        for response in model_response:
            best_f1_score = 0.0
            best_match = ""
            
            for gt in ground_truth:
                f1 = f1_score(response, gt)
                if f1 > best_f1_score:
                    best_f1_score = f1
                    best_match = gt
            
            if best_f1_score > 0.0:
                reward += best_f1_score * per_answer_true
                ground_truth.remove(best_match)
            else:
                reward += per_answer_false
        
        # Apply reward constraints
        if reward < EPS_LOWER:
            return ERROR_REWARD, WebSearcherResultDocs.INCORRECT.value
        if reward > CORRECT_REWARD - EPS_UPPER:
            return CORRECT_REWARD, WebSearcherResultDocs.CORRECT.value
        
        return reward, WebSearcherResultDocs.PARTIALLY_CORRECT.value
    
    def _handle_tool_format(self, eval_data: dict):
        """
        Handle reward calculation for tool format validation stage
        
        Validates the format of tool calls, including tool names and parameters legality.
        Subtracts negative reward for format errors.
        
        Args:
            eval_data: List of tool calls, each containing tool name and parameters
            
        Returns:
            tuple: (reward value, observation) - Negative reward indicates format error, 
                   observation describes the error details
        """
        tool_name = eval_data.get("function").get("name", "").strip()
        tool_args = eval_data.get("function").get("arguments", "")

        if tool_args:
            is_format_ok, obs = WebSearcherRewardFn._verify_tool(tool_name, tool_args)
        else:
            is_format_ok, obs = False, "Tool arguments are empty."
        
        if not is_format_ok:
            reward = self.config.format_reward_neg
            obs = obs if obs else "error, format error for websearcher function call."
        else:
            reward = 0.0
        return float(reward), obs
    
    def _handle_tool_return(self, eval_data: dict):
        """
        Handle reward calculation for tool return results stage
        
        Awards rewards based on the quality of tool execution results, including 
        empty returns, error cases, and successful cases.
        Different return states correspond to different reward values.
        
        Args:
            action: Dictionary containing tool outputs with tool_outputs key
            
        Returns:
            tuple: (reward value, observation) - Reward value determined by return quality, 
                   observation describes the return status
        """
        tool_return = next(iter(eval_data.get("tool_output", {}).values()), "")
        obs = tool_return.strip()
        if len(tool_return) < 10:
            reward = self.config.format_reward_nofound
            obs = "found nothing, probably due to irrelevant query or inaccurate input parameters"
        elif "error_output" in tool_return:
            reward = self.config.format_reward_err
        else:
            reward = self.config.format_reward_pos
        return float(reward), obs
    
    def _handle_answer(self, eval_data: str, task_info: dict):
        """
        Handle reward calculation for completion stage
        
        In the final answer stage, uses F1 score to evaluate the match between 
        model output and ground truth.
        Calculates final reward based on matching results and outputs detailed information for debugging.
        
        Args:
            action: Final answer string generated by the model
            task_info: Dictionary containing task information, especially the ground_truth field
            
        Returns:
            tuple: (reward value, observation) - Reward value is F1 score, 
                   observation contains matching details
        """
        answer = WebSearcherRewardFn._extract_answer(eval_data)
        ground_truth = task_info.get("ground_truth", "") if task_info else ""
        reward, obs = WebSearcherRewardFn._verify_result(ground_truth, answer)
        print(f"answer: {answer}\nground_truth: {ground_truth}\nreward: {reward}")
        return float(reward), obs