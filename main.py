import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

# Relative imports to work within the src package
from configuration import Configuration
from prompts import clarify_with_user_instructions
from state import AgentState, ClarificationAnalysis
from utils import (get_api_key_for_model, get_today_str)

# Initialize a configurable model
configurable_model = init_chat_model(
    "google_genai:gemini-2.5-pro",
    configurable_fields=("model", "max_tokens", "api_key"),
)

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> Command[Literal["write_research_brief", END]]:
    """Analyze user messages and ask clarifying questions if the research scope is unclear."""
    
    # 1. Configuration Check
    configurable = Configuration.from_runnable_config(config)
    if not configurable.allow_clarification:
        return Command(goto="write_research_brief")
    
    api_key = get_api_key_for_model(configurable.research_model, config)
    
    # Bind the key to the model
    bound_model = configurable_model.bind(api_key=api_key)

    # 2. Prepare Model with Structured Output
    # We use the schema defined in state.py
    clarification_model = bound_model.with_structured_output(ClarificationAnalysis)    
    
    # 3. Prepare Prompt
    messages = state.get("messages", [])
    prompt_content = clarify_with_user_instructions.replace("{date}", get_today_str())
    response = await clarification_model.ainvoke(
        [SystemMessage(content=prompt_content)] + messages
    )
    
    # We send the system instructions + the conversation history
    # This invokes the model to analyze the conversation
    response = await clarification_model.ainvoke(
        [SystemMessage(content=prompt_content)] + messages
    )
    
    # 4. Route based on Analysis
    if response.status == "CLARIFICATION_NEEDED":
        # Generate the clarifying question for the user
        question_text = response.reason + "\n\n" + "\n".join(response.questions or [])
        
        # Return END to wait for user input. The state is updated with the question.
        return Command(
            goto=END, 
            update={
                "messages": [AIMessage(content=question_text)],
                "status": "CLARIFICATION_NEEDED",
                "clarification_loop_count": state.get("clarification_loop_count", 0) + 1
            }
        )

    elif response.status == "REJECTED":
        # End the interaction if the request is unsafe
        return Command(
            goto=END,
            update={
                "messages": [AIMessage(content=response.message or "I cannot fulfill this request.")],
                "status": "REJECTED"
            }
        )

    else: # READY_FOR_RESEARCH
        # Proceed to the next node (writing the brief)
        # Update the state with the extracted entities
        return Command(
            goto="write_research_brief", 
            update={
                "status": "READY_FOR_RESEARCH",
                "buyer_entity": response.buyer_entity,
                "buyer_domain": response.buyer_domain,
                "seller_entity": response.seller_entity,
                "research_focus": response.research_focus,
                # Optional: Acknowledge the clear scope
                "messages": [AIMessage(content=f"Understood. Initiating research on {response.buyer_entity}...")]
            }
        )

async def write_research_brief(state: AgentState, config: RunnableConfig):
    """
    Placeholder for the research brief generation. 
    In the full implementation, this would use the extracted entities 
    (buyer_entity, etc.) to write a targeted brief.
    """
    # ... Logic to write brief ...
    return Command(goto=END, update={"research_brief": "Research Brief Placeholder"})

# --- Graph Definition ---

# Changed config_schema to context_schema to fix LangGraphDeprecatedSinceV10 error
workflow = StateGraph(AgentState, context_schema=Configuration)

# Add Nodes
workflow.add_node("clarify_with_user", clarify_with_user)
workflow.add_node("write_research_brief", write_research_brief)

# Add Edges
# Start directly with clarification
workflow.add_edge(START, "clarify_with_user")

# Compile the graph
graph = workflow.compile()

if __name__ == "__main__":
    import asyncio
    
    async def run_test():
        print("--- Starting Agent Test ---")
        
        # Simulating a user asking for a report
        initial_input = {
            "messages": [HumanMessage(content="I need a report on Salesforce. I am from ZoomInfo.")],
            "clarification_loop_count": 0
        }
        
        # Run the graph
        async for event in graph.astream(initial_input):
            for node_name, node_output in event.items():
                print(f"\n--- Node: {node_name} ---")
                if "messages" in node_output:
                    print(f"Agent Message: {node_output['messages'][-1].content}")
                if "status" in node_output:
                    print(f"Status: {node_output['status']}")
                if "buyer_entity" in node_output:
                    print(f"Buyer: {node_output.get('buyer_entity')}")

    # Execute the async function
    asyncio.run(run_test())