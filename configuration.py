import os
from dataclasses import dataclass, field, fields
from typing import Optional, Any
from langchain_core.runnables import RunnableConfig

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the research agent."""
    research_model: str = "google_genai:gemini-2.5-pro"
    research_model_max_tokens: int = 4096
    allow_clarification: bool = True
    max_structured_output_retries: int = 3
    max_concurrent_research_units: int = 3
    max_researcher_iterations: int = 3
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config.get("configurable", {}) if config else {}
        field_names = [f.name for f in fields(cls)]
        values: dict[str, Any] = {
            field_name: os.environ.get(field_name.upper(), configurable.get(field_name))
            for field_name in field_names
        }
        return cls(**{k: v for k, v in values.items() if v is not None})

    class Config:
        """Pydantic configuration."""
        
        arbitrary_types_allowed = True