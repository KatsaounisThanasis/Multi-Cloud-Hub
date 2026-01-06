"""
Prometheus Metrics Module

This module provides application metrics for monitoring and observability.
Metrics are exposed at /metrics endpoint in Prometheus format.
"""

import time
from typing import Callable, Optional
from functools import wraps
from collections import defaultdict
import threading
import os

# Simple in-memory metrics storage (for environments without prometheus_client)
# In production, consider using prometheus_client library

class MetricsRegistry:
    """
    Simple metrics registry for tracking application metrics.

    Provides counters, gauges, and histograms without external dependencies.
    For production, replace with prometheus_client library.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize metrics storage."""
        self.counters = defaultdict(lambda: defaultdict(int))
        self.gauges = defaultdict(lambda: defaultdict(float))
        self.histograms = defaultdict(lambda: defaultdict(list))
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: int = 1, labels: Optional[dict] = None):
        """Increment a counter metric."""
        label_key = self._labels_to_key(labels)
        with self._lock:
            self.counters[name][label_key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[dict] = None):
        """Set a gauge metric value."""
        label_key = self._labels_to_key(labels)
        with self._lock:
            self.gauges[name][label_key] = value

    def observe_histogram(self, name: str, value: float, labels: Optional[dict] = None):
        """Record a histogram observation."""
        label_key = self._labels_to_key(labels)
        with self._lock:
            self.histograms[name][label_key].append(value)
            # Keep only last 1000 observations to prevent memory issues
            if len(self.histograms[name][label_key]) > 1000:
                self.histograms[name][label_key] = self.histograms[name][label_key][-1000:]

    def _labels_to_key(self, labels: Optional[dict]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def _key_to_labels(self, key: str) -> str:
        """Format label key for Prometheus output."""
        if not key:
            return ""
        return "{" + key + "}"

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        # Export counters
        for name, values in self.counters.items():
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            for label_key, value in values.items():
                labels = self._key_to_labels(label_key)
                lines.append(f"{name}{labels} {value}")

        # Export gauges
        for name, values in self.gauges.items():
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            for label_key, value in values.items():
                labels = self._key_to_labels(label_key)
                lines.append(f"{name}{labels} {value}")

        # Export histograms (as summary for simplicity)
        for name, values in self.histograms.items():
            lines.append(f"# HELP {name} Histogram metric")
            lines.append(f"# TYPE {name} summary")
            for label_key, observations in values.items():
                if observations:
                    labels = self._key_to_labels(label_key)
                    count = len(observations)
                    total = sum(observations)
                    lines.append(f"{name}_count{labels} {count}")
                    lines.append(f"{name}_sum{labels} {total}")

        return "\n".join(lines) + "\n"


# Global metrics registry instance
metrics = MetricsRegistry()


# =============================================================================
# Pre-defined Metrics
# =============================================================================

# HTTP Request metrics
def record_request(method: str, path: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    labels = {"method": method, "path": path, "status": str(status_code)}
    metrics.increment_counter("http_requests_total", labels=labels)
    metrics.observe_histogram("http_request_duration_seconds", duration, labels={"method": method, "path": path})


# Deployment metrics
def record_deployment_started(provider: str, template: str):
    """Record deployment start."""
    labels = {"provider": provider, "template": template}
    metrics.increment_counter("deployments_started_total", labels=labels)


def record_deployment_completed(provider: str, template: str, success: bool, duration: float):
    """Record deployment completion."""
    status = "success" if success else "failure"
    labels = {"provider": provider, "template": template, "status": status}
    metrics.increment_counter("deployments_completed_total", labels=labels)
    metrics.observe_histogram("deployment_duration_seconds", duration, labels={"provider": provider})


# Authentication metrics
def record_auth_attempt(success: bool, reason: Optional[str] = None):
    """Record authentication attempt."""
    status = "success" if success else "failure"
    labels = {"status": status}
    if reason:
        labels["reason"] = reason
    metrics.increment_counter("auth_attempts_total", labels=labels)


def record_rate_limit_hit(path: str):
    """Record rate limit hit."""
    metrics.increment_counter("rate_limit_hits_total", labels={"path": path})


# System metrics
def set_active_deployments(count: int):
    """Set the number of active deployments."""
    metrics.set_gauge("active_deployments", count)


def set_connected_users(count: int):
    """Set the number of connected users."""
    metrics.set_gauge("connected_users", count)


# =============================================================================
# Decorator for timing functions
# =============================================================================

def timed(metric_name: str, labels: Optional[dict] = None):
    """
    Decorator to time function execution and record as histogram.

    Usage:
        @timed("function_duration_seconds", {"function": "process_data"})
        def process_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels=labels)
        return wrapper
    return decorator


def async_timed(metric_name: str, labels: Optional[dict] = None):
    """
    Async decorator to time function execution and record as histogram.

    Usage:
        @async_timed("async_function_duration_seconds", {"function": "fetch_data"})
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels=labels)
        return wrapper
    return decorator


# =============================================================================
# Metrics Endpoint
# =============================================================================

def get_metrics_text() -> str:
    """Get all metrics in Prometheus text format."""
    return metrics.export_prometheus()
