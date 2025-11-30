"""
Security event logging and monitoring for Agent0.
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


class SecurityEventType(Enum):
    """Types of security events."""
    CODE_EXECUTION_BLOCKED = "code_execution_blocked"
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONFIG_VALIDATION_FAILED = "config_validation_failed"
    MALICIOUS_INPUT_DETECTED = "malicious_input_detected"
    FILE_ACCESS_BLOCKED = "file_access_blocked"
    SUSPICIOUS_PATTERN_DETECTED = "suspicious_pattern_detected"
    INJECTION_ATTEMPT = "injection_attempt"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: SecurityEventType
    timestamp: float
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    details: Dict[str, Any]
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None


class SecurityLogger:
    """Enhanced security event logging and monitoring."""
    
    def __init__(self, log_dir: Path, enable_monitoring: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enable_monitoring = enable_monitoring
        
        # Security events log file
        self.security_log_file = self.log_dir / "security_events.jsonl"
        
        # Statistics file
        self.stats_file = self.log_dir / "security_stats.json"
        
        # Set up dedicated security logger
        self.logger = logging.getLogger("agent0.security")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for security events
        security_handler = logging.FileHandler(self.log_dir / "security.log")
        security_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(formatter)
        self.logger.addHandler(security_handler)
        
        # Security statistics
        self.stats = {
            'total_events': 0,
            'events_by_type': {event_type.value: 0 for event_type in SecurityEventType},
            'events_by_severity': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'last_event_time': 0,
            'blocked_attempts': 0,
            'start_time': time.time()
        }
        
        # Load existing stats if available
        self._load_stats()
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log a security event."""
        if details is None:
            details = {}
        
        # Create security event
        event = SecurityEvent(
            event_type=event_type,
            timestamp=time.time(),
            severity=severity.upper(),
            message=message,
            details=details,
            source_ip=source_ip,
            user_agent=user_agent,
            task_id=task_id,
            session_id=session_id
        )
        
        # Log to JSONL file
        self._log_event_to_file(event)
        
        # Log to regular logger
        log_method = self._get_log_method(severity)
        log_method(f"SECURITY: {message} | Type: {event_type.value} | Details: {json.dumps(details)}")
        
        # Update statistics
        self._update_stats(event)
        
        # Check for critical events that need immediate attention
        if severity.upper() == 'CRITICAL':
            self._handle_critical_event(event)
    
    def _log_event_to_file(self, event: SecurityEvent) -> None:
        """Log event to JSONL file."""
        try:
            with open(self.security_log_file, 'a', encoding='utf-8') as f:
                event_dict = asdict(event)
                event_dict['event_type'] = event.event_type.value  # Convert enum to string
                f.write(json.dumps(event_dict) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to log security event to file: {e}")
    
    def _get_log_method(self, severity: str):
        """Get appropriate logging method based on severity."""
        severity_upper = severity.upper()
        if severity_upper == 'CRITICAL':
            return self.logger.critical
        elif severity_upper == 'HIGH':
            return self.logger.error
        elif severity_upper == 'MEDIUM':
            return self.logger.warning
        else:
            return self.logger.info
    
    def _update_stats(self, event: SecurityEvent) -> None:
        """Update security statistics."""
        self.stats['total_events'] += 1
        self.stats['events_by_type'][event.event_type.value] += 1
        self.stats['events_by_severity'][event.severity] += 1
        self.stats['last_event_time'] = event.timestamp
        
        if event.event_type in [SecurityEventType.CODE_EXECUTION_BLOCKED, 
                               SecurityEventType.INPUT_VALIDATION_FAILED,
                               SecurityEventType.MALICIOUS_INPUT_DETECTED]:
            self.stats['blocked_attempts'] += 1
        
        # Save stats periodically
        if self.stats['total_events'] % 10 == 0:  # Save every 10 events
            self._save_stats()
    
    def _handle_critical_event(self, event: SecurityEvent) -> None:
        """Handle critical security events that need immediate attention."""
        # Log additional details for critical events
        self.logger.critical(f"CRITICAL SECURITY EVENT: {event.message}")
        self.logger.critical(f"Event details: {json.dumps(event.details, indent=2)}")
        
        # Could add additional alerting here (email, Slack, etc.)
        # For now, just ensure the event is prominently logged
    
    def _save_stats(self) -> None:
        """Save security statistics to file."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save security stats: {e}")
    
    def _load_stats(self) -> None:
        """Load existing security statistics."""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    # Merge with current stats, preserving counters
                    self.stats.update(loaded_stats)
        except Exception as e:
            self.logger.warning(f"Failed to load security stats: {e}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get a summary of security events."""
        current_time = time.time()
        uptime = current_time - self.stats['start_time']
        
        return {
            'uptime_hours': uptime / 3600,
            'total_events': self.stats['total_events'],
            'events_by_type': self.stats['events_by_type'],
            'events_by_severity': self.stats['events_by_severity'],
            'blocked_attempts': self.stats['blocked_attempts'],
            'security_score': self._calculate_security_score(),
            'last_event_time': datetime.fromtimestamp(self.stats['last_event_time']).isoformat() if self.stats['last_event_time'] > 0 else None
        }
    
    def _calculate_security_score(self) -> float:
        """Calculate a security score based on recent events."""
        if self.stats['total_events'] == 0:
            return 100.0
        
        # Weight recent events more heavily
        critical_weight = 50
        high_weight = 10
        medium_weight = 2
        low_weight = 1
        
        penalty = (
            self.stats['events_by_severity']['CRITICAL'] * critical_weight +
            self.stats['events_by_severity']['HIGH'] * high_weight +
            self.stats['events_by_severity']['MEDIUM'] * medium_weight +
            self.stats['events_by_severity']['LOW'] * low_weight
        )
        
        # Base score minus penalties
        base_score = 100.0
        score = max(0.0, base_score - penalty)
        
        return score
    
    def get_recent_events(self, limit: int = 100, severity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = []
        
        try:
            if not self.security_log_file.exists():
                return events
            
            with open(self.security_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Process lines in reverse order (most recent first)
            for line in reversed(lines):
                try:
                    event_data = json.loads(line.strip())
                    
                    # Apply severity filter if specified
                    if severity_filter and event_data.get('severity') != severity_filter.upper():
                        continue
                    
                    events.append(event_data)
                    
                    if len(events) >= limit:
                        break
                        
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
                    
        except Exception as e:
            self.logger.error(f"Failed to read security events: {e}")
        
        return events
    
    def generate_security_report(self) -> str:
        """Generate a comprehensive security report."""
        summary = self.get_security_summary()
        recent_events = self.get_recent_events(limit=10)
        
        report = []
        report.append("=" * 60)
        report.append("AGENT0 SECURITY REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Uptime: {summary['uptime_hours']:.1f} hours")
        report.append(f"Security Score: {summary['security_score']:.1f}/100")
        report.append("")
        
        report.append("EVENT SUMMARY")
        report.append("-" * 30)
        report.append(f"Total Events: {summary['total_events']}")
        report.append(f"Blocked Attempts: {summary['blocked_attempts']}")
        report.append("")
        
        report.append("EVENTS BY SEVERITY")
        report.append("-" * 30)
        for severity, count in summary['events_by_severity'].items():
            report.append(f"{severity}: {count}")
        report.append("")
        
        report.append("EVENTS BY TYPE")
        report.append("-" * 30)
        for event_type, count in summary['events_by_type'].items():
            if count > 0:
                report.append(f"{event_type}: {count}")
        report.append("")
        
        if recent_events:
            report.append("RECENT EVENTS (Last 10)")
            report.append("-" * 30)
            for event in recent_events:
                timestamp = datetime.fromtimestamp(event['timestamp']).isoformat()
                report.append(f"[{timestamp}] {event['severity']} - {event['event_type']}")
                report.append(f"  {event['message']}")
                if event['details']:
                    report.append(f"  Details: {json.dumps(event['details'])}")
                report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# Convenience functions for common security events
def log_code_execution_blocked(code: str, reason: str, security_logger: SecurityLogger, **kwargs) -> None:
    """Log code execution being blocked."""
    security_logger.log_security_event(
        event_type=SecurityEventType.CODE_EXECUTION_BLOCKED,
        severity="HIGH",
        message=f"Code execution blocked: {reason}",
        details={"code_length": len(code), "reason": reason, "code_preview": code[:100]},
        **kwargs
    )


def log_input_validation_failed(validation_errors: List[str], security_logger: SecurityLogger, **kwargs) -> None:
    """Log input validation failures."""
    security_logger.log_security_event(
        event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
        severity="MEDIUM",
        message=f"Input validation failed with {len(validation_errors)} errors",
        details={"errors": validation_errors},
        **kwargs
    )


def log_rate_limit_exceeded(limit_type: str, current: int, limit: int, security_logger: SecurityLogger, **kwargs) -> None:
    """Log rate limit exceeded events."""
    security_logger.log_security_event(
        event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
        severity="MEDIUM",
        message=f"Rate limit exceeded: {limit_type}",
        details={"limit_type": limit_type, "current": current, "limit": limit},
        **kwargs
    )


def log_malicious_input_detected(input_text: str, threat_type: str, security_logger: SecurityLogger, **kwargs) -> None:
    """Log detection of malicious input."""
    security_logger.log_security_event(
        event_type=SecurityEventType.MALICIOUS_INPUT_DETECTED,
        severity="HIGH",
        message=f"Malicious input detected: {threat_type}",
        details={"input_length": len(input_text), "threat_type": threat_type, "input_preview": input_text[:100]},
        **kwargs
    )


def log_suspicious_pattern_detected(pattern: str, context: str, security_logger: SecurityLogger, **kwargs) -> None:
    """Log detection of suspicious patterns."""
    security_logger.log_security_event(
        event_type=SecurityEventType.SUSPICIOUS_PATTERN_DETECTED,
        severity="MEDIUM",
        message=f"Suspicious pattern detected: {pattern}",
        details={"pattern": pattern, "context": context},
        **kwargs
    )


def log_injection_attempt(injection_type: str, payload: str, security_logger: SecurityLogger, **kwargs) -> None:
    """Log injection attempts."""
    security_logger.log_security_event(
        event_type=SecurityEventType.INJECTION_ATTEMPT,
        severity="CRITICAL",
        message=f"Injection attempt detected: {injection_type}",
        details={"injection_type": injection_type, "payload_length": len(payload), "payload_preview": payload[:100]},
        **kwargs
    )


def log_resource_limit_exceeded(resource_type: str, current: float, limit: float, security_logger: SecurityLogger, **kwargs) -> None:
    """Log resource limit exceeded events."""
    security_logger.log_security_event(
        event_type=SecurityEventType.RESOURCE_LIMIT_EXCEEDED,
        severity="HIGH",
        message=f"Resource limit exceeded: {resource_type}",
        details={"resource_type": resource_type, "current": current, "limit": limit, "percentage": (current/limit)*100},
        **kwargs
    )