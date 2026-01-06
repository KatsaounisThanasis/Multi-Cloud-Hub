"""
Unit tests for Metrics module
"""
import pytest
import time

from backend.core.metrics import (
    MetricsRegistry,
    metrics,
    record_request,
    record_deployment_started,
    record_deployment_completed,
    record_auth_attempt,
    record_rate_limit_hit,
    set_active_deployments,
    set_connected_users,
    timed,
    async_timed,
    get_metrics_text
)


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_singleton_pattern(self):
        """Test that MetricsRegistry is a singleton."""
        registry1 = MetricsRegistry()
        registry2 = MetricsRegistry()
        assert registry1 is registry2

    def test_increment_counter(self):
        """Test counter increment."""
        registry = MetricsRegistry()
        registry.increment_counter("test_counter_1")
        registry.increment_counter("test_counter_1")
        registry.increment_counter("test_counter_1", value=5)

        # Counter should be at 7
        assert registry.counters["test_counter_1"][""] == 7

    def test_increment_counter_with_labels(self):
        """Test counter increment with labels."""
        registry = MetricsRegistry()
        labels = {"method": "GET", "path": "/api"}
        registry.increment_counter("test_labeled_counter", labels=labels)
        registry.increment_counter("test_labeled_counter", labels=labels)

        label_key = registry._labels_to_key(labels)
        assert registry.counters["test_labeled_counter"][label_key] == 2

    def test_set_gauge(self):
        """Test gauge setting."""
        registry = MetricsRegistry()
        registry.set_gauge("test_gauge_1", 42.5)
        assert registry.gauges["test_gauge_1"][""] == 42.5

        registry.set_gauge("test_gauge_1", 100.0)
        assert registry.gauges["test_gauge_1"][""] == 100.0

    def test_set_gauge_with_labels(self):
        """Test gauge setting with labels."""
        registry = MetricsRegistry()
        labels = {"instance": "api-1"}
        registry.set_gauge("test_labeled_gauge", 50.0, labels=labels)

        label_key = registry._labels_to_key(labels)
        assert registry.gauges["test_labeled_gauge"][label_key] == 50.0

    def test_observe_histogram(self):
        """Test histogram observation."""
        registry = MetricsRegistry()
        registry.observe_histogram("test_histogram_1", 0.5)
        registry.observe_histogram("test_histogram_1", 1.0)
        registry.observe_histogram("test_histogram_1", 0.75)

        assert len(registry.histograms["test_histogram_1"][""]) == 3
        assert sum(registry.histograms["test_histogram_1"][""]) == 2.25

    def test_labels_to_key(self):
        """Test label key conversion."""
        registry = MetricsRegistry()

        # Empty labels
        assert registry._labels_to_key(None) == ""
        assert registry._labels_to_key({}) == ""

        # Single label
        key = registry._labels_to_key({"method": "GET"})
        assert key == 'method="GET"'

        # Multiple labels (should be sorted)
        key = registry._labels_to_key({"method": "POST", "code": "200"})
        assert key == 'code="200",method="POST"'

    def test_export_prometheus(self):
        """Test Prometheus format export."""
        registry = MetricsRegistry()

        # Add some metrics
        registry.increment_counter("export_test_counter")
        registry.set_gauge("export_test_gauge", 123.0)
        registry.observe_histogram("export_test_histogram", 0.5)

        output = registry.export_prometheus()

        # Check that metrics are in output
        assert "export_test_counter" in output
        assert "export_test_gauge" in output
        assert "export_test_histogram" in output
        assert "# TYPE" in output
        assert "# HELP" in output


class TestHelperFunctions:
    """Tests for metric helper functions."""

    def test_record_request(self):
        """Test request recording."""
        record_request("GET", "/api/test", 200, 0.05)

        # Verify counter was incremented
        output = get_metrics_text()
        assert "http_requests_total" in output

    def test_record_deployment_started(self):
        """Test deployment started recording."""
        record_deployment_started("azure", "storage-account")

        output = get_metrics_text()
        assert "deployments_started_total" in output

    def test_record_deployment_completed(self):
        """Test deployment completed recording."""
        record_deployment_completed("gcp", "compute-instance", True, 120.5)
        record_deployment_completed("azure", "vm", False, 60.0)

        output = get_metrics_text()
        assert "deployments_completed_total" in output
        assert "deployment_duration_seconds" in output

    def test_record_auth_attempt(self):
        """Test auth attempt recording."""
        record_auth_attempt(True)
        record_auth_attempt(False, reason="invalid_password")

        output = get_metrics_text()
        assert "auth_attempts_total" in output

    def test_record_rate_limit_hit(self):
        """Test rate limit hit recording."""
        record_rate_limit_hit("/auth/login")

        output = get_metrics_text()
        assert "rate_limit_hits_total" in output

    def test_set_active_deployments(self):
        """Test active deployments gauge."""
        set_active_deployments(5)

        output = get_metrics_text()
        assert "active_deployments" in output

    def test_set_connected_users(self):
        """Test connected users gauge."""
        set_connected_users(100)

        output = get_metrics_text()
        assert "connected_users" in output


class TestTimedDecorators:
    """Tests for timed decorators."""

    def test_timed_decorator(self):
        """Test synchronous timed decorator."""
        @timed("sync_function_duration", {"function": "test_func"})
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"

        output = get_metrics_text()
        assert "sync_function_duration" in output

    @pytest.mark.asyncio
    async def test_async_timed_decorator(self):
        """Test asynchronous timed decorator."""
        import asyncio

        @async_timed("async_function_duration", {"function": "async_test"})
        async def async_slow_function():
            await asyncio.sleep(0.01)
            return "async done"

        result = await async_slow_function()
        assert result == "async done"

        output = get_metrics_text()
        assert "async_function_duration" in output


class TestGetMetricsText:
    """Tests for get_metrics_text function."""

    def test_returns_string(self):
        """Test that get_metrics_text returns a string."""
        output = get_metrics_text()
        assert isinstance(output, str)

    def test_ends_with_newline(self):
        """Test that output ends with newline."""
        output = get_metrics_text()
        assert output.endswith("\n")
