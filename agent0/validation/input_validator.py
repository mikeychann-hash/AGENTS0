import re
from typing import List, Dict, Any, Optional


from agent0.tasks.schema import TaskSpec


class InputValidator:
    """Enhanced input validation for tasks and configuration."""

    MAX_PROMPT_LENGTH = 2000  # Increased but still reasonable
    ALLOWED_DOMAINS = {"math", "logic", "code", "long"}
    
    # Suspicious patterns that might indicate injection attempts
    SUSPICIOUS_PATTERNS = [
        r'eval\s*\(', r'exec\s*\(', r'__import__\s*\(', r'subprocess\s*\.',
        r'os\s*\.system\s*\(', r'rm\s+-rf', r'del\s+', r'format\s+[A-Z]:',
        r'\.\.[/\\]', r'javascript:', r'<script', r'onload\s*=',
        r'onerror\s*=', r'document\.write', r'innerHTML\s*=',
        r'union\s+select', r'drop\s+table', r'insert\s+into',
        r'php://', r'expect://', r'data://', r'file://'
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\bcreate\b|\balter\b).*\b(from|where|and|or)\b",
        r"(\b(or|and)\b.*=.*\b(or|and)\b|=.*\b(or|and)\b)",
        r"(\b1\s*=\s*1\b|\btrue\s*=\s*true\b|\b0\s*=\s*0\b)"
    ]

    def validate_task(self, task: TaskSpec) -> List[str]:
        """Comprehensive task validation with security checks."""
        errors: List[str] = []

        # Basic field validation
        if not task.task_id or not isinstance(task.task_id, str):
            errors.append("Missing or invalid task_id")
        elif len(task.task_id) > 100:
            errors.append("task_id too long (max 100 characters)")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', task.task_id):
            errors.append("task_id contains invalid characters (alphanumeric, underscore, dash only)")

        if task.domain not in self.ALLOWED_DOMAINS:
            errors.append(f"Invalid domain: {task.domain}. Allowed: {', '.join(self.ALLOWED_DOMAINS)}")

        if not task.prompt or not isinstance(task.prompt, str):
            errors.append("Empty or invalid prompt")
        else:
            prompt_length = len(task.prompt)
            if prompt_length > self.MAX_PROMPT_LENGTH:
                errors.append(f"Prompt too long: {prompt_length} > {self.MAX_PROMPT_LENGTH}")
            if prompt_length < 3:
                errors.append("Prompt too short (minimum 3 characters)")

        # Security validation
        if isinstance(task.prompt, str):
            lower_prompt = task.prompt.lower()
            
            # Check for code execution attempts
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, lower_prompt, re.IGNORECASE):
                    errors.append(f"Suspicious content detected (potential code injection): {pattern}")
            
            # Check for SQL injection patterns
            for pattern in self.SQL_PATTERNS:
                if re.search(pattern, lower_prompt, re.IGNORECASE):
                    errors.append(f"Potential SQL injection pattern detected: {pattern}")
            
            # Check for script tags and HTML injection
            if re.search(r'<(script|iframe|object|embed|form)', lower_prompt):
                errors.append("HTML/script tags detected in prompt")
            
            # Check for excessive special characters
            special_char_ratio = sum(1 for c in task.prompt if not c.isalnum() and not c.isspace()) / len(task.prompt)
            if special_char_ratio > 0.3:  # More than 30% special characters
                errors.append("Prompt contains excessive special characters")

        # Validate constraints if present
        if hasattr(task, 'constraints') and task.constraints:
            if not isinstance(task.constraints, list):
                errors.append("Constraints must be a list")
            else:
                for i, constraint in enumerate(task.constraints):
                    if not isinstance(constraint, str):
                        errors.append(f"Constraint {i} must be a string")
                    elif len(constraint) > 500:
                        errors.append(f"Constraint {i} too long (max 500 characters)")

        # Validate verifier if present
        if hasattr(task, 'verifier') and task.verifier:
            if not hasattr(task.verifier, 'kind') or not task.verifier.kind:
                errors.append("Verifier missing kind field")
            if hasattr(task.verifier, 'spec') and not isinstance(task.verifier.spec, dict):
                errors.append("Verifier spec must be a dictionary")

        return errors

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration parameters."""
        errors: List[str] = []
        
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return errors

        # Validate timeout values
        for key, value in config.items():
            if 'timeout' in key.lower():
                if not isinstance(value, (int, float)):
                    errors.append(f"{key} must be a number")
                elif value <= 0 or value > 300:  # Max 5 minutes
                    errors.append(f"{key} must be between 0 and 300 seconds")

        # Validate model configuration
        if 'models' in config:
            if not isinstance(config['models'], dict):
                errors.append("models must be a dictionary")
            else:
                for model_name, model_config in config['models'].items():
                    if not isinstance(model_config, dict):
                        errors.append(f"Model config for {model_name} must be a dictionary")
                    else:
                        # Validate temperature
                        if 'temperature' in model_config:
                            temp = model_config['temperature']
                            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2.0:
                                errors.append(f"{model_name} temperature must be between 0 and 2.0")
                        
                        # Validate top_p
                        if 'top_p' in model_config:
                            top_p = model_config['top_p']
                            if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1.0:
                                errors.append(f"{model_name} top_p must be between 0 and 1.0")

        return errors

    def sanitize_string(self, text: str, max_length: int = 1000) -> str:
        """Sanitize string input for safe processing."""
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove control characters except newlines and tabs
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
        
        return sanitized.strip()
