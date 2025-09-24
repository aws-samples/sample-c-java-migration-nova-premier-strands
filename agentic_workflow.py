"""
Strands-Compatible Agentic Workflow for C to Java Code Conversion
Senior AWS Engineer Implementation - Production Ready

This module implements a comprehensive agentic workflow using AWS Strands framework
while preserving the critical BedrockInference functionality for token handling.
"""

import boto3
import json
import time
import logging
import os
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from botocore.config import Config

# Import strands framework
from strands.session import SessionManager, FileSessionManager

# Import our strands-compatible agents
from conversion_agents import (
    ConversionContext,
    create_strands_agents,
    BaseStrandsConversionAgent
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    """Metadata for C files being converted - unchanged from original"""
    filename: str
    file_type: str  # 'c', 'header', 'dbio'
    complexity: str  # 'simple', 'medium', 'complex'
    line_count: int
    dependencies: List[str]

@dataclass
class ConversionResult:
    """Data class to store conversion results - unchanged from original"""
    success: bool
    java_code: str
    feedback_iterations: int
    processing_time: float
    validation_score: float
    errors: List[str]

class BedrockInference:
    """
    Enhanced Bedrock inference class with text prefilling for token limit handling
    
    CRITICAL: This class is preserved exactly as-is from the original implementation
    because it provides essential token continuation functionality that strands-agents
    doesn't support natively.
    """
    
    def __init__(self, region_name: str = "us-east-1", model_id: str = "us.amazon.nova-premier-v1:0"):
        self.config = Config(read_timeout=300)
        self.client = boto3.client("bedrock-runtime", config=self.config, region_name=region_name)
        self.model_id = model_id
        self.continue_prompt = {
            "role": "user",
            "content": [{"text": "Continue the code conversion from where you left off."}]
        }
        
        logger.info(f"Initialized Bedrock Inference with model: {model_id}")
    
    def generate_conversation(self, system_prompts: List[Dict], messages: List[Dict]) -> Tuple[Dict, str]:
        """Generate conversation with Bedrock Converse API"""
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system_prompts,
                inferenceConfig={
                    'maxTokens': 4096,
                    'temperature': 0.05,
                    'topP': 0.9
                }
            )
            
            stop_reason = response['stopReason']
            logger.debug(f"Stop reason: {stop_reason}")
            
            return response, stop_reason
            
        except Exception as e:
            logger.error(f"Error in generate_conversation: {str(e)}")
            raise
    
    def run_converse_inference_with_continuation(self, prompt: str, system_prompt: str) -> List[str]:
        """Run inference with continuation handling for large outputs"""
        ans_list = []
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        response, stop = self.generate_conversation([{'text': system_prompt}], messages)
        ans = response['output']['message']['content'][0]['text']
        ans_list.append(ans)
        
        while stop == "max_tokens":
            logger.info("Response truncated, continuing generation...")
            messages.append(response['output']['message'])
            messages.append(self.continue_prompt)
            
            # Extract last few lines for continuation context
            sec_last_line = '\n'.join(ans.rsplit('\n', 3)[1:-1]).strip()
            messages.append({"role": "assistant", "content": [{"text": sec_last_line}]})
            
            response, stop = self.generate_conversation([{'text': system_prompt}], messages)
            ans = response['output']['message']['content'][0]['text']
            del messages[-1]  # Remove the prefill message
            ans_list.append(ans)
        
        return ans_list
    
    def stitch_output(self, prompt: str, system_prompt: str, tag: str = "java") -> str:
        """Stitch together multiple responses and extract content within specified tags"""
        ans_list = self.run_converse_inference_with_continuation(prompt, system_prompt)

        if len(ans_list) == 1:
            final_ans = ans_list[0]
        else:
            final_ans = ans_list[0]
            for i in range(1, len(ans_list)):
                final_ans = final_ans.rsplit('\n', 1)[0] + ans_list[i]

        # Extract content within tags
        # if f'<{tag}>' in final_ans and f'</{tag}>' in final_ans:
        #     final_ans = final_ans.split(f'<{tag}>')[-1].split(f'</{tag}>')[0].strip()
        #     final_ans = final_ans.replace(f'</{tag}>', '').replace(f'<{tag}>', '')

        return final_ans
    
    def simple_inference(self, prompt: str, system_prompt: str) -> str:
        """Simple inference for cases where continuation is not expected"""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        try:
            response, stop_reason = self.generate_conversation([{'text': system_prompt}], messages)
            result = response['output']['message']['content'][0]['text']
            
            if stop_reason == "max_tokens":
                logger.warning("Response was truncated. Consider using stitch_output for longer responses.")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in simple_inference: {str(e)}")
            raise

