#!/usr/bin/env python3
"""
Simple Test Script for C to Java Conversion Workflow

This script provides a comprehensive test of the agentic workflow for converting
C code to Java/Spring framework code using Amazon Bedrock with Nova Premier.

Usage:
    python test_conversion_simple.py

Prerequisites:
    1. AWS credentials configured (aws configure)
    2. Bedrock access with Nova Premier model permissions
    3. Required Python packages installed (pip install -r requirements.txt)
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
import logging

# Import the required modules
try:
    from agentic_workflow import ConversionOrchestrator, BedrockInference
    from conversion_agents import create_strands_agents
    import prompts
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all files are in the same directory and dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def test_imports():
    """Test if all required modules can be imported"""
    print_section("Testing Imports")
    
    # Since imports are at the top, just verify they're available
    try:
        # Test that we can access the imported classes
        ConversionOrchestrator
        BedrockInference
        create_strands_agents
        prompts
        print("✅ Successfully imported all modules")
        return True
    except NameError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all files are in the same directory and dependencies are installed")
        return False

def test_orchestrator_initialization():
    """Test orchestrator initialization"""
    print_section("Testing Orchestrator Initialization")
    
    try:
        orchestrator = ConversionOrchestrator(region_name="us-east-1")
        print("✅ Orchestrator initialized successfully")
        print(f"🤖 Model: {orchestrator.bedrock.model_id}")
        print(f"🔧 Agents created: {len(orchestrator.agents)}")
        return orchestrator
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        print("Please check your AWS credentials and Bedrock permissions")
        return None

def analyze_sample_file():
    """Analyze the sample C file"""
    print_section("Analyzing Sample C File")
    
    sample_file = "sample_customer_service.c"
    sample_path = Path(sample_file)
    
    if not sample_path.exists():
        print(f"❌ Sample C file not found: {sample_file}")
        return None
    print(f"✅ Sample C file found: {sample_file}")
    return sample_file

async def test_single_file_conversion(orchestrator, sample_file):
    """Test single file conversion"""
    print_section("Testing Single File Conversion")
    
    if not orchestrator or not sample_file:
        print("⚠️ Skipping single file conversion test (missing prerequisites)")
        return None
    
    print(f"🔄 Starting conversion of {sample_file}...")
    print(f"📁 Output directory: output/")
    
    start_time = time.time()
    
    try:
        result = await orchestrator.convert_single_file(
            input_file_path=sample_file,
            output_dir="output",
            max_iterations=3
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result['success']:
            print(f"✅ Conversion completed successfully!")
            print(f"📊 Results:")
            print(f"   - Input file: {result['input_file']}")
            print(f"   - Output file: {result['output_file']}")
            print(f"   - Processing time: {processing_time:.2f} seconds")
            print(f"   - Feedback iterations: {result['feedback_iterations']}")
            
            # Check output file
            output_path = Path(result['output_file'])
            if output_path.exists():
                output_size = output_path.stat().st_size
                with open(output_path, 'r') as f:
                    output_content = f.read()
                    output_lines = len(output_content.splitlines())
                
                print(f"📄 Output file statistics:")
                print(f"   - Size: {output_size:,} bytes")
                print(f"   - Lines: {output_lines:,}")
                
                return result
            else:
                print(f"⚠️ Output file not found: {result['output_file']}")
        else:
            print(f"❌ Conversion failed!")
            print(f"Error: {result['error']}")
    
    except Exception as e:
        print(f"❌ Exception during conversion: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def analyze_conversion_quality(result):
    """Analyze the quality of the conversion"""
    print_section("Analyzing Conversion Quality")
    
    if not result or not result['success']:
        print("⚠️ No successful conversion result to analyze")
        return
    
    output_file = result['output_file']
    if not Path(output_file).exists():
        print(f"⚠️ Output file not found: {output_file}")
        return
    
    with open(output_file, 'r') as f:
        java_content = f.read()
    
    # Check for key Java/Spring patterns
    patterns_to_check = {
        '@Service': 'Spring Service annotation',
        '@Component': 'Spring Component annotation',
        '@Repository': 'Spring Repository annotation',
        '@Autowired': 'Dependency injection',
        '@RequiredArgsConstructor': 'Lombok constructor',
        'public class': 'Java class definition',
        'private': 'Encapsulation',
        'public': 'Public methods',
        'Optional<': 'Optional usage',
        'List<': 'Generic collections',
        'throws': 'Exception handling',
        'logger': 'Logging implementation'
    }
    
    print("📋 Java/Spring Pattern Analysis:")
    found_patterns = 0
    total_patterns = len(patterns_to_check)
    
    # for pattern, description in patterns_to_check.items():
    #     if pattern in java_content:
    #         print(f"   ✅ {description}")
    #         found_patterns += 1
    #     else:
    #         print(f"   ❌ {description}")
    
    quality_score = (found_patterns / total_patterns) * 100
    # print(f"\n🎯 Conversion Quality Score: {quality_score:.1f}% ({found_patterns}/{total_patterns} patterns found)")
    
    # Check for common issues
    print("\n🔍 Common Issue Analysis:")
    issues = []
    
    if 'malloc' in java_content or 'free' in java_content:
        issues.append("C memory management functions still present")
    
    if 'printf' in java_content and 'System.out.println' not in java_content:
        issues.append("C printf functions not converted to Java")
    
    if '#include' in java_content:
        issues.append("C include statements still present")
    
    if 'struct' in java_content and 'class' not in java_content:
        issues.append("C structs not converted to Java classes")
    
    if issues:
        for issue in issues:
            print(f"   ⚠️ {issue}")
    else:
        print("   ✅ No common conversion issues detected")

async def test_dbio_conversion(orchestrator):
    """Test DBIO conversion"""
    print_section("Testing DBIO Conversion")
    
    if not orchestrator:
        print("⚠️ Skipping DBIO conversion test (missing orchestrator)")
        return None
    
    # Create sample DBIO file
    dbio_sample = "sample_dbio.c"
    dbio_content = '''/*
 * Sample DBIO C code for testing SQL to MyBatis conversion
 */
#include <stdio.h>
#include <sqlca.h>

EXEC SQL BEGIN DECLARE SECTION;
    int customer_id;
    char customer_name[100];
    char email[150];
    double balance;
EXEC SQL END DECLARE SECTION;

int get_customer_by_id(int id) {
    EXEC SQL SELECT customer_name, email, balance
             INTO :customer_name, :email, :balance
             FROM customers
             WHERE customer_id = :id;
    
    if (SQLCODE != 0) {
        return -1;
    }
    return 0;
}

int update_customer_balance(int id, double new_balance) {
    EXEC SQL UPDATE customers
             SET balance = :new_balance
             WHERE customer_id = :id;
    
    if (SQLCODE != 0) {
        return -1;
    }
    return 0;
}
'''
    
    with open(dbio_sample, 'w') as f:
        f.write(dbio_content)
    
    print(f"📝 Created DBIO sample file: {dbio_sample}")
    
    try:
        start_time = time.time()
        
        dbio_result = await orchestrator.convert_dbio_file(
            input_file_path=dbio_sample,
            output_dir="mybatis_output"
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if dbio_result['success']:
            print(f"✅ DBIO conversion completed successfully!")
            print(f"📊 Results:")
            print(f"   - Input file: {dbio_result['input_file']}")
            print(f"   - Output file: {dbio_result['output_file']}")
            print(f"   - Processing time: {processing_time:.2f} seconds")
            
            return dbio_result
        else:
            print(f"❌ DBIO conversion failed!")
            print(f"Error: {dbio_result['error']}")
    
    except Exception as e:
        print(f"❌ Exception during DBIO conversion: {e}")
    
    return None

async def test_batch_directory_processing(orchestrator):
    """Test batch directory processing"""
    print_section("Testing Batch Directory Processing")
    
    if not orchestrator:
        print("⚠️ Skipping batch directory processing test (missing orchestrator)")
        return None
    
    # Create a test directory with multiple C files
    test_dir = "test_c_files"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create additional test files
    test_files = {
        "math_utils.c": '''#include <stdio.h>
#include <math.h>

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

double calculate_area(double radius) {
    return 3.14159 * radius * radius;
}

int main() {
    printf("Math utilities test\\n");
    printf("5 + 3 = %d\\n", add(5, 3));
    printf("5 * 3 = %d\\n", multiply(5, 3));
    printf("Area of circle (r=5): %.2f\\n", calculate_area(5.0));
    return 0;
}''',
        
        "string_utils.c": '''#include <stdio.h>
#include <string.h>
#include <stdlib.h>

char* concat_strings(const char* str1, const char* str2) {
    int len1 = strlen(str1);
    int len2 = strlen(str2);
    char* result = malloc(len1 + len2 + 1);
    
    strcpy(result, str1);
    strcat(result, str2);
    
    return result;
}

int string_length(const char* str) {
    return strlen(str);
}

int main() {
    char* result = concat_strings("Hello, ", "World!");
    printf("Concatenated: %s\\n", result);
    printf("Length: %d\\n", string_length(result));
    free(result);
    return 0;
}''',
        
        "file_utils.c": '''#include <stdio.h>
#include <stdlib.h>

int read_file(const char* filename) {
    FILE* file = fopen(filename, "r");
    if (file == NULL) {
        printf("Error opening file\\n");
        return -1;
    }
    
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), file)) {
        printf("%s", buffer);
    }
    
    fclose(file);
    return 0;
}

int write_file(const char* filename, const char* content) {
    FILE* file = fopen(filename, "w");
    if (file == NULL) {
        printf("Error creating file\\n");
        return -1;
    }
    
    fprintf(file, "%s", content);
    fclose(file);
    return 0;
}

int main() {
    write_file("test.txt", "Hello, World!\\n");
    read_file("test.txt");
    return 0;
}'''
    }
    
    # Create test files
    for filename, content in test_files.items():
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"📝 Created test file: {filepath}")
    
    # Copy the main sample file to test directory if it exists
    sample_file = "sample_customer_service.c"
    if Path(sample_file).exists():
        import shutil
        shutil.copy(sample_file, os.path.join(test_dir, sample_file))
        print(f"📝 Copied {sample_file} to test directory")
        total_files = len(test_files) + 1
    else:
        total_files = len(test_files)
    
    print(f"\n📁 Test directory '{test_dir}' created with {total_files} C files")
    
    # Test batch directory processing
    print("🔄 Starting batch directory processing test...")
    print(f"📁 Input directory: {test_dir}")
    print(f"📁 Output directory: batch_output")
    
    try:
        batch_start_time = time.time()
        
        # Process the entire directory
        batch_results = await orchestrator.process_directory(
            input_directory=test_dir,
            output_directory="batch_output"
        )
        
        batch_end_time = time.time()
        total_batch_time = batch_end_time - batch_start_time
        
        # Display batch results
        print(f"\n📊 Batch Processing Results:")
        print(f"   - Total files processed: {batch_results['total_files']}")
        print(f"   - Successful conversions: {batch_results['successful_conversions']}")
        print(f"   - Failed conversions: {batch_results['failed_conversions']}")
        print(f"   - Total processing time: {total_batch_time:.2f} seconds")
        print(f"   - Average time per file: {total_batch_time / max(batch_results['total_files'], 1):.2f} seconds")
        
        # Show individual file results
        print(f"\n📋 Individual File Results:")
        for file_result in batch_results['file_results']:
            status = "✅" if file_result['success'] else "❌"
            print(f"   {status} {file_result['filename']} - {file_result['processing_time']:.2f}s")
            if not file_result['success']:
                print(f"      Error: {file_result.get('error', 'Unknown error')}")
        
        # Calculate success rate
        if batch_results['total_files'] > 0:
            success_rate = (batch_results['successful_conversions'] / batch_results['total_files']) * 100
            print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return batch_results
        
    except Exception as e:
        print(f"\n❌ Exception during batch processing: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_summary(results):
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    # Count successful tests
    successful_tests = sum(1 for result in results.values() if result is not None)
    total_tests = len(results)
    
    print(f"📊 Test Results: {successful_tests}/{total_tests} tests passed")
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result is not None else "❌ FAILED"
        print(f"   {test_name:30} | {status}")
    
    # Check output directories
    print("\n📁 Output Directory Summary:")
    output_dirs = ['output', 'mybatis_output', 'batch_output']
    
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            files = list(Path(output_dir).glob('*'))
            print(f"   {output_dir:15} | {len(files)} files created")
        else:
            print(f"   {output_dir:15} | Directory not found")
    
    if successful_tests == total_tests:
        print("\n🎉 All tests completed successfully!")
    else:
        print(f"\n⚠️ {total_tests - successful_tests} test(s) failed. Check the output above for details.")

async def main():
    """Main test function"""
    print_header("C to Java Conversion Workflow Test")
    print("This script tests the agentic workflow for converting C code to Java/Spring framework code.")
    
    # Initialize results tracking
    results = {}
    
    # Test 1: Import modules
    if not test_imports():
        print("\n❌ Critical error: Cannot import required modules. Exiting.")
        sys.exit(1)
    results['Module Imports'] = True
    
    # Test 2: Initialize orchestrator
    orchestrator = test_orchestrator_initialization()
    results['Orchestrator Initialization'] = orchestrator
    
    # Test 3: Analyze sample file
    sample_file = analyze_sample_file()
    results['Sample File Analysis'] = sample_file
    
    # Test 4: Single file conversion
    conversion_result = await test_single_file_conversion(orchestrator, sample_file)
    results['Single File Conversion'] = conversion_result
    
    # Test 5: Analyze conversion quality
    if conversion_result:
        analyze_conversion_quality(conversion_result)
        results['Conversion Quality Analysis'] = True
    else:
        results['Conversion Quality Analysis'] = None
    
    # Test 6: DBIO conversion
    dbio_result = await test_dbio_conversion(orchestrator)
    results['DBIO Conversion'] = dbio_result
    
    # Test 7: Batch directory processing
    # batch_result = await test_batch_directory_processing(orchestrator)
    # results['Batch Directory Processing'] = batch_result
    
    # Print summary
    print_summary(results)

if __name__ == "__main__":
    asyncio.run(main())
