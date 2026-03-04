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
import sys
import types
from concurrent.futures import as_completed
from queue import Queue
from threading import Thread
from typing import Any, Dict, List, Optional
from dataclasses import fields
import torch

from agentic_rl import Trajectory, BaseEngineWrapper, StepTrajectory, Step

verl = types.ModuleType("verl")
verl.protocol = types.ModuleType("verl.protocol")
verl.protocol.DataProto = object
verl.utils = types.ModuleType("verl.utils")
verl.utils.torch_functional = types.ModuleType("verl.utils.torch_functional")
verl.utils.torch_functional.get_response_mask = object
verl.utils.torch_functional.pad_2d_list_to_length = object
sys.modules["verl"] = verl
sys.modules["verl.protocol"] = verl.protocol
sys.modules["verl.utils"] = verl.utils
sys.modules["verl.utils.torch_functional"] = verl.utils.torch_functional

from examples.rllm.agent_execution_engine import AgentExecutionEngine, OpenAIRouter
from examples.agents.agents_mapping import get_agent_by_name


def dict_to_step_trajectory(result: Dict[str, Any]) -> StepTrajectory:
    step_objects = []
    for step_dict in result.get("steps", []):
        step_fields = {f.name: step_dict.get(f.name) for f in fields(Step) if f.name in step_dict}
        step_objects.append(Step(**step_fields))

    step_trajectory_fields = {
        "task": result.get("task"),
        "steps": step_objects,
    }

    base_trajectory_fields = {
        "prompt_tokens": result.get("prompt_tokens", torch.tensor([])),
        "response_tokens": result.get("response_tokens", torch.tensor([])),
        "response_masks": result.get("response_masks", torch.tensor([])),
        "idx": result.get("idx", 0),
        "trajectory_reward": result.get("trajectory_reward", 0.0),
        "chat_completions": result.get("chat_completions", []),
        "metrics": result.get("metrics", {})
    }

    merged_fields = {**base_trajectory_fields, **step_trajectory_fields}
    return StepTrajectory(**merged_fields)


