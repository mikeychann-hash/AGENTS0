"""
Configuration validation for Agent0.
Ensures all configuration parameters are valid and safe.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """Comprehensive configuration validator for Agent0."""
    
    # Valid backend types
    VALID_BACKENDS = {"ollama", "llama_cpp", "vllm", "cli"}
    
    # Valid device types
    VALID_DEVICES = {"cuda", "cpu", "auto", "mps"}
    
    # Valid domains
    VALID_DOMAINS = {"math", "logic", "code", "long"}
    
    # Configuration schema with validation rules
    CONFIG_SCHEMA = {
        "models": {
            "teacher": {
                "backend": str,
                "model": str,
                "host": str,
                "context_length": int,
                "temperature": float,
                "top_p": float,
                "uncertainty_samples": int
            },
            "student": {
                "backend": str,
                "model": str,
                "host": str,
                "context_length": int,
                "temperature": float,
                "top_p": float,
                "uncertainty_samples": int
            }
        },
        "resources": {
            "device": str,
            "max_gpu_memory_gb": (int, float),
            "num_threads": int,
            "max_tokens_per_task": int
        },
        "tooling": {
            "enable_python": bool,
            "enable_shell": bool,
            "enable_math": bool,
            "enable_tests": bool,
            "timeout_seconds": (int, float),
            "workdir": str,
            "allowed_shell": list
        },
        "rewards": {
            "weight_uncertainty": float,
            "weight_tool_use": float,
            "weight_novelty": float,
            "target_success_rate": float,
            "repetition_similarity_threshold": float
        },
        "curriculum": {
            "enable_frontier": bool,
            "target_success": float,
            "frontier_window": float,
            "domains": list
        },
        "verification": {
            "enable": bool,
            "num_samples": int,
            "confidence_threshold": float,
            "enable_cot": bool
        },
        "logging": {
            "base_dir": str,
            "save_every": int,
            "flush_every": int
        },
        "router": {
            "enable": bool,
            "cloud_confidence_threshold": float,
            "local_confidence_threshold": float,
            "cache_path": str,
            "cloud_command": str
        },
        "embedding": {
            "use_transformer": bool,
            "model_name": str
        },
        "rate_limiting": {
            "max_tasks_per_minute": int,
            "max_tasks_per_hour": int
        },
        "resource_limits": {
            "max_memory_mb": int,
            "max_cpu_seconds": (int, float),
            "max_output_kb": int
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.errors: List[str] = []
        self.logger = logging.getLogger(__name__)
    
    def validate(self) -> List[str]:
        """Validate the entire configuration."""
        self.errors = []
        
        # Validate required top-level sections
        required_sections = {"models", "resources", "tooling", "rewards", "logging"}
        for section in required_sections:
            if section not in self.config:
                self.errors.append(f"Missing required configuration section: {section}")
        
        # Validate each section
        self._validate_models()
        self._validate_resources()
        self._validate_tooling()
        self._validate_rewards()
        self._validate_curriculum()
        self._validate_verification()
        self._validate_logging()
        self._validate_router()
        self._validate_embedding()
        self._validate_rate_limiting()
        self._validate_resource_limits()
        
        # Validate cross-section dependencies
        self._validate_cross_dependencies()
        
        return self.errors
    
    def _validate_models(self) -> None:
        """Validate model configurations."""
        if "models" not in self.config:
            return
        
        models = self.config["models"]
        required_models = {"teacher", "student"}
        
        for model_type in required_models:
            if model_type not in models:
                self.errors.append(f"Missing {model_type} model configuration")
                continue
            
            model_config = models[model_type]
            
            # Validate backend
            backend = model_config.get("backend")
            if not backend or backend not in self.VALID_BACKENDS:
                self.errors.append(f"Invalid backend for {model_type}: {backend}. Must be one of: {', '.join(self.VALID_BACKENDS)}")
            
            # Validate model name
            model_name = model_config.get("model")
            if not model_name or not isinstance(model_name, str) or len(model_name.strip()) == 0:
                self.errors.append(f"Invalid model name for {model_type}: {model_name}")
            
            # Validate host
            host = model_config.get("host")
            if host and not self._is_valid_url(host):
                self.errors.append(f"Invalid host URL for {model_type}: {host}")
            
            # Validate context length
            context_length = model_config.get("context_length")
            if not isinstance(context_length, int) or context_length <= 0 or context_length > 128000:
                self.errors.append(f"Invalid context_length for {model_type}: {context_length}. Must be positive integer <= 128000")
            
            # Validate temperature
            temperature = model_config.get("temperature")
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2.0:
                self.errors.append(f"Invalid temperature for {model_type}: {temperature}. Must be between 0 and 2.0")
            
            # Validate top_p
            top_p = model_config.get("top_p")
            if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1.0:
                self.errors.append(f"Invalid top_p for {model_type}: {top_p}. Must be between 0 and 1.0")
            
            # Validate uncertainty samples
            uncertainty_samples = model_config.get("uncertainty_samples")
            if not isinstance(uncertainty_samples, int) or uncertainty_samples <= 0 or uncertainty_samples > 10:
                self.errors.append(f"Invalid uncertainty_samples for {model_type}: {uncertainty_samples}. Must be integer between 1 and 10")
    
    def _validate_resources(self) -> None:
        """Validate resource configuration."""
        if "resources" not in self.config:
            return
        
        resources = self.config["resources"]
        
        # Validate device
        device = resources.get("device")
        if device and device not in self.VALID_DEVICES:
            self.errors.append(f"Invalid device: {device}. Must be one of: {', '.join(self.VALID_DEVICES)}")
        
        # Validate GPU memory
        max_gpu_memory = resources.get("max_gpu_memory_gb")
        if not isinstance(max_gpu_memory, (int, float)) or max_gpu_memory <= 0 or max_gpu_memory > 128:
            self.errors.append(f"Invalid max_gpu_memory_gb: {max_gpu_memory}. Must be positive number <= 128")
        
        # Validate number of threads
        num_threads = resources.get("num_threads")
        if not isinstance(num_threads, int) or num_threads <= 0 or num_threads > 64:
            self.errors.append(f"Invalid num_threads: {num_threads}. Must be integer between 1 and 64")
        
        # Validate max tokens
        max_tokens = resources.get("max_tokens_per_task")
        if not isinstance(max_tokens, int) or max_tokens <= 0 or max_tokens > 8192:
            self.errors.append(f"Invalid max_tokens_per_task: {max_tokens}. Must be integer between 1 and 8192")
    
    def _validate_tooling(self) -> None:
        """Validate tooling configuration."""
        if "tooling" not in self.config:
            return
        
        tooling = self.config["tooling"]
        
        # Validate boolean flags
        bool_flags = ["enable_python", "enable_shell", "enable_math", "enable_tests"]
        for flag in bool_flags:
            if flag in tooling and not isinstance(tooling[flag], bool):
                self.errors.append(f"Invalid {flag}: must be boolean")
        
        # Validate timeout
        timeout = tooling.get("timeout_seconds")
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
            self.errors.append(f"Invalid timeout_seconds: {timeout}. Must be between 1 and 300")
        
        # Validate workdir
        workdir = tooling.get("workdir")
        if workdir and not isinstance(workdir, str):
            self.errors.append(f"Invalid workdir: must be string")
        elif workdir:
            # Check for dangerous paths
            if ".." in workdir or workdir.startswith("/") or "~" in workdir:
                self.errors.append(f"Potentially dangerous workdir path: {workdir}")
        
        # Validate allowed shell commands
        allowed_shell = tooling.get("allowed_shell")
        if allowed_shell and not isinstance(allowed_shell, list):
            self.errors.append(f"Invalid allowed_shell: must be list")
        elif allowed_shell:
            for cmd in allowed_shell:
                if not isinstance(cmd, str):
                    self.errors.append(f"All allowed_shell commands must be strings")
                elif any(dangerous in cmd for dangerous in ["rm", "del", "format", "sudo", "su"]):
                    self.errors.append(f"Potentially dangerous shell command in allowed_shell: {cmd}")
    
    def _validate_rewards(self) -> None:
        """Validate reward configuration."""
        if "rewards" not in self.config:
            return
        
        rewards = self.config["rewards"]
        
        # Validate weights
        weight_keys = ["weight_uncertainty", "weight_tool_use", "weight_novelty"]
        for key in weight_keys:
            weight = rewards.get(key)
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 1.0:
                self.errors.append(f"Invalid {key}: {weight}. Must be between 0 and 1.0")
        
        # Validate target success rate
        target_success = rewards.get("target_success_rate")
        if not isinstance(target_success, (int, float)) or target_success < 0 or target_success > 1.0:
            self.errors.append(f"Invalid target_success_rate: {target_success}. Must be between 0 and 1.0")
        
        # Validate similarity threshold
        similarity_threshold = rewards.get("repetition_similarity_threshold")
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1.0:
            self.errors.append(f"Invalid repetition_similarity_threshold: {similarity_threshold}. Must be between 0 and 1.0")
    
    def _validate_curriculum(self) -> None:
        """Validate curriculum configuration."""
        if "curriculum" not in self.config:
            return
        
        curriculum = self.config["curriculum"]
        
        # Validate boolean flags
        if "enable_frontier" in curriculum and not isinstance(curriculum["enable_frontier"], bool):
            self.errors.append(f"Invalid enable_frontier: must be boolean")
        
        # Validate target success
        target_success = curriculum.get("target_success")
        if not isinstance(target_success, (int, float)) or target_success < 0 or target_success > 1.0:
            self.errors.append(f"Invalid curriculum target_success: {target_success}. Must be between 0 and 1.0")
        
        # Validate frontier window
        frontier_window = curriculum.get("frontier_window")
        if not isinstance(frontier_window, (int, float)) or frontier_window < 0 or frontier_window > 1.0:
            self.errors.append(f"Invalid frontier_window: {frontier_window}. Must be between 0 and 1.0")
        
        # Validate domains
        domains = curriculum.get("domains")
        if domains and not isinstance(domains, list):
            self.errors.append(f"Invalid curriculum domains: must be list")
        elif domains:
            for domain in domains:
                if domain not in self.VALID_DOMAINS:
                    self.errors.append(f"Invalid curriculum domain: {domain}. Must be one of: {', '.join(self.VALID_DOMAINS)}")
    
    def _validate_verification(self) -> None:
        """Validate verification configuration."""
        if "verification" not in self.config:
            return
        
        verification = self.config["verification"]
        
        # Validate boolean flags
        if "enable" in verification and not isinstance(verification["enable"], bool):
            self.errors.append(f"Invalid verification enable: must be boolean")
        
        if "enable_cot" in verification and not isinstance(verification["enable_cot"], bool):
            self.errors.append(f"Invalid verification enable_cot: must be boolean")
        
        # Validate number of samples
        num_samples = verification.get("num_samples")
        if not isinstance(num_samples, int) or num_samples <= 0 or num_samples > 10:
            self.errors.append(f"Invalid verification num_samples: {num_samples}. Must be integer between 1 and 10")
        
        # Validate confidence threshold
        confidence_threshold = verification.get("confidence_threshold")
        if not isinstance(confidence_threshold, (int, float)) or confidence_threshold < 0 or confidence_threshold > 1.0:
            self.errors.append(f"Invalid verification confidence_threshold: {confidence_threshold}. Must be between 0 and 1.0")
    
    def _validate_logging(self) -> None:
        """Validate logging configuration."""
        if "logging" not in self.config:
            return
        
        logging_config = self.config["logging"]
        
        # Validate base directory
        base_dir = logging_config.get("base_dir")
        if base_dir and not isinstance(base_dir, str):
            self.errors.append(f"Invalid logging base_dir: must be string")
        elif base_dir:
            # Check for dangerous paths
            if ".." in base_dir or base_dir.startswith("/") or "~" in base_dir:
                self.errors.append(f"Potentially dangerous logging base_dir: {base_dir}")
        
        # Validate save frequency
        save_every = logging_config.get("save_every")
        if not isinstance(save_every, int) or save_every <= 0 or save_every > 1000:
            self.errors.append(f"Invalid logging save_every: {save_every}. Must be integer between 1 and 1000")
        
        # Validate flush frequency
        flush_every = logging_config.get("flush_every")
        if not isinstance(flush_every, int) or flush_every <= 0 or flush_every > 100:
            self.errors.append(f"Invalid logging flush_every: {flush_every}. Must be integer between 1 and 100")
    
    def _validate_router(self) -> None:
        """Validate router configuration."""
        if "router" not in self.config:
            return
        
        router = self.config["router"]
        
        # Validate boolean flags
        if "enable" in router and not isinstance(router["enable"], bool):
            self.errors.append(f"Invalid router enable: must be boolean")
        
        # Validate confidence thresholds
        cloud_threshold = router.get("cloud_confidence_threshold")
        if not isinstance(cloud_threshold, (int, float)) or cloud_threshold < 0 or cloud_threshold > 1.0:
            self.errors.append(f"Invalid router cloud_confidence_threshold: {cloud_threshold}. Must be between 0 and 1.0")
        
        local_threshold = router.get("local_confidence_threshold")
        if not isinstance(local_threshold, (int, float)) or local_threshold < 0 or local_threshold > 1.0:
            self.errors.append(f"Invalid router local_confidence_threshold: {local_threshold}. Must be between 0 and 1.0")
        
        # Validate cache path
        cache_path = router.get("cache_path")
        if cache_path and not isinstance(cache_path, str):
            self.errors.append(f"Invalid router cache_path: must be string")
        elif cache_path:
            # Check for dangerous paths
            if ".." in cache_path or cache_path.startswith("/") or "~" in cache_path:
                self.errors.append(f"Potentially dangerous router cache_path: {cache_path}")
    
    def _validate_embedding(self) -> None:
        """Validate embedding configuration."""
        if "embedding" not in self.config:
            return
        
        embedding = self.config["embedding"]
        
        # Validate boolean flags
        if "use_transformer" in embedding and not isinstance(embedding["use_transformer"], bool):
            self.errors.append(f"Invalid embedding use_transformer: must be boolean")
        
        # Validate model name
        model_name = embedding.get("model_name")
        if model_name and not isinstance(model_name, str):
            self.errors.append(f"Invalid embedding model_name: must be string")
    
    def _validate_rate_limiting(self) -> None:
        """Validate rate limiting configuration."""
        if "rate_limiting" not in self.config:
            return
        
        rate_limiting = self.config["rate_limiting"]
        
        # Validate per-minute limit
        max_per_minute = rate_limiting.get("max_tasks_per_minute")
        if not isinstance(max_per_minute, int) or max_per_minute <= 0 or max_per_minute > 1000:
            self.errors.append(f"Invalid rate_limiting max_tasks_per_minute: {max_per_minute}. Must be integer between 1 and 1000")
        
        # Validate per-hour limit
        max_per_hour = rate_limiting.get("max_tasks_per_hour")
        if not isinstance(max_per_hour, int) or max_per_hour <= 0 or max_per_hour > 10000:
            self.errors.append(f"Invalid rate_limiting max_tasks_per_hour: {max_per_hour}. Must be integer between 1 and 10000")
    
    def _validate_resource_limits(self) -> None:
        """Validate resource limits configuration."""
        if "resource_limits" not in self.config:
            return
        
        resource_limits = self.config["resource_limits"]
        
        # Validate memory limit
        max_memory = resource_limits.get("max_memory_mb")
        if not isinstance(max_memory, int) or max_memory <= 0 or max_memory > 16384:  # 16GB max
            self.errors.append(f"Invalid resource_limits max_memory_mb: {max_memory}. Must be integer between 1 and 16384")
        
        # Validate CPU time limit
        max_cpu = resource_limits.get("max_cpu_seconds")
        if not isinstance(max_cpu, (int, float)) or max_cpu <= 0 or max_cpu > 3600:  # 1 hour max
            self.errors.append(f"Invalid resource_limits max_cpu_seconds: {max_cpu}. Must be between 1 and 3600")
        
        # Validate output size limit
        max_output = resource_limits.get("max_output_kb")
        if not isinstance(max_output, int) or max_output <= 0 or max_output > 10240:  # 10MB max
            self.errors.append(f"Invalid resource_limits max_output_kb: {max_output}. Must be integer between 1 and 10240")
    
    def _validate_cross_dependencies(self) -> None:
        """Validate dependencies between configuration sections."""
        # Check that shell is not enabled if not explicitly allowed
        if self.config.get("tooling", {}).get("enable_shell", False):
            allowed_shell = self.config.get("tooling", {}).get("allowed_shell", [])
            if not allowed_shell:
                self.errors.append("Shell execution is enabled but no allowed_shell commands are specified")
        
        # Check that Python is enabled if verification uses Python predicates
        if self.config.get("verification", {}).get("enable", False):
            if not self.config.get("tooling", {}).get("enable_python", True):
                self.errors.append("Verification is enabled but Python execution is disabled")
        
        # Check that domains in curriculum are valid
        curriculum_domains = self.config.get("curriculum", {}).get("domains", [])
        if curriculum_domains:
            for domain in curriculum_domains:
                if domain not in self.VALID_DOMAINS:
                    self.errors.append(f"Invalid curriculum domain: {domain}. Must be one of: {', '.join(self.VALID_DOMAINS)}")
        
        # Check rate limiting consistency (only warn, don't error)
        rate_limiting = self.config.get("rate_limiting", {})
        max_per_minute = rate_limiting.get("max_tasks_per_minute", 60)
        max_per_hour = rate_limiting.get("max_tasks_per_hour", 1000)
        
        if max_per_minute * 60 > max_per_hour:
            # This is a warning, not an error - some deployments may want aggressive per-minute limits
            self.logger.warning(f"Rate limiting configuration: max_tasks_per_minute ({max_per_minute}) * 60 > max_tasks_per_hour ({max_per_hour}). This may cause unexpected behavior.")
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        if not isinstance(url, str):
            return False
        
        # Simple URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate Agent0 configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation errors (empty if valid)
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    validator = ConfigValidator(config)
    errors = validator.validate()
    
    if errors:
        raise ConfigValidationError(f"Configuration validation failed with {len(errors)} errors: {'; '.join(errors)}")
    
    return errors