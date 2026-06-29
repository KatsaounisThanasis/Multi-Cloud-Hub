"""
Unit tests for backend/tasks/deployment_tasks.py

Covers the pure log helpers plus the Celery deployment tasks. The Celery tasks
are exercised by calling their underlying ``.run`` callable (Celery binds
``self`` automatically) against an in-memory SQLite database, with the cloud
provider and ``update_state`` mocked out so no broker/credentials are needed.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.tasks.deployment_tasks as dt
from backend.core.database import Base, Deployment, DeploymentStatus, TerraformState
from backend.providers.base import DeploymentError


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class TestStripAnsiCodes:
    def test_empty_input_returned_as_is(self):
        assert dt.strip_ansi_codes("") == ""
        assert dt.strip_ansi_codes(None) is None

    def test_removes_ansi_color_sequences(self):
        colored = "\x1b[31mError\x1b[0m happened"
        assert dt.strip_ansi_codes(colored) == "Error happened"

    def test_removes_box_drawing_characters(self):
        boxed = "│ some output ╵"
        assert "│" not in dt.strip_ansi_codes(boxed)
        assert "╵" not in dt.strip_ansi_codes(boxed)

    def test_collapses_whitespace_and_blank_lines(self):
        messy = "line1   with    spaces\n\n\nline2"
        cleaned = dt.strip_ansi_codes(messy)
        assert "   " not in cleaned
        assert "\n\n\n" not in cleaned


class TestLogEntry:
    def test_basic_entry_has_timestamp_level_and_message(self):
        entry = dt.log_entry("INFO", "hello")
        assert "[INFO]" in entry
        assert "hello" in entry
        assert entry.endswith("\n")

    def test_phase_is_uppercased(self):
        entry = dt.log_entry("INFO", "msg", phase="validating")
        assert "[VALIDATING]" in entry

    def test_details_serialized_as_json(self):
        entry = dt.log_entry("ERROR", "boom", details={"code": 42})
        assert '"code": 42' in entry

    def test_timestamp_is_iso_parseable(self):
        entry = dt.log_entry("DEBUG", "x")
        ts = entry.split("]")[0].lstrip("[")
        # Should not raise
        datetime.fromisoformat(ts)


# ---------------------------------------------------------------------------
# DB-backed task fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def db_session(monkeypatch):
    """In-memory SQLite shared across all SessionLocal() calls in the module."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # The task code (and DatabaseTask) resolves SessionLocal from this module.
    monkeypatch.setattr(dt, "SessionLocal", TestSession)
    # Avoid touching the Celery result backend.
    monkeypatch.setattr(dt.deploy_infrastructure, "update_state", MagicMock())
    # DatabaseTask caches its session on the singleton task; after_return (which
    # clears it) is not invoked when calling .run() directly, so reset it here to
    # avoid a stale session leaking across tests.
    monkeypatch.setattr(dt.deploy_infrastructure, "_db", None, raising=False)

    session = TestSession()
    try:
        yield session
    finally:
        session.close()


def _seed_deployment(session, provider_type="terraform-azure", **overrides):
    deployment = Deployment(
        deployment_id=overrides.get("deployment_id", "dep-123"),
        provider_type=provider_type,
        cloud_provider=overrides.get("cloud_provider", "azure"),
        template_name="vm-template",
        resource_group="rg-test",
        status=DeploymentStatus.PENDING,
        logs="",
    )
    session.add(deployment)
    session.commit()
    return deployment


def _fake_provider(outputs=None, raises=None):
    provider = MagicMock()

    async def _deploy(**kwargs):
        if raises is not None:
            raise raises
        result = MagicMock()
        result.outputs = outputs if outputs is not None else {}
        return result

    provider.deploy = _deploy
    return provider