class ConversionOrchestrator:
    """
    Enhanced orchestrator using Strands framework with preserved BedrockInference
    
    This class combines the benefits of Strands session management with the critical
    token continuation functionality of the original BedrockInference implementation.
    """
    
    def __init__(self, region_name: str = "us-east-1", model_id: str = "us.amazon.nova-premier-v1:0"):
        # Initialize BedrockInference
        self.bedrock = BedrockInference(region_name, model_id)
        
        # Initialize Strands session manager with default session
        self.session_manager = FileSessionManager(session_id="default_conversion_session")
        
        # Create all strands-compatible agents
        self.agents = create_strands_agents(self.bedrock)
        
        # Performance tracking
        self.conversion_stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "average_processing_time": 0.0
        }
        
        logger.info("Strands Conversion Orchestrator initialized successfully")
    
    def _assess_complexity(self, c_code: str) -> str:
        """Assess code complexity based on line count and patterns"""
        lines = len(c_code.split('\n'))
        
        if lines <= 300:
            return "simple"
        elif lines <= 700:
            return "medium"
        else:
            return "complex"
    
    def _create_file_metadata(self, file_path: str, c_code: str) -> FileMetadata:
        """Create metadata for the input file"""
        filename = os.path.basename(file_path)
        file_type = "dbio" if "dbio" in filename.lower() or "sql" in c_code.lower() else "c"
        complexity = self._assess_complexity(c_code)
        line_count = len(c_code.split('\n'))
        
        # Simple dependency detection
        dependencies = []
        for line in c_code.split('\n'):
            if line.strip().startswith('#include'):
                dependencies.append(line.strip())
        
        return FileMetadata(
            filename=filename,
            file_type=file_type,
            complexity=complexity,
            line_count=line_count,
            dependencies=dependencies
        )
    
    async def execute_conversion_pipeline(self, context: ConversionContext, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Execute the complete conversion pipeline using Strands agents
        
        Args:
            context: ConversionContext with C code and metadata
            max_iterations: Maximum feedback iterations
            
        Returns:
            Dictionary with conversion results
        """
        start_time = time.time()
        
        try:
            # Create session for this conversion
            session_id = f"conversion_{int(time.time())}"
            context.session_id = session_id
            
            logger.info(f"Starting conversion pipeline for session: {session_id}")
            
            # Step 1: Code Analysis
            analysis_result = await self.agents["code_analysis_agent"].execute_async(context)
            if not analysis_result.get("success", False):
                return self._create_error_result(analysis_result, start_time)
            
            context = analysis_result["context"]
            
            # Step 2: Initial Conversion
            conversion_result = await self.agents["conversion_agent"].execute_async(context)
            if not conversion_result.get("success", False):
                return self._create_error_result(conversion_result, start_time)
            
            context = conversion_result["context"]
            
            # Step 3: Iterative Validation, Security Assessment and Feedback Loop
            for iteration in range(max_iterations):
                logger.info(f"Starting validation iteration {iteration + 1}")
                
                # Validate conversion
                validation_result = await self.agents["validation_agent"].execute_async(context)
                if not validation_result.get("success", False):
                    logger.error(f"Validation failed at iteration {iteration + 1}")
                    break
                
                context = validation_result["context"]
                
                # Security Assessment
                security_result = await self.agents["security_assessment_agent"].execute_async(context)
                if not security_result.get("success", False):
                    logger.warning(f"Security assessment failed at iteration {iteration + 1}, continuing without security feedback")
                else:
                    context = security_result["context"]
                    critical_vulns = security_result.get("critical_vulnerabilities_count", 0)
                    logger.info(f"Security assessment completed. Critical vulnerabilities: {critical_vulns}")
                
                # Check if conversion is complete and secure
                is_functionally_complete = validation_result.get("is_complete", False)
                has_critical_security_issues = security_result.get("critical_vulnerabilities_count", 0) > 0 if security_result.get("success", False) else False
                
                if is_functionally_complete and not has_critical_security_issues:
                    logger.info(f"Conversion completed successfully after {iteration + 1} iterations")
                    
                    # Optional integration step
                    integration_result = await self.agents["integration_agent"].execute_async(context)
                    if integration_result.get("success", False):
                        context = integration_result["context"]
                    
                    return self._create_success_result(context, iteration + 1, start_time, validation_result, security_result)
                
                # Apply feedback if not complete or has security issues
                feedback_result = await self.agents["feedback_agent"].execute_async(context)
                if not feedback_result.get("success", False):
                    logger.error(f"Feedback application failed at iteration {iteration + 1}")
                    break
                
                context = feedback_result["context"]
                
                # Small delay between iterations
                await asyncio.sleep(1)
            
            # Return final result even if max iterations reached
            final_validation = await self.agents["validation_agent"].execute_async(context)
            final_security = await self.agents["security_assessment_agent"].execute_async(context)
            return self._create_success_result(
                context, 
                max_iterations, 
                start_time, 
                final_validation,
                final_security,
                max_iterations_reached=True
            )
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "session_id": getattr(context, 'session_id', None)
            }
    
    async def execute_dbio_conversion(self, context: ConversionContext) -> Dict[str, Any]:
        """Execute DBIO conversion using Strands agents"""
        start_time = time.time()
        
        try:
            session_id = f"dbio_conversion_{int(time.time())}"
            context.session_id = session_id
            
            logger.info(f"Starting DBIO conversion for session: {session_id}")
            
            dbio_result = await self.agents["dbio_conversion_agent"].execute_async(context)
            
            if dbio_result.get("success", False):
                return {
                    "success": True,
                    "mybatis_xml": dbio_result["mybatis_xml"],
                    "context": dbio_result["context"],
                    "processing_time": time.time() - start_time,
                    "session_id": session_id
                }
            else:
                return self._create_error_result(dbio_result, start_time)
                
        except Exception as e:
            logger.error(f"DBIO conversion failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "session_id": getattr(context, 'session_id', None)
            }
    
    def _create_success_result(self, context: ConversionContext, iterations: int, 
                             start_time: float, validation_result: Dict, 
                             security_result: Dict = None,
                             max_iterations_reached: bool = False) -> Dict[str, Any]:
        """Create a successful conversion result"""
        processing_time = time.time() - start_time
        validation_score = validation_result.get("validation", {}).get("completeness_score", 0.0)
        
        # Update stats
        self.conversion_stats["total_conversions"] += 1
        self.conversion_stats["successful_conversions"] += 1
        self._update_average_processing_time(processing_time)
        
        result = {
            "success": True,
            "context": context,
            "java_code": context.java_code,
            "iterations": iterations,
            "processing_time": processing_time,
            "validation_score": validation_score,
            "max_iterations_reached": max_iterations_reached,
            "final_validation": validation_result.get("validation", {}),
            "session_id": context.session_id,
            "agent_trace": context.agent_trace
        }
        
        # Add security assessment results if available
        if security_result and security_result.get("success", False):
            result["security_assessment"] = security_result.get("security_assessment", {})
            result["critical_vulnerabilities_count"] = security_result.get("critical_vulnerabilities_count", 0)
        
        return result
    
    def _create_error_result(self, error_result: Dict, start_time: float) -> Dict[str, Any]:
        """Create an error result"""
        processing_time = time.time() - start_time
        
        # Update stats
        self.conversion_stats["total_conversions"] += 1
        self.conversion_stats["failed_conversions"] += 1
        self._update_average_processing_time(processing_time)
        
        return {
            "success": False,
            "error": error_result.get("error", "Unknown error"),
            "processing_time": processing_time,
            "agent_name": error_result.get("agent_name", "unknown"),
            "context": error_result.get("context")
        }
    
    def _update_average_processing_time(self, processing_time: float):
        """Update average processing time statistics"""
        total = self.conversion_stats["total_conversions"]
        current_avg = self.conversion_stats["average_processing_time"]
        
        # Avoid division by zero
        if total == 0:
            self.conversion_stats["average_processing_time"] = processing_time
        else:
            # Calculate new average
            new_avg = ((current_avg * (total - 1)) + processing_time) / total
            self.conversion_stats["average_processing_time"] = new_avg
    
    async def convert_single_file(self, input_file_path: str, output_dir: str = "output", 
                                max_iterations: int = 3) -> Dict[str, Any]:
        """
        Convert a single C file to Java using Strands agents
        
        Args:
            input_file_path: Path to the C file
            output_dir: Output directory for converted files
            max_iterations: Maximum feedback iterations
            
        Returns:
            Dictionary with conversion results
        """
        try:
            # Read input file
            if not os.path.exists(input_file_path):
                return {
                    "success": False,
                    "error": f"Input file not found: {input_file_path}",
                    "input_file": input_file_path
                }
            
            with open(input_file_path, 'r', encoding='utf-8') as f:
                c_code = f.read()
            
            # Create context
            file_metadata = self._create_file_metadata(input_file_path, c_code)
            context = ConversionContext(
                c_code=c_code,
                file_metadata=file_metadata.__dict__
            )
            
            # Execute conversion
            if file_metadata.file_type == "dbio":
                result = await self.execute_dbio_conversion(context)
                output_extension = ".xml"
                output_content = result.get("mybatis_xml", "")
            else:
                result = await self.execute_conversion_pipeline(context, max_iterations)
                output_extension = ".java"
                output_content = result.get("java_code", "")
            
            if result.get("success", False):
                # Create output directory
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(input_file_path))[0]
                if file_metadata.file_type == "dbio":
                    output_filename = f"{base_name}Mapper{output_extension}"
                else:
                    # Convert to Java class naming convention
                    class_name = ''.join(word.capitalize() for word in base_name.split('_'))
                    output_filename = f"{class_name}{output_extension}"
                
                output_file_path = os.path.join(output_dir, output_filename)
                
                # Write output file
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                
                logger.info(f"✅ Conversion successful: {input_file_path} -> {output_file_path}")
                
                return {
                    "success": True,
                    "input_file": input_file_path,
                    "output_file": output_file_path,
                    "feedback_iterations": result.get("iterations", 0),
                    "processing_time": result.get("processing_time", 0.0),
                    "validation_score": result.get("validation_score", 0.0),
                    "file_metadata": file_metadata.__dict__,
                    "session_id": result.get("session_id"),
                    "agent_trace": result.get("agent_trace", [])
                }
            else:
                return {
                    "success": False,
                    "input_file": input_file_path,
                    "error": result.get("error", "Unknown conversion error"),
                    "processing_time": result.get("processing_time", 0.0)
                }
                
        except Exception as e:
            logger.error(f"File conversion failed: {str(e)}")
            return {
                "success": False,
                "input_file": input_file_path,
                "error": str(e),
                "processing_time": 0.0
            }
    
    async def convert_dbio_file(self, input_file_path: str, output_dir: str = "output") -> Dict[str, Any]:
        """Convert DBIO C file to MyBatis XML"""
        return await self.convert_single_file(input_file_path, output_dir, max_iterations=1)
    
    async def process_directory(self, input_directory: str, output_directory: str = "output") -> Dict[str, Any]:
        """
        Process entire directory of C files using Strands agents
        
        Args:
            input_directory: Directory containing C files
            output_directory: Output directory for converted files
            
        Returns:
            Dictionary with batch processing results
        """
        start_time = time.time()
        
        if not os.path.exists(input_directory):
            return {
                "success": False,
                "error": f"Input directory not found: {input_directory}",
                "total_files": 0
            }
        
        # Find all C files
        c_files = []
        for root, dirs, files in os.walk(input_directory):
            for file in files:
                if file.endswith(('.c', '.h')):
                    c_files.append(os.path.join(root, file))
        
        if not c_files:
            return {
                "success": True,
                "message": "No C files found in directory",
                "total_files": 0,
                "successful_conversions": 0,
                "failed_conversions": 0
            }
        
        logger.info(f"Processing {len(c_files)} C files from {input_directory}")
        
        # Process files concurrently (with reasonable limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent conversions
        
        async def process_single_file(file_path):
            async with semaphore:
                return await self.convert_single_file(file_path, output_directory)
        
        # Execute all conversions
        tasks = [process_single_file(file_path) for file_path in c_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_conversions = 0
        failed_conversions = 0
        file_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                file_results.append({
                    "filename": os.path.basename(c_files[i]),
                    "success": False,
                    "error": str(result),
                    "processing_time": 0.0
                })
                failed_conversions += 1
            else:
                file_results.append({
                    "filename": os.path.basename(c_files[i]),
                    "success": result.get("success", False),
                    "processing_time": result.get("processing_time", 0.0),
                    "output_file": result.get("output_file", ""),
                    "error": result.get("error", "")
                })
                
                if result.get("success", False):
                    successful_conversions += 1
                else:
                    failed_conversions += 1
        
        total_processing_time = time.time() - start_time
        
        logger.info(f"Batch processing completed: {successful_conversions}/{len(c_files)} successful")
        
        return {
            "success": True,
            "total_files": len(c_files),
            "successful_conversions": successful_conversions,
            "failed_conversions": failed_conversions,
            "total_processing_time": total_processing_time,
            "file_results": file_results,
            "input_directory": input_directory,
            "output_directory": output_directory
        }
    
    # Backward compatibility methods
    async def convert_from_code_string(self, c_code: str, filename: str = "code.c", 
                                     output_dir: str = "output") -> Dict[str, Any]:
        """Convert from code string (backward compatibility)"""
        # Create temporary file
        temp_file = os.path.join(output_dir, f"temp_{filename}")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(c_code)
            
            result = await self.convert_single_file(temp_file, output_dir)
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return result
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        return self.conversion_stats.copy()

# Utility functions for testing and validation
async def test_strands_orchestrator():
    """Test function to verify the strands orchestrator works correctly"""
    try:
        orchestrator = ConversionOrchestrator()
        logger.info("✅ Strands orchestrator created successfully")
        
        # Test simple code conversion
        test_code = """
        #include <stdio.h>
        int add(int a, int b) {
            return a + b;
        }
        """
        
        result = await orchestrator.convert_from_code_string(test_code, "test.c")
        
        if result.get("success", False):
            logger.info("✅ Test conversion successful")
            return True
        else:
            logger.error(f"❌ Test conversion failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Orchestrator test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Run test
    asyncio.run(test_strands_orchestrator())
