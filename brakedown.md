 🏗️ Multi-Cloud Infrastructure Management API - Complete Breakdown

  📋 Table of Contents

  1. #architecture
  2. #request-flow
  3. #components
  4. #database
  5. #deployment
  6. #docker
  7. #structure

  ---
  🎯 Architecture Overview {#architecture}

  ┌─────────────┐
  │   Client    │ (cURL, Postman, Frontend)
  └──────┬──────┘
         │ HTTP Request
         ↓
  ┌──────────────────────────────────────┐
  │         FastAPI (api_rest.py)        │
  │  - Endpoints (/deploy, /templates)   │
  │  - Request validation (Pydantic)     │
  │  - Database session management       │
  └──────┬───────────────────────────────┘
         │
         ├─────→ PostgreSQL (Deployment records)
         │
         ├─────→ Celery (Queue async task)
         │
         └─────→ Template Manager (Find templates)

  ┌──────────────────────────────────────┐
  │         Redis Message Broker         │
  │    (Queue for Celery tasks)          │
  └──────┬───────────────────────────────┘
         │
         ↓
  ┌──────────────────────────────────────┐
  │        Celery Worker Process         │
  │  - Picks up deployment tasks         │
  │  - Creates provider instance         │
  │  - Executes deployment               │
  │  - Updates database with results     │
  └──────┬───────────────────────────────┘
         │
         ├─────→ Azure (Bicep deployment)
         ├─────→ AWS (Terraform)
         └─────→ GCP (Terraform)

  ---
  🔄 Request Flow (End-to-End) {#request-flow}

  Scenario: User deploys an S3 bucket on AWS

  Step 1: Client sends deployment request

  POST http://localhost:8000/deploy
  {
    "template_name": "storage-bucket",
    "provider_type": "terraform-aws",
    "subscription_id": "123456789012",
    "resource_group": "my-resources",
    "location": "us-east-1",
    "parameters": {
      "bucket_name": "my-awesome-bucket"
    }
  }

  Step 2: FastAPI receives request (api_rest.py:297)

  async def deploy_infrastructure(request: DeploymentRequest, db: Session = Depends(get_db)):

  What happens:
  1. Validates request using Pydantic model
  2. Checks template exists via template_manager.get_template_path()
  3. Generates deployment ID: deploy-a1b2c3d4e5f6
  4. Creates database record:
  deployment = Deployment(
      deployment_id="deploy-a1b2c3d4e5f6",
      provider_type="terraform-aws",
      cloud_provider="aws",
      template_name="storage-bucket",
      resource_group="my-resources",
      status=PENDING,
      parameters={"bucket_name": "my-awesome-bucket"}
  )
  db.add(deployment)
  db.commit()

  Step 3: Queue Celery task (api_rest.py:346)

  task = deploy_task.delay(
      deployment_id="deploy-a1b2c3d4e5f6",
      provider_type="terraform-aws",
      template_path="/app/templates/terraform/aws/storage-bucket.tf",
      parameters={"bucket_name": "my-awesome-bucket"},
      resource_group="my-resources",
      provider_config={
          "subscription_id": "123456789012",
          "region": "us-east-1"
      }
  )

  What happens:
  - Celery serializes task data to JSON
  - Sends to Redis queue
  - Redis stores in list: celery:tasks
  - Returns immediately to client

  Step 4: FastAPI returns response (202 Accepted)

  {
    "success": true,
    "message": "Deployment queued successfully",
    "data": {
      "deployment_id": "deploy-a1b2c3d4e5f6",
      "status": "pending",
      "task_id": "celery-task-uuid-here",
      "template": "storage-bucket"
    }
  }

  ⏱️ Total time: ~100-200ms (non-blocking!)

  ---
  Step 5: Celery Worker picks up task (tasks.py:37)

  Celery worker is running in background:
  celery -A backend.celery_app worker --loglevel=info

  Worker sees new task in Redis and executes:
  @celery_app.task(bind=True, base=DatabaseTask)
  def deploy_infrastructure(self, deployment_id, provider_type, ...):

  What happens:
  1. Gets deployment from DB:
  deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
  2. Updates status to RUNNING:
  deployment.status = DeploymentStatus.RUNNING
  deployment.started_at = datetime.utcnow()
  db.commit()
  3. Updates Celery task state (for real-time monitoring):
  self.update_state(
      state="RUNNING",
      meta={"status": "initializing", "progress": 10}
  )

  Step 6: Create Provider Instance (tasks.py:62)

  provider = ProviderFactory.create_provider(
      "terraform-aws",
      subscription_id="123456789012",
      region="us-east-1"
  )

  Provider Factory logic (providers/factory.py:54):
  def create_provider(provider_type: str, **kwargs):
      if provider_type == "terraform-aws":
          return TerraformProvider(
              cloud_platform="aws",
              region=kwargs.get("region"),
              subscription_id=kwargs.get("subscription_id")
          )

  TerraformProvider initialization (providers/terraform_provider.py:39):
  def __init__(self, subscription_id, region, cloud_platform="aws"):
      super().__init__(subscription_id, region)
      self.cloud_platform = "aws"
      self.working_dir = tempfile.mkdtemp(prefix="terraform_")  # /tmp/terraform_xyz/

      # Verify Terraform installed
      if not self._check_terraform_installed():
          raise ProviderConfigurationError("Terraform not installed")

  Step 7: Execute Deployment (tasks.py:73)

  result = provider.deploy(
      template_path="/app/templates/terraform/aws/storage-bucket.tf",
      resource_group_name="my-resources",
      parameters={"bucket_name": "my-awesome-bucket"}
  )

  Inside TerraformProvider.deploy() (providers/terraform_provider.py:320):

  7a. Setup Terraform workspace
  # Copy template to working directory
  shutil.copy(template_path, f"{self.working_dir}/main.tf")

  # Create terraform.tfvars with parameters
  with open(f"{self.working_dir}/terraform.tfvars", "w") as f:
      f.write('bucket_name = "my-awesome-bucket"\n')

  7b. Generate provider configuration
  # Create providers.tf
  provider_config = {
      "provider": {
          "aws": {
              "region": "us-east-1"
          }
      }
  }
  with open(f"{self.working_dir}/providers.tf", "w") as f:
      json.dump(provider_config, f)

  7c. Run Terraform init
  subprocess.run(
      ["terraform", "init"],
      cwd=self.working_dir,
      check=True,
      capture_output=True
  )
  Output:
  Initializing provider plugins...
  - Finding latest version of hashicorp/aws...
  - Installing hashicorp/aws v5.31.0...
  Terraform has been successfully initialized!

  7d. Run Terraform plan
  subprocess.run(
      ["terraform", "plan", "-out=tfplan"],
      cwd=self.working_dir,
      check=True
  )

  7e. Run Terraform apply
  subprocess.run(
      ["terraform", "apply", "-auto-approve", "tfplan"],
      cwd=self.working_dir,
      check=True
  )
  Output:
  aws_s3_bucket.main: Creating...
  aws_s3_bucket.main: Creation complete after 2s [id=my-awesome-bucket]

  Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

  7f. Get outputs
  result = subprocess.run(
      ["terraform", "output", "-json"],
      cwd=self.working_dir,
      capture_output=True,
      text=True
  )
  outputs = json.loads(result.stdout)

  ⏱️ Total deployment time: 2-10 minutes

  ---
  Step 8: Update Database with Results (tasks.py:87)

  Success case:
  deployment.status = DeploymentStatus.COMPLETED
  deployment.completed_at = datetime.utcnow()
  deployment.outputs = {
      "bucket_name": "my-awesome-bucket",
      "bucket_arn": "arn:aws:s3:::my-awesome-bucket",
      "bucket_region": "us-east-1"
  }
  db.commit()

  Failure case:
  except DeploymentError as e:
      deployment.status = DeploymentStatus.FAILED
      deployment.error_message = str(e)
      deployment.logs = traceback.format_exc()
      db.commit()

  ---
  Step 9: Client checks status

  While deployment is running:
  GET http://localhost:8000/deployments/deploy-a1b2c3d4e5f6/status

  Response:
  {
    "deployment_id": "deploy-a1b2c3d4e5f6",
    "status": "running",
    "started_at": "2025-11-09T12:00:00",
    "duration_seconds": 45.2,
    "provider_type": "terraform-aws",
    "template_name": "storage-bucket"
  }

  After completion:
  {
    "deployment_id": "deploy-a1b2c3d4e5f6",
    "status": "completed",
    "started_at": "2025-11-09T12:00:00",
    "completed_at": "2025-11-09T12:02:30",
    "duration_seconds": 150.0,
    "outputs": {
      "bucket_name": "my-awesome-bucket",
      "bucket_arn": "arn:aws:s3:::my-awesome-bucket"
    }
  }

  ---
  🧩 Core Components Deep Dive {#components}

  1. FastAPI Application (backend/api_rest.py)

  Purpose: HTTP API layer

  Key responsibilities:
  - Receive HTTP requests
  - Validate input (Pydantic models)
  - Manage database sessions
  - Queue tasks to Celery
  - Return responses

  Key endpoints:

  | Endpoint                     | Method | Purpose               |
  |------------------------------|--------|-----------------------|
  | /health                      | GET    | Health check          |
  | /providers                   | GET    | List cloud providers  |
  | /templates                   | GET    | List templates        |
  | /templates/{provider}/{name} | GET    | Get template details  |
  | /deploy                      | POST   | Queue deployment      |
  | /deployments                 | GET    | List all deployments  |
  | /deployments/{id}/status     | GET    | Get deployment status |

  Database integration:
  @app.on_event("startup")
  async def startup_event():
      init_db()  # Creates tables if they don't exist

  ---
  2. Celery App (backend/celery_app.py)

  Purpose: Task queue configuration

  Key settings:
  celery_app = Celery(
      "cloud_manager",
      broker="redis://localhost:6379/0",  # Where tasks are queued
      backend="redis://localhost:6379/0",  # Where results are stored
  )

  # Task routes (which queue for which task)
  task_routes = {
      "backend.tasks.deploy_infrastructure": {"queue": "deployments"},
      "backend.tasks.cleanup_deployment": {"queue": "maintenance"},
  }

  Why Redis?
  - Fast in-memory storage
  - Pub/Sub messaging
  - Atomic operations
  - TTL support for task results

  ---
  3. Celery Tasks (backend/tasks.py)

  Purpose: Background job execution

  Main task: deploy_infrastructure
  @celery_app.task(bind=True, base=DatabaseTask)
  def deploy_infrastructure(self, deployment_id, provider_type, ...):
      # 1. Update DB status to RUNNING
      # 2. Create provider instance
      # 3. Execute deployment
      # 4. Update DB with results
      # 5. Update Celery task state (for monitoring)

  DatabaseTask base class:
  class DatabaseTask(Task):
      _db = None

      @property
      def db(self):
          if self._db is None:
              self._db = SessionLocal()
          return self._db

      def after_return(self, *args, **kwargs):
          if self._db is not None:
              self._db.close()
  Purpose: Automatic DB session management per task

  ---
  4. Database Models (backend/database.py)

  Schema:

  Deployment Table

  CREATE TABLE deployments (
      deployment_id VARCHAR(50) PRIMARY KEY,
      provider_type VARCHAR(50) NOT NULL,
      cloud_provider VARCHAR(20) NOT NULL,
      template_name VARCHAR(200) NOT NULL,
      resource_group VARCHAR(200),
      status VARCHAR(20) NOT NULL,  -- pending, running, completed, failed
      created_at TIMESTAMP NOT NULL,
      started_at TIMESTAMP,
      completed_at TIMESTAMP,
      parameters JSONB,
      outputs JSONB,
      error_message TEXT,
      logs TEXT,
      celery_task_id VARCHAR(100)
  );

  CREATE INDEX idx_deployments_status ON deployments(status);
  CREATE INDEX idx_deployments_created ON deployments(created_at DESC);

  TerraformState Table (for future use)

  CREATE TABLE terraform_states (
      deployment_id VARCHAR(50) PRIMARY KEY,
      backend_type VARCHAR(20) NOT NULL,  -- s3, azurerm, gcs
      backend_config JSONB NOT NULL,
      state_version VARCHAR(20),
      last_modified TIMESTAMP,
      workspace VARCHAR(100)
  );

  Connection:
  DATABASE_URL = "postgresql://apiuser:password@postgres:5432/multicloud"
  engine = create_engine(DATABASE_URL)
  SessionLocal = sessionmaker(bind=engine)

  ---
  5. Provider Factory (backend/providers/factory.py)

  Purpose: Creates appropriate cloud provider instance

  Pattern: Factory + Strategy

  class ProviderFactory:
      _providers = {
          "azure": AzureNativeProvider,
          "terraform-aws": TerraformProvider,
          "terraform-gcp": TerraformProvider,
          "terraform-azure": TerraformProvider,
      }

      @staticmethod
      def create_provider(provider_type: str, **kwargs):
          if provider_type not in ProviderFactory._providers:
              raise ValueError(f"Unknown provider: {provider_type}")

          provider_class = ProviderFactory._providers[provider_type]

          # Special handling for Terraform
          if provider_type.startswith("terraform-"):
              cloud = provider_type.split("-")[1]  # aws, gcp, azure
              return provider_class(cloud_platform=cloud, **kwargs)

          return provider_class(**kwargs)

  ---
  6. Cloud Providers

  Base Provider (backend/providers/base.py)

  class CloudProvider(ABC):
      @abstractmethod
      async def deploy(self, template_path, resource_group_name, parameters):
          """Deploy infrastructure"""
          pass

      @abstractmethod
      async def list_resource_groups(self):
          """List resource groups"""
          pass

      @abstractmethod
      def get_provider_type(self) -> ProviderType:
          """Get provider type"""
          pass

  Azure Native Provider (backend/providers/azure_native.py)

  - Uses Azure SDK (azure-mgmt-resource)
  - Compiles Bicep → ARM JSON
  - Deploys via Azure Resource Manager
  - Supports 15 Bicep templates

  Key method:
  async def deploy(self, template_path, resource_group_name, parameters):
      # 1. Compile Bicep to ARM JSON
      arm_template = self.compile_bicep(template_path)

      # 2. Create resource group
      self.resource_client.resource_groups.create_or_update(
          resource_group_name,
          {"location": self.region}
      )

      # 3. Deploy ARM template
      deployment = self.resource_client.deployments.begin_create_or_update(
          resource_group_name,
          deployment_name,
          {
              "properties": {
                  "template": arm_template,
                  "parameters": parameters,
                  "mode": "Incremental"
              }
          }
      )

      # 4. Wait for completion (blocking!)
      result = deployment.result()

      return DeploymentResult(...)

  Terraform Provider (backend/providers/terraform_provider.py)

  - Uses subprocess to run terraform CLI
  - Supports AWS, GCP, Azure
  - Manages temporary workspace
  - Handles 7 Terraform templates (3 AWS + 3 GCP + 1 Azure)

  Key methods:
  def __init__(self, cloud_platform, region, subscription_id):
      self.cloud_platform = cloud_platform  # aws, gcp, azure
      self.working_dir = tempfile.mkdtemp()  # /tmp/terraform_xyz/
      self._check_terraform_installed()

  async def deploy(self, template_path, resource_group_name, parameters):
      # 1. Setup workspace
      self._setup_workspace(template_path, parameters)

      # 2. terraform init
      self._run_terraform_command(["init"])

      # 3. terraform plan
      self._run_terraform_command(["plan", "-out=tfplan"])

      # 4. terraform apply
      self._run_terraform_command(["apply", "-auto-approve", "tfplan"])

      # 5. Get outputs
      outputs = self._get_terraform_outputs()

      return DeploymentResult(...)

  def _run_terraform_command(self, command: List[str]):
      result = subprocess.run(
          ["terraform"] + command,
          cwd=self.working_dir,
          capture_output=True,
          text=True,
          timeout=3600  # 1 hour max
      )
      if result.returncode != 0:
          raise DeploymentError(result.stderr)

  ---
  7. Template Manager (backend/template_manager.py)

  Purpose: Discover and manage infrastructure templates

  Template discovery:
  def __init__(self, templates_root: str):
      self.templates_root = Path(templates_root)
      self._templates_cache = {
          "bicep": [],
          "terraform-aws": [],
          "terraform-gcp": [],
          "terraform-azure": []
      }
      self._scan_templates()

  def _scan_templates(self):
      # Scan for Bicep templates (*.bicep)
      for bicep_file in self.templates_root.glob("*.bicep"):
          metadata = self._extract_bicep_metadata(bicep_file)
          self._templates_cache["bicep"].append(metadata)

      # Scan for Terraform templates
      tf_aws = self.templates_root / "terraform" / "aws"
      for tf_file in tf_aws.glob("*.tf"):
          metadata = self._extract_terraform_metadata(tf_file, "aws")
          self._templates_cache["terraform-aws"].append(metadata)

  Template structure:
  templates/
  ├── app-service.bicep                  # Azure App Service
  ├── storage-account.bicep              # Azure Storage
  ├── function-app.bicep                 # Azure Functions
  ├── ...                                # 15 Bicep templates
  └── terraform/
      ├── aws/
      │   ├── storage-bucket.tf          # S3 Bucket
      │   ├── compute-instance.tf        # EC2 Instance
      │   └── lambda-function.tf         # Lambda Function
      ├── gcp/
      │   ├── storage-bucket.tf          # GCS Bucket
      │   ├── compute-instance.tf        # Compute Engine
      │   └── cloud-function.tf          # Cloud Functions
      └── azure/
          └── storage-account.tf         # Storage via Terraform

  ---
  🗄️ Database Schema {#database}

  Entity Relationship

  ┌─────────────────────────┐
  │      Deployment         │
  ├─────────────────────────┤
  │ PK deployment_id        │ 
  │    provider_type        │
  │    cloud_provider       │
  │    template_name        │
  │    resource_group       │
  │    status               │◄────┐
  │    created_at           │     │
  │    started_at           │     │ 1:1
  │    completed_at         │     │
  │    parameters (JSON)    │     │
  │    outputs (JSON)       │     │
  │    error_message        │     │
  │    logs                 │     │
  │    celery_task_id       │     │
  └─────────────────────────┘     │
                                   │
                                   │
  ┌─────────────────────────┐     │
  │   TerraformState        │     │
  ├─────────────────────────┤     │
  │ PK deployment_id        │─────┘
  │    backend_type         │
  │    backend_config(JSON) │
  │    state_version        │
  │    last_modified        │
  │    workspace            │
  └─────────────────────────┘

  Status Flow

  PENDING ──→ RUNNING ──→ COMPLETED
                    │
                    └──→ FAILED
                    │
                    └──→ CANCELLED

  ---
  🚀 Deployment Process (Full Detail) {#deployment}

  Phase 1: API Request Handling (100-200ms)

  1.1 Request arrives at FastAPI
  Client → Nginx/Load Balancer → FastAPI → Route: POST /deploy

  1.2 Pydantic validation
  class DeploymentRequest(BaseModel):
      template_name: str      # Required
      provider_type: str      # Must be valid provider
      subscription_id: str    # Cloud account ID
      resource_group: str     # Where to deploy
      location: str           # Region
      parameters: Dict[str, Any]  # Template params

  1.3 Template validation
  template_path = template_manager.get_template_path(
      "storage-bucket",
      "terraform-aws"
  )
  # Returns: /app/templates/terraform/aws/storage-bucket.tf

  1.4 Database record creation
  deployment = Deployment(
      deployment_id=generate_unique_id(),
      provider_type="terraform-aws",
      status="pending",
      parameters=request.parameters
  )
  db.add(deployment)
  db.commit()

  1.5 Task queuing
  task = deploy_task.delay(
      deployment_id=deployment.deployment_id,
      ...
  )
  # Task is now in Redis queue

  1.6 Response to client
  HTTP 202 Accepted
  {
    "deployment_id": "deploy-abc123",
    "status": "pending",
    "task_id": "celery-task-xyz"
  }

  ---
  Phase 2: Celery Task Execution (2-10 minutes)

  2.1 Worker picks up task
  [2025-11-09 12:00:00] Received task: deploy_infrastructure
  [2025-11-09 12:00:00] Task ID: celery-task-xyz

  2.2 Update status to RUNNING
  UPDATE deployments
  SET status = 'running', started_at = NOW()
  WHERE deployment_id = 'deploy-abc123';

  2.3 Provider initialization
  provider = ProviderFactory.create_provider(
      "terraform-aws",
      subscription_id="123456789012",
      region="us-east-1"
  )

  2.4 Terraform workspace setup
  mkdir /tmp/terraform_xyz/
  cp /app/templates/terraform/aws/storage-bucket.tf /tmp/terraform_xyz/main.tf

  # Create terraform.tfvars
  echo 'bucket_name = "my-bucket"' > /tmp/terraform_xyz/terraform.tfvars

  # Create providers.tf
  cat > /tmp/terraform_xyz/providers.tf <<EOF
  provider "aws" {
    region = "us-east-1"
  }
  EOF

  2.5 Terraform init (~30 seconds)
  $ terraform init
  Initializing provider plugins...
  - Finding hashicorp/aws versions...
  - Installing hashicorp/aws v5.31.0...
  Terraform has been successfully initialized!

  2.6 Terraform plan (~10 seconds)
  $ terraform plan -out=tfplan
  Terraform will perform the following actions:
    # aws_s3_bucket.main will be created
    + resource "aws_s3_bucket" "main" {
        + bucket = "my-bucket"
        + region = "us-east-1"
      }
  Plan: 1 to add, 0 to change, 0 to destroy.

  2.7 Terraform apply (~1-5 minutes)
  $ terraform apply -auto-approve tfplan
  aws_s3_bucket.main: Creating...
  aws_s3_bucket.main: Still creating... [10s elapsed]
  aws_s3_bucket.main: Creation complete after 2s [id=my-bucket]

  Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

  Outputs:
  bucket_name = "my-bucket"
  bucket_arn = "arn:aws:s3:::my-bucket"

  2.8 Extract outputs
  $ terraform output -json
  {
    "bucket_name": {"value": "my-bucket"},
    "bucket_arn": {"value": "arn:aws:s3:::my-bucket"}
  }

  2.9 Update database
  UPDATE deployments
  SET
    status = 'completed',
    completed_at = NOW(),
    outputs = '{"bucket_name": "my-bucket", "bucket_arn": "arn:aws:s3:::my-bucket"}'
  WHERE deployment_id = 'deploy-abc123';

  ---
  Phase 3: Status Monitoring

  Client polls for status:
  # Every 5 seconds
  GET /deployments/deploy-abc123/status

  # Response when running:
  {"status": "running", "duration_seconds": 45}

  # Response when complete:
  {"status": "completed", "outputs": {...}}

  ---
  🐳 Docker & Infrastructure {#docker}

  Docker Compose Stack

  services:
    api:          # FastAPI application
    celery-worker:# Background task processor
    postgres:     # Database
    redis:        # Message broker

  Network Flow

  External → Port 8000 → api container
                         ↓
  api → postgres:5432 (internal network)
  api → redis:6379 (internal network)
                         ↓
  celery-worker ← redis:6379 (gets tasks)
  celery-worker → postgres:5432 (updates DB)
  celery-worker → AWS/Azure/GCP APIs (deploys infrastructure)

  Volume Mounts

  ./logs → /app/logs (api & worker)
  ./templates → /app/templates (api & worker)
  redis-data → /data (redis)
  postgres-data → /var/lib/postgresql/data (postgres)

  ---
  📁 File Structure {#structure}

  project/
  │
  ├── backend/
  │   ├── api_rest.py              # FastAPI application (600 lines)
  │   ├── celery_app.py            # Celery configuration
  │   ├── tasks.py                 # Celery tasks (deploy, cleanup)
  │   ├── database.py              # SQLAlchemy models
  │   ├── template_manager.py      # Template discovery (300 lines)
  │   │
  │   └── providers/
  │       ├── __init__.py
  │       ├── base.py              # Abstract base class
  │       ├── factory.py           # Provider factory
  │       ├── azure_native.py      # Azure Bicep provider
  │       └── terraform_provider.py# Terraform provider
  │
  ├── templates/
  │   ├── *.bicep                  # 15 Azure templates
  │   └── terraform/
  │       ├── aws/*.tf             # 3 AWS templates
  │       ├── gcp/*.tf             # 3 GCP templates
  │       └── azure/*.tf           # 1 Azure template
  │
  ├── tests/
  │   ├── unit/                    # Unit tests
  │   ├── integration/             # API tests
  │   └── e2e/                     # End-to-end tests
  │
  ├── docs/                        # 9 documentation guides
  ├── examples/                    # API usage examples
  ├── scripts/                     # Utility scripts
  │
  ├── docker-compose.yml           # Full stack orchestration
  ├── Dockerfile                   # API container
  ├── requirements.txt             # Python dependencies
  ├── .env.example                 # Environment template
  └── README.md                    # Project documentation

  ---
  🔑 Key Design Decisions

  Why Celery instead of FastAPI BackgroundTasks?

  - ✅ Persistent queue (survives API restarts)
  - ✅ Distributed workers (horizontal scaling)
  - ✅ Task retry logic
  - ✅ Progress tracking
  - ✅ Task cancellation

  Why PostgreSQL instead of MongoDB?

  - ✅ ACID compliance (critical for deployments)
  - ✅ Strong consistency
  - ✅ Rich query capabilities (filtering, sorting)
  - ✅ JSON support (JSONB for parameters/outputs)

  Why Redis as broker?

  - ✅ In-memory speed
  - ✅ Atomic operations
  - ✅ TTL support
  - ✅ Simple setup

  Why Factory pattern for providers?

  - ✅ Easy to add new cloud providers
  - ✅ Unified interface
  - ✅ Runtime provider selection

  ---
  Αυτό ήταν το complete breakdown! Έχεις κάποιο συγκεκριμένο κομμάτι που θέλεις να εμβαθύνουμε περισσότερο;