class TestDeployInfrastructure:
    def test_successful_deployment_marks_completed(self, db_session, monkeypatch):
        _seed_deployment(db_session)
        monkeypatch.setattr(
            dt.ProviderFactory,
            "create_provider",
            lambda *a, **k: _fake_provider(outputs={"ip": "1.2.3.4"}),
        )

        result = dt.deploy_infrastructure.run(
            deployment_id="dep-123",
            provider_type="terraform-azure",
            template_path="/tmp/main.tf",
            parameters={"size": "small"},
            resource_group="rg-test",
            provider_config={"subscription_id": "sub-1", "region": "westeurope"},
        )

        assert result["status"] == "completed"
        assert result["outputs"] == {"ip": "1.2.3.4"}

        db_session.expire_all()
        row = db_session.query(Deployment).filter_by(deployment_id="dep-123").first()
        assert row.status == DeploymentStatus.COMPLETED
        assert row.completed_at is not None
        assert row.outputs == {"ip": "1.2.3.4"}

    def test_gcp_tags_remapped_to_labels(self, db_session, monkeypatch):
        _seed_deployment(db_session, provider_type="terraform-gcp", cloud_provider="gcp")
        captured = {}

        def _factory(*a, **k):
            provider = MagicMock()

            async def _deploy(**kwargs):
                captured.update(kwargs["parameters"])
                result = MagicMock()
                result.outputs = {}
                return result

            provider.deploy = _deploy
            return provider

        monkeypatch.setattr(dt.ProviderFactory, "create_provider", _factory)

        dt.deploy_infrastructure.run(
            deployment_id="dep-123",
            provider_type="terraform-gcp",
            template_path="/tmp/main.tf",
            parameters={"tags": {"env": "test"}, "projectId": "proj-9"},
            provider_config={"region": "europe-west1"},
        )

        assert "labels" in captured and captured["labels"] == {"env": "test"}
        assert "tags" not in captured
        assert captured["project_id"] == "proj-9"
        assert "resource_group_name" not in captured

    def test_deployment_error_marks_failed_and_raises(self, db_session, monkeypatch):
        _seed_deployment(db_session)
        monkeypatch.setattr(
            dt.ProviderFactory,
            "create_provider",
            lambda *a, **k: _fake_provider(raises=DeploymentError("terraform exploded", "terraform-azure")),
        )

        with pytest.raises(RuntimeError):
            dt.deploy_infrastructure.run(
                deployment_id="dep-123",
                provider_type="terraform-azure",
                template_path="/tmp/main.tf",
                parameters={},
                resource_group="rg-test",
                provider_config={"region": "westeurope"},
            )

        db_session.expire_all()
        row = db_session.query(Deployment).filter_by(deployment_id="dep-123").first()
        assert row.status == DeploymentStatus.FAILED
        assert row.error_message

    def test_unexpected_error_marks_failed_and_raises(self, db_session, monkeypatch):
        _seed_deployment(db_session)
        monkeypatch.setattr(
            dt.ProviderFactory,
            "create_provider",
            lambda *a, **k: _fake_provider(raises=ValueError("boom")),
        )

        with pytest.raises(RuntimeError):
            dt.deploy_infrastructure.run(
                deployment_id="dep-123",
                provider_type="terraform-azure",
                template_path="/tmp/main.tf",
                parameters={},
                resource_group="rg-test",
                provider_config={"region": "westeurope"},
            )

        db_session.expire_all()
        row = db_session.query(Deployment).filter_by(deployment_id="dep-123").first()
        assert row.status == DeploymentStatus.FAILED


class TestGetDeploymentStatus:
    def test_returns_to_dict_for_existing(self, db_session):
        _seed_deployment(db_session)
        out = dt.get_deployment_status.run(deployment_id="dep-123")
        assert out["deployment_id"] == "dep-123"
        assert out["status"] == DeploymentStatus.PENDING.value

    def test_returns_not_found_for_missing(self, db_session):
        out = dt.get_deployment_status.run(deployment_id="nope")
        assert out["status"] == "not_found"


class TestCleanupTasks:
    def test_cleanup_deployment_missing_is_noop(self, db_session):
        # Should simply log and return without raising.
        assert dt.cleanup_deployment.run(deployment_id="missing") is None

    def test_cleanup_deployment_with_terraform_state(self, db_session):
        _seed_deployment(db_session, provider_type="terraform-azure")
        db_session.add(
            TerraformState(
                deployment_id="dep-123",
                backend_type="azurerm",
                backend_config={"key": "value"},
            )
        )
        db_session.commit()
        assert dt.cleanup_deployment.run(deployment_id="dep-123") is None

    def test_cleanup_old_deployments_runs(self, db_session):
        old = _seed_deployment(db_session, deployment_id="old-1")
        old.status = DeploymentStatus.COMPLETED
        old.completed_at = datetime.utcnow() - timedelta(days=60)
        db_session.commit()
        # Should not raise; selects and "archives" (logs) old deployments.
        assert dt.cleanup_old_deployments.run(days=30) is None
