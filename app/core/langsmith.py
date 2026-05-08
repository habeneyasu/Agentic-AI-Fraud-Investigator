import os
from typing import Optional, Dict, Any
from langsmith import Client
from langsmith.config import LANGCHAIN_TRACING_V2_ENV_VAR
from app.core.config import LangSmithConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class LangSmithManager:
    """Manages LangSmith observability for the fraud investigation system."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.enabled = LangSmithConfig.enabled
        self.project = LangSmithConfig.project
        
    def initialize(self) -> None:
        """Initialize LangSmith client and configure tracing."""
        if not self.enabled:
            logger.info("LangSmith is disabled")
            return
            
        try:
            # Set environment variables for LangSmith
            if LangSmithConfig.api_key:
                os.environ["LANGCHAIN_API_KEY"] = LangSmithConfig.api_key
            
            if LangSmithConfig.endpoint:
                os.environ["LANGCHAIN_ENDPOINT"] = LangSmithConfig.endpoint
                
            os.environ["LANGCHAIN_PROJECT"] = self.project
            os.environ[LANGCHAIN_TRACING_V2_ENV_VAR] = str(LangSmithConfig.tracing).lower()
            
            # Initialize client
            self.client = Client(
                api_key=LangSmithConfig.api_key,
                api_url=LangSmithConfig.endpoint
            )
            
            logger.info("LangSmith initialized successfully", project=self.project)
            
        except Exception as e:
            logger.error("Failed to initialize LangSmith", error=str(e))
            self.enabled = False
    
    def create_run(
        self,
        name: str,
        inputs: Dict[str, Any],
        run_type: str = "chain",
        tags: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Create a new LangSmith run for tracking."""
        if not self.enabled or not self.client:
            return None
            
        try:
            # Add fraud investigation specific metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "system": "fraud_investigator",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "version": "1.0.0"
            })
            
            run_id = self.client.create_run(
                name=name,
                inputs=inputs,
                run_type=run_type,
                tags=tags or ["fraud-investigation"],
                project_name=self.project,
                metadata=metadata
            )
            
            logger.debug("Created LangSmith run", run_id=run_id, name=name)
            return run_id
            
        except Exception as e:
            logger.error("Failed to create LangSmith run", error=str(e))
            return None
    
    def end_run(
        self,
        run_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """End a LangSmith run with results or error."""
        if not self.enabled or not self.client or not run_id:
            return
            
        try:
            self.client.end_run(
                run_id=run_id,
                outputs=outputs,
                error=error
            )
            
            if error:
                logger.warning("LangSmith run ended with error", run_id=run_id, error=error)
            else:
                logger.debug("LangSmith run completed successfully", run_id=run_id)
                
        except Exception as e:
            logger.error("Failed to end LangSmith run", run_id=run_id, error=str(e))
    
    def log_feedback(
        self,
        run_id: str,
        key: str,
        score: Optional[float] = None,
        value: Optional[str] = None,
        comment: Optional[str] = None
    ) -> None:
        """Log feedback for a LangSmith run."""
        if not self.enabled or not self.client or not run_id:
            return
            
        try:
            self.client.create_feedback(
                run_id=run_id,
                key=key,
                score=score,
                value=value,
                comment=comment
            )
            
            logger.debug("Logged feedback for LangSmith run", run_id=run_id, key=key)
            
        except Exception as e:
            logger.error("Failed to log LangSmith feedback", run_id=run_id, error=str(e))
    
    def create_dataset(
        self,
        name: str,
        description: str,
        data: list
    ) -> Optional[str]:
        """Create a dataset for evaluation."""
        if not self.enabled or not self.client:
            return None
            
        try:
            dataset = self.client.create_dataset(
                dataset_name=name,
                description=description,
                data=data
            )
            
            logger.info("Created LangSmith dataset", name=name, dataset_id=dataset.id)
            return dataset.id
            
        except Exception as e:
            logger.error("Failed to create LangSmith dataset", name=name, error=str(e))
            return None
    
    def get_run_metrics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific run."""
        if not self.enabled or not self.client or not run_id:
            return None
            
        try:
            # This would require additional LangSmith client methods
            # For now, return basic info
            return {"run_id": run_id, "status": "retrieved"}
            
        except Exception as e:
            logger.error("Failed to get LangSmith run metrics", run_id=run_id, error=str(e))
            return None


# Global LangSmith manager instance
langsmith_manager = LangSmithManager()


def get_langsmith_manager() -> LangSmithManager:
    """Get the global LangSmith manager instance."""
    return langsmith_manager


def initialize_langsmith() -> None:
    """Initialize LangSmith for the application."""
    langsmith_manager.initialize()


# Decorator for automatic LangSmith tracking
def track_langsmith(
    name: str,
    run_type: str = "chain",
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Decorator to automatically track function execution with LangSmith."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not langsmith_manager.enabled:
                return func(*args, **kwargs)
            
            # Create run
            run_id = langsmith_manager.create_run(
                name=name,
                inputs={"args": str(args), "kwargs": str(kwargs)},
                run_type=run_type,
                tags=tags,
                metadata=metadata
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # End run successfully
                langsmith_manager.end_run(
                    run_id=run_id,
                    outputs={"result": str(result)}
                )
                
                return result
                
            except Exception as e:
                # End run with error
                langsmith_manager.end_run(
                    run_id=run_id,
                    error=str(e)
                )
                raise
                
        return wrapper
    return decorator
