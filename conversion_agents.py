"""
Strands-Compatible Conversion Agents for C to Java Code Conversion
Senior AWS Engineer Implementation - Production Ready

This module implements conversion agents using AWS Strands framework while preserving
the critical BedrockInference functionality for token limit handling and continuation.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Import strands framework
from strands import Agent
from strands.session import SessionManager

# Import all prompts from separate file
from prompts import (
    CODE_ANALYSIS_SYSTEM_PROMPT, get_code_analysis_prompt,
    CONVERSION_SYSTEM_PROMPT, get_conversion_prompt,
    VALIDATION_SYSTEM_PROMPT, get_validation_prompt,
    SECURITY_ASSESSMENT_SYSTEM_PROMPT, get_security_assessment_prompt,
    FEEDBACK_SYSTEM_PROMPT, get_feedback_prompt,
    INTEGRATION_SYSTEM_PROMPT, get_integration_prompt,
    DBIO_CONVERSION_SYSTEM_PROMPT, get_dbio_conversion_prompt
)

logger = logging.getLogger(__name__)

@dataclass
class ConversionContext:
    """Enhanced context data structure for strands compatibility"""
    c_code: str
    java_code: Optional[str] = None
    file_metadata: Optional[Dict] = None
    validation_results: Optional[Dict] = None
    security_results: Optional[Dict] = None
    feedback_history: Optional[List[Dict]] = None
    analysis_results: Optional[Dict] = None
    session_id: Optional[str] = None
    agent_trace: Optional[List[str]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.feedback_history is None:
            self.feedback_history = []
        if self.agent_trace is None:
            self.agent_trace = []

    def add_trace(self, agent_name: str, action: str):
        """Add tracing information for debugging and monitoring"""
        self.agent_trace.append(f"{agent_name}: {action}")

class BaseStrandsConversionAgent(ABC):
    """
    Base agent class that combines Strands framework with custom BedrockInference
    
    This hybrid approach uses Strands for agent lifecycle and session management
    while preserving the critical BedrockInference for token handling.
    """
    
    def __init__(self, name: str, bedrock_inference, system_prompt: str):
        self.name = name
        self.bedrock = bedrock_inference
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Create strands agent for session management and structure
        # Note: We don't pass a model since we use custom BedrockInference
        self.strands_agent = Agent(
            name=name,
            system_prompt=system_prompt,
            # No model parameter - we handle inference manually
        )
        
        self.logger.info(f"Initialized {name} with Strands framework")
    
    @abstractmethod
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Execute the agent's task asynchronously"""
        pass
    
    def log_info(self, message: str):
        """Log info message with agent name"""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """Log error message with agent name"""
        self.logger.error(f"[{self.name}] {message}")
    
    def log_debug(self, message: str):
        """Log debug message with agent name"""
        self.logger.debug(f"[{self.name}] {message}")

    def _safe_bedrock_call(self, prompt: str, use_continuation: bool = True) -> str:
        """
        Safe wrapper around BedrockInference calls with error handling
        
        Args:
            prompt: The prompt to send to the model
            use_continuation: Whether to use continuation for long responses
            
        Returns:
            The model response as a string
        """
        try:
            if use_continuation:
                return self.bedrock.stitch_output(prompt, self.system_prompt)
            else:
                return self.bedrock.simple_inference(prompt, self.system_prompt)
        except Exception as e:
            self.log_error(f"Bedrock inference failed: {str(e)}")
            raise

class StrandsCodeAnalysisAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for analyzing C codebase structure and dependencies"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_code_analysis_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=CODE_ANALYSIS_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Analyze C codebase structure asynchronously"""
        self.log_info("Starting C codebase analysis...")
        context.add_trace(self.name, "analysis_started")
        
        try:
            # Use the prompt utility function
            analysis_prompt = get_code_analysis_prompt(context.c_code)
            
            # Use our custom BedrockInference in executor to avoid blocking
            analysis_response = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, analysis_prompt, False
            )
            start = analysis_response.find('{')
            end = analysis_response.rfind('}') + 1
            analysis_response = analysis_response[start: end]
            
            # Parse the analysis response
            try:
                analysis_results = json.loads(analysis_response)
            except json.JSONDecodeError:
                self.log_error("Failed to parse analysis response as JSON")
                analysis_results = {
                    "complexity": "medium",
                    "main_functions": [],
                    "dependencies": [],
                    "conversion_challenges": ["JSON parsing failed"],
                    "raw_response": analysis_response
                }
            
            # Update context
            context.analysis_results = analysis_results
            context.add_trace(self.name, "analysis_completed")
            
            self.log_info(f"Analysis completed. Complexity: {analysis_results.get('complexity', 'unknown')}")
            
            return {
                "success": True,
                "context": context,
                "analysis": analysis_results,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Analysis failed: {str(e)}")
            context.add_trace(self.name, f"analysis_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsConversionAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for transforming C code to Java/Spring framework code"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_conversion_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=CONVERSION_SYSTEM_PROMPT
        )
        self.bedrock = bedrock_inference
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Transform C code to Java/Spring code asynchronously"""
        self.log_info("Starting C to Java conversion...")
        context.add_trace(self.name, "conversion_started")
        
        try:
            # Use the prompt utility function
            conversion_prompt = get_conversion_prompt(context.c_code)
            
            # Use continuation for potentially long Java code generation
            java_code = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, conversion_prompt, True
            )
            
            # Update context
            context.java_code = java_code
            context.add_trace(self.name, "conversion_completed")
            
            self.log_info("C to Java conversion completed successfully")
            
            return {
                "success": True,
                "context": context,
                "java_code": java_code,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Conversion failed: {str(e)}")
            context.add_trace(self.name, f"conversion_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsValidationAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for verifying conversion completeness and accuracy"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_validation_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=VALIDATION_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Validate conversion quality asynchronously"""
        self.log_info("Starting conversion validation...")
        context.add_trace(self.name, "validation_started")
        
        if not context.java_code:
            return {
                "success": False,
                "error": "No Java code available for validation",
                "context": context,
                "agent_name": self.name
            }
        
        try:
            # Use the prompt utility function
            validation_prompt = get_validation_prompt(context.c_code, context.java_code)
            
            validation_response = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, validation_prompt, False
            )
            start = validation_response.find('{')
            end = validation_response.rfind('}') + 1
            validation_response = validation_response[start: end]
            # Parse validation response
            try:
                validation_results = json.loads(validation_response)
            except json.JSONDecodeError:
                self.log_error("Failed to parse validation response as JSON")
                validation_results = {
                    "is_complete": False,
                    "completeness_score": 0.5,
                    "issues": ["JSON parsing failed"],
                    "suggestions": ["Review validation response format"],
                    "raw_response": validation_response
                }
            is_complete = validation_results.get("is_complete", False)
            # Update context
            context.validation_results = validation_results
            context.add_trace(self.name, "validation_completed")
            
            self.log_info(f"Validation completed.")
            
            return {
                "success": True,
                "context": context,
                "validation": validation_results,
                "is_complete": is_complete,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Validation failed: {str(e)}")
            context.add_trace(self.name, f"validation_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsSecurityAssessmentAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for comprehensive security analysis of C and Java code"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_security_assessment_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=SECURITY_ASSESSMENT_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Perform security assessment on both C and Java code asynchronously"""
        self.log_info("Starting security assessment...")
        context.add_trace(self.name, "security_assessment_started")
        
        if not context.java_code:
            return {
                "success": False,
                "error": "No Java code available for security assessment",
                "context": context,
                "agent_name": self.name
            }
        
        try:
            # Use the prompt utility function
            security_prompt = get_security_assessment_prompt(context.c_code, context.java_code)
            
            security_response = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, security_prompt, False
            )
            
            # Extract JSON from response
            start = security_response.find('{')
            end = security_response.rfind('}') + 1
            security_response = security_response[start: end]
            
            # Parse security assessment response
            try:
                security_results = json.loads(security_response)
            except json.JSONDecodeError:
                self.log_error("Failed to parse security assessment response as JSON")
                security_results = {
                    "critical_vulnerabilities": [],
                    "security_risk_issues": [],
                    "secure_code_recommendations": ["JSON parsing failed - manual security review required"],
                    "spring_security_configurations": [],
                    "compliance_gaps": ["Assessment parsing failed"],
                    "migration_security_notes": ["Manual security review required"],
                    "raw_response": security_response
                }
            
            # Update context
            context.security_results = security_results
            context.add_trace(self.name, "security_assessment_completed")
            
            critical_count = len(security_results.get("critical_vulnerabilities", []))
            risk_count = len(security_results.get("security_risk_issues", []))
            
            self.log_info(f"Security assessment completed. Critical: {critical_count}, Risk Issues: {risk_count}")
            
            return {
                "success": True,
                "context": context,
                "security_assessment": security_results,
                "critical_vulnerabilities_count": critical_count,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Security assessment failed: {str(e)}")
            context.add_trace(self.name, f"security_assessment_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsFeedbackAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for improving code based on validation and security feedback"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_feedback_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=FEEDBACK_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Apply feedback to improve code asynchronously"""
        self.log_info("Starting feedback application...")
        context.add_trace(self.name, "feedback_started")
        
        if not context.validation_results:
            return {
                "success": False,
                "error": "No validation results available for feedback",
                "context": context,
                "agent_name": self.name
            }
        
        try:
            # Prepare security feedback if available
            security_feedback = ""
            if context.security_results:
                security_feedback = json.dumps(context.security_results, indent=2)
            
            # Use the updated prompt utility function with security feedback
            feedback_prompt = get_feedback_prompt(
                context.c_code, 
                context.java_code, 
                json.dumps(context.validation_results, indent=2),
                security_feedback
            )
            
            # Use continuation for potentially long improved code
            improved_java_code = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, feedback_prompt, True
            )
            
            # Store feedback history
            feedback_entry = {
                "iteration": len(context.feedback_history) + 1,
                "original_issues": context.validation_results.get("issues", []),
                "improved_code": improved_java_code
            }
            context.feedback_history.append(feedback_entry)
            
            # Update context with improved code
            context.java_code = improved_java_code
            context.add_trace(self.name, "feedback_applied")
            
            self.log_info(f"Feedback applied successfully. Iteration: {feedback_entry['iteration']}")
            
            return {
                "success": True,
                "context": context,
                "improved_code": improved_java_code,
                "feedback_iteration": feedback_entry["iteration"],
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Feedback application failed: {str(e)}")
            context.add_trace(self.name, f"feedback_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsIntegrationAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for combining multiple converted files"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_integration_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=INTEGRATION_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Integrate multiple converted files asynchronously"""
        self.log_info("Starting file integration...")
        context.add_trace(self.name, "integration_started")
        
        try:
            # For single file conversion, return as-is
            if not hasattr(context, 'related_files') or not context.related_files:
                self.log_info("Single file conversion - no integration needed")
                return {
                    "success": True,
                    "context": context,
                    "integrated_code": context.java_code,
                    "agent_name": self.name
                }
            
            # Use the prompt utility function for multiple files
            integration_prompt = get_integration_prompt(
                context.java_code, 
                getattr(context, 'related_files', [])
            )
            
            integrated_code = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, integration_prompt, True
            )
            
            context.java_code = integrated_code
            context.add_trace(self.name, "integration_completed")
            
            self.log_info("File integration completed successfully")
            
            return {
                "success": True,
                "context": context,
                "integrated_code": integrated_code,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"Integration failed: {str(e)}")
            context.add_trace(self.name, f"integration_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

class StrandsDBIOConversionAgent(BaseStrandsConversionAgent):
    """Strands-compatible agent for converting SQL DBIO C code to MyBatis XML"""
    
    def __init__(self, bedrock_inference):
        super().__init__(
            name="strands_dbio_conversion_agent",
            bedrock_inference=bedrock_inference,
            system_prompt=DBIO_CONVERSION_SYSTEM_PROMPT
        )
    
    async def execute_async(self, context: ConversionContext) -> Dict[str, Any]:
        """Convert DBIO C code to MyBatis XML asynchronously"""
        self.log_info("Starting DBIO to MyBatis conversion...")
        context.add_trace(self.name, "dbio_conversion_started")
        
        try:
            # Use the prompt utility function
            dbio_prompt = get_dbio_conversion_prompt(context.c_code)
            
            # Use continuation for potentially long XML generation
            mybatis_xml = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_bedrock_call, dbio_prompt, True
            )
            
            # Update context
            context.java_code = mybatis_xml  # Store XML in java_code field
            context.add_trace(self.name, "dbio_conversion_completed")
            
            self.log_info("DBIO to MyBatis conversion completed successfully")
            
            return {
                "success": True,
                "context": context,
                "mybatis_xml": mybatis_xml,
                "agent_name": self.name
            }
            
        except Exception as e:
            self.log_error(f"DBIO conversion failed: {str(e)}")
            context.add_trace(self.name, f"dbio_conversion_failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "agent_name": self.name
            }

# Factory function for creating agents
def create_strands_agents(bedrock_inference) -> Dict[str, BaseStrandsConversionAgent]:
    """
    Factory function to create all strands-compatible conversion agents
    
    Args:
        bedrock_inference: The BedrockInference instance to use
        
    Returns:
        Dictionary mapping agent names to agent instances
    """
    agents = {
        "code_analysis_agent": StrandsCodeAnalysisAgent(bedrock_inference),
        "conversion_agent": StrandsConversionAgent(bedrock_inference),
        "validation_agent": StrandsValidationAgent(bedrock_inference),
        "security_assessment_agent": StrandsSecurityAssessmentAgent(bedrock_inference),
        "feedback_agent": StrandsFeedbackAgent(bedrock_inference),
        "integration_agent": StrandsIntegrationAgent(bedrock_inference),
        "dbio_conversion_agent": StrandsDBIOConversionAgent(bedrock_inference)
    }
    
    logger.info(f"Created {len(agents)} strands-compatible conversion agents")
    return agents

# Utility functions for backward compatibility and testing
async def test_agent_creation(bedrock_inference):
    """Test function to verify all agents can be created successfully"""
    try:
        agents = create_strands_agents(bedrock_inference)
        logger.info("✅ All strands agents created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Agent creation failed: {str(e)}")
        return False
