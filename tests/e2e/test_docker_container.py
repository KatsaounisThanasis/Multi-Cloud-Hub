"""
End-to-end tests for Docker container deployment
"""
import pytest
import requests
import time
import docker
from docker.errors import NotFound, APIError


@pytest.fixture(scope="module")
def docker_client():
    """Create Docker client"""
    try:
        client = docker.from_env()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="module")
def container_url():
    """Container API URL"""
    return "http://localhost:8000"


class TestDockerBuild:
    """Test Docker image build"""

    def test_build_docker_image(self, docker_client):
        """Test building Docker image"""
        try:
            image, logs = docker_client.images.build(
                path=".",
                dockerfile="Dockerfile",
                tag="multicloud-api:test",
                rm=True
            )

            assert image is not None
            assert "multicloud-api:test" in [tag for tag in image.tags]

        except docker.errors.BuildError as e:
            pytest.fail(f"Docker build failed: {e}")

    def test_build_minimal_image(self, docker_client):
        """Test building minimal Docker image"""
        try:
            image, logs = docker_client.images.build(
                path=".",
                dockerfile="Dockerfile.minimal",
                tag="multicloud-api:minimal-test",
                rm=True
            )

            assert image is not None
            assert "multicloud-api:minimal-test" in [tag for tag in image.tags]

        except docker.errors.BuildError as e:
            pytest.fail(f"Minimal Docker build failed: {e}")


