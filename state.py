from typing import List, Optional, Literal, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
import operator

# --- 1. The Graph State ---
class AgentState(TypedDict):
    """
    The state of the Account Deep Research Agent.
    """
    messages: Annotated[List[AnyMessage], operator.add] # Append-only message history
    user_query: str                  
    clarification_loop_count: int    
    
    # Fields populated by the Clarification Node
    status: Literal["CLARIFICATION_NEEDED", "READY_FOR_RESEARCH", "REJECTED"]
    buyer_entity: Optional[str]
    buyer_domain: Optional[str]
    seller_entity: Optional[str]
    research_focus: Optional[str]
    rejection_message: Optional[str]
    research_brief: Optional[str] # Populated later

# --- 2. The Structured Output Schema ---
class ClarificationAnalysis(BaseModel):
    """
    Structured output for the Clarification Analyst.
    Enforces the JSON format required by the prompt.
    """
    status: Literal["CLARIFICATION_NEEDED", "READY_FOR_RESEARCH", "REJECTED"] = Field(
        ..., description="The decision status based on the analysis criteria."
    )
    
    # Scenario A: Clarification Needed
    reason: Optional[str] = Field(
        None, description="Brief explanation of what is missing or ambiguous."
    )
    questions: Optional[List[str]] = Field(
        None, description="List of specific questions to ask the user."
    )
    
    # Scenario B: Ready
    buyer_entity: Optional[str] = Field(None, description="Name of the target company.")
    buyer_domain: Optional[str] = Field(None, description="Domain of the target company.")
    seller_entity: Optional[str] = Field(None, description="Name of the requesting company.")
    research_focus: Optional[str] = Field(None, description="Summary of user intent.")
    
    # Scenario C: Rejected
    message: Optional[str] = Field(None, description="Polite refusal message for unsafe inputs.")