# Search Tools Simulation - OASIS

原文链接: https://docs.oasis.camel-ai.org/cookbooks/search_tools_simulation

[OASIS home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/camel-6d2d1ad0/logo/normal_logo.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/camel-6d2d1ad0/logo/white_logo.svg)](https://www.camel-ai.org/)Search...⌘KSearch...NavigationCookbooksSearch Tools Simulation[Guides](/introduction)- [Documentation](https://docs.oasis.camel-ai.org/)
- [Community](https://discord.com/invite/CNcNpquyDc)
- [Blog](https://www.camel-ai.org/blogs/oasis)
##### Get Started

* [Introduction](/introduction)
* [Quickstart](/quickstart)
##### Overview

* [Overview](/overview)
##### Key Modules

* [Environment](/key_modules/environments)
* [Agent Graph](/key_modules/agent_graph)
* [Agent Profile](/user_generation/generation)
* [Social Agent](/key_modules/social_agent)
* [Models](/key_modules/models)
* [Toolkits](/key_modules/toolkits)
* [Platform](/key_modules/platform)
* [Actions](/key_modules/actions)
##### Cookbooks

* [Twitter Simulation](/cookbooks/twitter_simulation)
* [Reddit Simulation](/cookbooks/reddit_simulation)
* [Sympy Tools Simulation](/cookbooks/sympy_tools_simulation)
* [Search Tools Simulation](/cookbooks/search_tools_simulation)
* [Custom Prompt Simulation](/cookbooks/custom_prompt_simulation)
* [Interview](/cookbooks/twitter_interview)
##### Visualization

* [Visualization](/visualization/visualization)
Cookbooks
# Search Tools Simulation

This cookbook provides a example of an agent uses search tools to get information.

# [​](#search-tools-simulation)Search Tools Simulation

This cookbook provides a example of an agent uses search tools to get information.

Copy
```
import asyncio
import os

from camel.models import ModelFactory
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType, ModelType

import oasis
from oasis import (ActionType, AgentGraph, LLMAction, ManualAction,
                   SocialAgent, UserInfo)


async def main():
    # Define the model for the agents
    openai_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    # Define the available actions for the agents
    available_actions = [
        ActionType.LIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.FOLLOW,
    ]

    agent_graph = AgentGraph()
    agent_1 = SocialAgent(
        agent_id=0,
        user_info=UserInfo(
            user_name="ali",
            name="Alice",
            description="A girl",
            profile=None,
            recsys_type="reddit",
        ),
        agent_graph=agent_graph,
        model=openai_model,
        available_actions=available_actions,
    )
    agent_graph.add_agent(agent_1)

    agent_2 = SocialAgent(agent_id=1,
                          user_info=UserInfo(
                              user_name="bubble",
                              name="Bob",
                              description="A boy",
                              profile=None,
                              recsys_type="reddit",
                          ),
                          tools=[SearchToolkit().search_duckduckgo],
                          agent_graph=agent_graph,
                          model=openai_model,
                          available_actions=[ActionType.CREATE_COMMENT],
                          single_iteration=False)
    agent_graph.add_agent(agent_2)

    # Define the path to the database
    db_path = "./data/reddit_simulation.db"

    # Delete the old database
    if os.path.exists(db_path):
        os.remove(db_path)

    # Make the environment
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
    )

    # Run the environment
    await env.reset()

    actions_1 = {
        env.agent_graph.get_agent(0): [
            ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={
                    "content":
                    "Can someone use duckduckgo tool now? I can not open it."
                    "If so, can you help me with searching the oasis?"
                })
        ]
    }
    await env.step(actions_1)

    for _ in range(3):
        action = {
            agent: LLMAction()
            for _, agent in env.agent_graph.get_agents()
        }
        await env.step(action)

    # Close the environment
    await env.close()


if __name__ == "__main__":
    asyncio.run(main())

```
[Sympy Tools Simulation](/cookbooks/sympy_tools_simulation)[Custom Prompt Simulation](/cookbooks/custom_prompt_simulation)On this page

* [Search Tools Simulation](#search-tools-simulation)
AssistantResponses are generated using AI and may contain mistakes.