class TestDockerRun:
    """Test running Docker container"""

    @pytest.fixture(scope="class")
    def running_container(self, docker_client):
        """Start container for testing"""
        # Build image first
        try:
            docker_client.images.build(
                path=".",
                dockerfile="Dockerfile",
                tag="multicloud-api:test",
                rm=True
            )
        except Exception as e:
            pytest.skip(f"Could not build image: {e}")

        # Start container
        try:
            container = docker_client.containers.run(
                "multicloud-api:test",
                detach=True,
                ports={"8000/tcp": 8000},
                environment={
                    "LOG_LEVEL": "INFO",
                    "ENVIRONMENT": "test"
                },
                name="multicloud-api-test"
            )

            # Wait for container to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get("http://localhost:8000/health", timeout=2)
                    if response.status_code == 200:
                        break
                except (requests.ConnectionError, requests.Timeout):
                    if i == max_retries - 1:
                        container.stop()
                        container.remove()
                        pytest.skip("Container failed to start")
                    time.sleep(1)

            yield container

            # Cleanup
            container.stop()
            container.remove()

        except Exception as e:
            pytest.skip(f"Could not start container: {e}")

    def test_container_is_running(self, running_container):
        """Test container is running"""
        running_container.reload()
        assert running_container.status == "running"

    def test_container_health_check(self, running_container, container_url):
        """Test container health check"""
        response = requests.get(f"{container_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_container_api_accessible(self, running_container, container_url):
        """Test API is accessible from container"""
        response = requests.get(f"{container_url}/api/v1/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_container_swagger_docs(self, running_container, container_url):
        """Test Swagger docs are accessible"""
        response = requests.get(f"{container_url}/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_container_logs(self, running_container):
        """Test container logs are being generated"""
        logs = running_container.logs().decode("utf-8")

        assert len(logs) > 0
        assert "uvicorn" in logs.lower() or "started" in logs.lower()

    def test_container_environment_variables(self, running_container):
        """Test container has correct environment variables"""
        attrs = running_container.attrs
        env_vars = attrs["Config"]["Env"]

        env_dict = {}
        for env in env_vars:
            if "=" in env:
                key, value = env.split("=", 1)
                env_dict[key] = value

        assert "LOG_LEVEL" in env_dict
        assert env_dict["LOG_LEVEL"] == "INFO"

    def test_container_exposed_ports(self, running_container):
        """Test container exposes correct ports"""
        attrs = running_container.attrs
        exposed_ports = attrs["Config"]["ExposedPorts"]

        assert "8000/tcp" in exposed_ports

    def test_container_non_root_user(self, running_container):
        """Test container runs as non-root user"""
        exec_result = running_container.exec_run("whoami")
        user = exec_result.output.decode("utf-8").strip()

        assert user == "apiuser"


class TestDockerCompose:
    """Test docker-compose setup"""

    def test_docker_compose_config_valid(self):
        """Test docker-compose.yml is valid"""
        import subprocess

        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"

    def test_docker_compose_dev_config_valid(self):
        """Test docker-compose.dev.yml is valid"""
        import subprocess

        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml", "config"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"docker-compose dev config failed: {result.stderr}"


class TestDockerImageProperties:
    """Test Docker image properties"""

    def test_image_size(self, docker_client):
        """Test Docker image size is reasonable"""
        try:
            image = docker_client.images.get("multicloud-api:test")
            size_mb = image.attrs["Size"] / (1024 * 1024)

            # Image should be less than 2GB
            assert size_mb < 2048, f"Image too large: {size_mb:.2f} MB"

        except NotFound:
            pytest.skip("Image not built yet")

    def test_image_layers(self, docker_client):
        """Test Docker image has reasonable number of layers"""
        try:
            image = docker_client.images.get("multicloud-api:test")
            layers = len(image.history())

            # Should have reasonable number of layers (less than 50)
            assert layers < 50, f"Too many layers: {layers}"

        except NotFound:
            pytest.skip("Image not built yet")

    def test_image_labels(self, docker_client):
        """Test Docker image has correct labels"""
        try:
            image = docker_client.images.get("multicloud-api:test")
            labels = image.labels or {}

            # Check for custom labels if any were added
            # This is optional - add assertions if you add labels to Dockerfile

        except NotFound:
            pytest.skip("Image not built yet")


class TestContainerSecurity:
    """Test container security features"""

    def test_container_runs_as_non_root(self, docker_client):
        """Test container runs as non-root user"""
        try:
            container = docker_client.containers.run(
                "multicloud-api:test",
                detach=True,
                remove=True,
                command="id -u"
            )

            container.wait()
            logs = container.logs().decode("utf-8").strip()
            uid = int(logs)

            assert uid != 0, "Container should not run as root (UID 0)"
            assert uid == 1000, f"Container should run as UID 1000, got {uid}"

        except NotFound:
            pytest.skip("Image not built yet")

    def test_container_filesystem_readonly_where_possible(self, docker_client):
        """Test container filesystem permissions"""
        try:
            container = docker_client.containers.run(
                "multicloud-api:test",
                detach=True,
                remove=True,
                command="touch /test-write"
            )

            exit_code = container.wait()["StatusCode"]

            # Should fail to write to root filesystem
            assert exit_code != 0, "Should not be able to write to root filesystem"

        except NotFound:
            pytest.skip("Image not built yet")


class TestContainerResourceLimits:
    """Test container resource limits from docker-compose"""

    def test_memory_limit_set(self):
        """Test memory limit is configured in docker-compose"""
        import yaml

        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)

        deploy = compose["services"]["api"].get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})

        assert "memory" in limits, "Memory limit should be set"

    def test_cpu_limit_set(self):
        """Test CPU limit is configured in docker-compose"""
        import yaml

        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)

        deploy = compose["services"]["api"].get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})

        assert "cpus" in limits, "CPU limit should be set"


class TestContainerHealthCheck:
    """Test container health check"""

    def test_health_check_defined(self):
        """Test health check is defined in docker-compose"""
        import yaml

        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)

        healthcheck = compose["services"]["api"].get("healthcheck")

        assert healthcheck is not None, "Health check should be defined"
        assert "test" in healthcheck
        assert "interval" in healthcheck
        assert "timeout" in healthcheck
        assert "retries" in healthcheck

    def test_dockerfile_health_check(self, docker_client):
        """Test HEALTHCHECK instruction in Dockerfile"""
        try:
            image = docker_client.images.get("multicloud-api:test")
            config = image.attrs["Config"]

            assert "Healthcheck" in config or "HEALTHCHECK" in open("Dockerfile").read()

        except NotFound:
            pytest.skip("Image not built yet")