class RllmEngineWrapper(BaseEngineWrapper):
    """
    Wrapper for RLLM agent execution engine with enhanced resource management.

    Provides high-level interface for agent trajectory generation with proper
    initailization, validation and cleanup.
    """

    # Default configuration for the RLLM agent
    DEFAULT_MAX_PROMPT_LENGTH = 8192
    DEFAULT_MAX_RESPONSE_LENGTH = 16384
    DEFAULT_N_PARALLEL_AGENTS = 8
    DEFAULT_MAX_STEPS = 128
    DEFAULT_ENV_CREATION_WORKERS = 64
    DEFAULT_AGENT_CREATION_WORKERS = 64

    def __init__(
        self,
        agent_name: str,
        tokenizer: Any,
        sampling_params: Optional[Dict[str, Any]] = None,
        max_prompt_length: int = DEFAULT_MAX_PROMPT_LENGTH,
        max_response_length: int = DEFAULT_MAX_RESPONSE_LENGTH,
        n_parallel_agents: int = DEFAULT_N_PARALLEL_AGENTS,
        max_steps: int = DEFAULT_MAX_STEPS,
        mode: str = "Token",
    ) -> None:
        """
        Initialize the RLLM Engine Wrapper.

        Args:
            agent_name (str): Name of the agent configuration to use.
            tokenizer (Any): Tokenizer instance for text processing.
            sampling_params (Optional[Dict[str, Any]]): Sampling parameters for model sampling.
            max_prompt_length (int): Maximum length of the prompt.
            max_response_length (int): Maximum length of the response.
            n_parallel_agents (int): Number of parallel agents to run.
            max_steps (int): Maximum steps per trajectory.
            mode (str): Trajectory generation mode, 'Token' for token-level rewards, or 'Step' for step-level rewards.

        Raises:
            ValueError / TypeError: If any of the parameters are invalid.
            ImportError: If required modules are not found.
        """
        # Initialize base class
        super().__init__(
            agent_name=agent_name,
            tokenizer=tokenizer,
            sampling_params=sampling_params,
            max_prompt_length=max_prompt_length,
            max_response_length=max_response_length,
            n_parallel_agents=n_parallel_agents,
            max_steps=max_steps
        )

        # Load agent configuration
        agent_config = get_agent_by_name(agent_name)
        print(f"Successfully retrieved configuration of {agent_name} agent")

        # Extract agent and environment classes and arguments
        self.agent_class = agent_config.agent_class
        self.env_class = agent_config.env_class
        self.agent_args = agent_config.agent_args
        self.env_args = agent_config.env_args

        # Trajectory generation mode
        self.mode = mode

    def initialize(self):
        """
        Perform necessary initialize procedure for agent engine

        Raises:
            RuntimeError: If initialization fails.
        """
        # Initialize the router
        try:
            self.router = OpenAIRouter(self.completions)
        except Exception as e:
            raise RuntimeError(f"Initialization of router failed: {e}") from e

        # Initialize the agent execution engine
        try:
            self.engine = AgentExecutionEngine(
                tokenizer=self.tokenizer,
                router=self.router,
                agent_class=self.agent_class,
                agent_args=self.agent_args,
                env_class=self.env_class,
                env_args=self.env_args,
                sampling_params=self.sampling_params,
                max_prompt_length=self.max_prompt_length,
                max_response_length=self.max_response_length,
                n_parallel_agents=self.n_parallel_agents,
                max_steps=self.max_steps
            )
        except Exception as e:
            raise RuntimeError(f"Initialization of agent execution engine failed: {e}") from e
        
        print(
            f"RLLM Engine Wrapper initialized with agent '{self.agent_name}' "
            f"with parallel agents: {self.n_parallel_agents}"
        )

    def init_envs_and_agents(self, tasks: List[dict]):
        """
        Initialize environments and agents for the given tasks.

        Args:
            tasks (List[dict]): List of task to initialize environment and agent for

        Raises:
            RuntimeError: If agents/envs update fails.
        """
        print(f"Initializing {len(tasks)} environments and agents...")

        # Create environments and agents in parallel
        envs = self._create_environments_parallel(tasks)
        agents = self._create_agents_parallel(len(envs))

        # Update the engine with the created envs and agents
        try:
            self.engine.update_envs_and_agents(envs, agents)
        except Exception as e:
            raise RuntimeError(f"Failed to update engine with created envs/agents: {e}") from e
        
        print(f"Successfully initialized {len(envs)} environments and {len(agents)} agents.")
    
    def generate_agent_trajectories_async(self, tasks: List[dict]) -> List[Trajectory]:
        """
        Generate agent trajectories asynchronously for the given tasks using the agent
        execution engine.

        This method runs the asynchronous trajectory_generator in a separate thread and
        collects results synchronously through a queue, allowing synchronous training
        loops to consume asynchronously generated trajectories.

        Args:
            tasks (List[dict]): List of task dictionaries containing 'question', 'ground_truth', etc.
        
        Returns:
            List[Trajectory]: List of generated agent trajectories.

        Raises:
            RuntimeError: If trajectory generation fails.
        """
        print(f"Generating trajectories asynchronously for {len(tasks)} tasks...")
        try:
            # Initialize environments and agents
            self.init_envs_and_agents(tasks)

            # Thread-safe queue to communication between threads
            # Prevent unbounded memory usage with maxsize
            results_queue: Queue = Queue(maxsize=1000)

            def trajectory_runner() -> None:
                """
                Thread target function to run the asynchronous trajectory generator
                and put results into the queue.
                """
                async def consume_trajectories() -> None:
                    try:
                        async for trajectory in self.engine.trajectory_generator(mode=self.mode):
                            results_queue.put(trajectory)
                        results_queue.put(None)  # Sentinel value to indicate completion
                    except Exception as e:
                        print(f"Error in trajectory generation: {e}")
                        results_queue.put(e)  # Put exception in the queue to indicate failure
                try:
                    asyncio.run(consume_trajectories())
                except Exception as e:
                    print(f"Error running trajectory generation: {e}")
                    results_queue.put(e)  # Put exception in the queue to indicate failure
            
            # Start the trajectory runner thread
            runner_thread = Thread(target=trajectory_runner, daemon=True, name="trajectory-generator-thread")
            runner_thread.start()

            # Collect results from the queue synchronously
            trajectories: List[Trajectory] = []
            while True:
                try:
                    result = results_queue.get(timeout=1000)  # Timeout to avoid indefinite blocking
                    if result is None:
                    # Completion sentinel
                        break  
                    elif isinstance(result, Exception):
                        # Error occurred in the trajectory generation
                        raise RuntimeError(f"Trajectory generation failed: {result}") from result
                    else:
                        # Valid trajectory result
                        if self.mode == 'Step':
                            traj = dict_to_step_trajectory(result)
                            trajectories.append(traj)
                        elif self.mode == 'Token':
                            trajectories.append(Trajectory(**result))
                        else:
                            raise ValueError(f"mode must be 'Token' or 'Step', got '{self.mode}'")
                except Exception as e:
                    print(f"Error collecting trajectory from queue: {e}")
                    raise RuntimeError(f"Error collecting trajectory from queue: {e}") from e
            
            print(f"Successfully generated {len(trajectories)} trajectories.")
            return trajectories
        
        except Exception as e:
            print(f"Failed to generate agent trajectories: {e}")
            raise RuntimeError(f"Failed to generate agent trajectories: {e}") from e

    def _create_environments_parallel(self, tasks: List[dict]) -> List[Any]:
        """
        Create environments in parallel for the given tasks using the engine's thread pool.

        Args:
            tasks (List[dict]): List of task to create environments for
        
        Raises:
            RuntimeError: If environment creation fails.
        """
        def _create_env(i: int) -> tuple[int, Any]:
            try:
                env_args_copy = self.env_args.copy()
                env_args_copy["task"] = tasks[i]
                env_args_copy["max_steps"] = self.max_steps
                env = self.env_class.from_dict(env_args_copy)
                return i, env
            except Exception as e:
                raise RuntimeError(f"Environment creation failed for task {i}: {e}") from e
            
        envs = [None] * len(tasks)

        # Check if executor is active and recreate if necessary
        self._ensure_executor_active("environment creation")

        # Submit environment creation tasks to the engine's thread pool executor instead of creating a new one
        futures = [
            self.engine.executor.submit(_create_env, i)
            for i in range(len(tasks))
        ]

        for future in as_completed(futures):
            i, env = future.result()
            envs[i] = env
        
        return envs
    
    def _create_agents_parallel(self, n_agents: int) -> List[Any]:
        """
        Create agents in parallel using the engine's thread pool.

        Args:
            n_agents (int): Number of agents to create

        Raises:
            RuntimeError: If agent creation fails.
        """
        def _create_agent(i: int) -> tuple[int, Any]:
            try:
                agent = self.agent_class(**self.agent_args)
                return i, agent
            except Exception as e:
                raise RuntimeError(f"Agent creation failed for agent {i}: {e}") from e
            
        agents = [None] * n_agents

        # Check if executor is active and recreate if necessary
        self._ensure_executor_active("agent creation")

        # Submit agent creation tasks to the engine's thread pool executor instead of creating a new one
        futures = [
            self.engine.executor.submit(_create_agent, i)
            for i in range(n_agents)
        ]

        for future in as_completed(futures):
            i, agent = future.result()
            agents[i] = agent
        
        return agents
    
    def _ensure_executor_active(self, context: str) -> None:
        """
        Ensure that the engine's thread pool executor is active.
        If it has been shut down, recreate it.

        Args:
            context (str): Description of the operation context for logging purposes.
        """
        if hasattr(self.engine.executor, "_shutdown") and self.engine.executor._shutdown:
            import concurrent.futures
            self.engine.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.engine.max_workers,
                thread_name_prefix="agent-env-executor"
            )
            print(
                f"Engine's thread pool executor has been shut down. "
                f"Recreating executor for {context}..."
            )
            