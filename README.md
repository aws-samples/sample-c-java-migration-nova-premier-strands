# C to Java Code Conversion

Agentic workflow for converting legacy C code to Java/Spring using Amazon Bedrock Nova Premier.

## Quick Start

```bash
pip install -r requirements.txt
aws configure
python test_conversion.py
```

## Architecture

Six specialized agents using AWS Strands framework:
1. **Code Analysis** - Analyzes C structure and complexity
2. **Conversion** - Transforms C to Java/Spring code 
3. **Validation** - Verifies conversion quality
4. **Security Assessment** - Identifies security issues in the original and converted code
5. **Feedback** - Iterative improvement
6. **Integration** - Combines multiple files
7. **DBIO Conversion** - SQL to MyBatis XML

## Files

```
├── agentic_workflow.py    # Main orchestrator
├── conversion_agents.py   # Six agents
├── prompts.py            # Prompt templates
└── test_conversion.py    # Demo
```

## Usage

### Single File Conversion

```python
from agentic_workflow import ConversionOrchestrator

orchestrator = ConversionOrchestrator(region_name="us-east-1")

result = orchestrator.convert_single_file(
    input_file_path="legacy_code/math_utils.c",
    output_dir="converted_java",
    max_iterations=3
)
```

### DBIO Conversion

```python
dbio_result = orchestrator.convert_dbio_file(
    input_file_path="legacy_sql/account_queries.c",
    output_dir="mybatis_xml"
)
```

### Batch Processing

```python
results = orchestrator.process_directory(
    input_directory="legacy_c_code",
    output_directory="converted_java"
)
```

## Configuration

### Model Settings
```python
class BedrockInference:
    def __init__(self, region_name="us-east-1", model_id="us.amazon.nova-premier-v1:0"):
        self.inference_config = {
            'maxTokens': 4096,
            'temperature': 0.05,
            'topP': 0.9
        }
```

### Prompt Customization
All prompts are in `prompts.py`:
- `CODE_ANALYSIS_SYSTEM_PROMPT`
- `CONVERSION_SYSTEM_PROMPT`
- `VALIDATION_SYSTEM_PROMPT`
- `FEEDBACK_SYSTEM_PROMPT`
- `INTEGRATION_SYSTEM_PROMPT`
- `DBIO_CONVERSION_SYSTEM_PROMPT`
- `SECURITY_ASSESSMENT_SYSTEM_PROMPT`

## Testing

```bash
python test_conversion.py
```

## Troubleshooting

1. **AWS Issues**: Configure credentials with `aws configure`
2. **Import Errors**: Ensure all files are in same directory
3. **Quality Issues**: Increase `max_iterations` parameter

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

