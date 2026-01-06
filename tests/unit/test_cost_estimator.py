import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.cost_estimator import (
    CostEstimate,
    estimate_deployment_cost,
    estimate_azure_vm_cost_realtime,
    estimate_gcp_vm_cost_realtime,
    estimate_azure_storage_cost_realtime,
    estimate_gcp_storage_cost,
    estimate_azure_vm_cost_fallback
)

class TestCostEstimateClass:
    """Test the CostEstimate helper class"""
    
    def test_add_component(self):
        estimate = CostEstimate()
        estimate.add_component('VM', 50.0, 'month', 'Test VM')
        
        assert estimate.monthly_cost == 50.0
        assert len(estimate.breakdown) == 1
        assert estimate.breakdown[0]['component'] == 'VM'
        assert estimate.breakdown[0]['cost'] == 50.0

    def test_add_multiple_components(self):
        estimate = CostEstimate()
        estimate.add_component('VM', 50.0)
        estimate.add_component('Disk', 10.0)
        
        assert estimate.monthly_cost == 60.0
        assert len(estimate.breakdown) == 2

    def test_to_dict(self):
        estimate = CostEstimate()
        estimate.add_component('VM', 100.0)
        estimate.add_note('Test note')
        
        result = estimate.to_dict()
        assert result['total_monthly_cost'] == 100.0
        assert result['currency'] == 'USD'
        assert 'Test note' in result['notes']


@pytest.mark.asyncio
class TestCostEstimatorAzure:
    """Test Azure cost estimation logic"""

    @patch('backend.core.cost_estimator.get_azure_public_client')
    async def test_azure_vm_realtime_success(self, mock_get_client):
        # Setup Mock
        mock_client = AsyncMock()
        mock_client.get_vm_pricing.return_value = {
            'retail_price_per_month': 80.0,
            'product_name': 'Test VM Product'
        }
        mock_client.get_disk_pricing.return_value = {
            'price_per_month': 5.0
        }
        mock_get_client.return_value = mock_client

        # Execute
        params = {'vm_size': 'Standard_D2s_v3', 'location': 'eastus', 'disk_size_gb': 64}
        estimate = await estimate_azure_vm_cost_realtime(params)

        # Assert
        assert estimate.monthly_cost > 80.0  # VM + Disk
        assert any(x['component'] == 'Virtual Machine' for x in estimate.breakdown)
        assert any(x['component'] == 'OS Disk' for x in estimate.breakdown)
        # Check that we used the API value (80.0) not the hardcoded one
        vm_cost = next(x['cost'] for x in estimate.breakdown if x['component'] == 'Virtual Machine')
        assert vm_cost == 80.0

    @patch('backend.core.cost_estimator.get_azure_public_client')
    async def test_azure_vm_realtime_api_failure_fallback(self, mock_get_client):
        # Setup Mock to raise exception
        mock_get_client.side_effect = Exception("API Error")

        # Execute
        params = {'vm_size': 'Standard_B2s', 'location': 'eastus'}
        estimate = await estimate_azure_vm_cost_realtime(params)

        # Assert - should fallback to hardcoded values
        # Standard_B2s hardcoded cost is 30.37
        assert estimate.monthly_cost > 0
        vm_cost = next(x['cost'] for x in estimate.breakdown if x['component'] == 'Virtual Machine')
        assert vm_cost == 30.37
        assert "Using estimated pricing (fallback)" in estimate.notes

    @patch('backend.core.cost_estimator.get_azure_public_client')
    async def test_azure_storage_realtime_success(self, mock_get_client):
        # Setup Mock
        mock_client = AsyncMock()
        mock_client.get_storage_pricing.return_value = {
            'price_per_gb_month': 0.02,
            'product_name': 'Standard LRS'
        }
        mock_get_client.return_value = mock_client

        # Execute
        params = {'account_tier': 'Standard', 'account_replication_type': 'LRS', 'location': 'eastus'}
        estimate = await estimate_azure_storage_cost_realtime(params)

        # Assert
        # 100GB * 0.02 = 2.0 + 0.5 base = 2.5
        assert estimate.monthly_cost == 2.5
        assert "Real-time pricing" in str(estimate.notes)


@pytest.mark.asyncio
class TestCostEstimatorGCP:
    """Test GCP cost estimation logic"""

    @patch('backend.core.cost_estimator.get_gcp_client')
    async def test_gcp_vm_realtime_success(self, mock_get_client):
        # Setup Mock
        mock_client = AsyncMock()
        mock_client.get_compute_pricing.return_value = {
            'price_per_month': 45.0,
            'vcpu_count': 2,
            'memory_gb': 8,
            'notes': ['Test Note']
        }
        mock_client.get_disk_pricing.return_value = {
            'price_per_gb_month': 0.04
        }
        mock_get_client.return_value = mock_client

        # Execute
        params = {'machine_type': 'e2-medium', 'region': 'us-central1'}
        estimate = await estimate_gcp_vm_cost_realtime(params)

        # Assert
        assert estimate.monthly_cost > 45.0
        assert "Test Note" in estimate.notes

    def test_gcp_storage_static(self):
        # GCP Storage uses static pricing map in the code currently
        params = {'storage_class': 'NEARLINE'}
        estimate = estimate_gcp_storage_cost(params)
        
        # NEARLINE cost is 0.01 * 100GB = 1.0
        assert estimate.monthly_cost == 1.0
        assert estimate.breakdown[0]['component'] == 'Storage Cost'


@pytest.mark.asyncio
class TestDeploymentCostDispatcher:
    """Test the main estimate_deployment_cost function"""

    @patch('backend.core.cost_estimator.estimate_azure_vm_cost_realtime')
    async def test_dispatch_azure_vm(self, mock_vm_est):
        # Setup
        mock_res = CostEstimate()
        mock_res.add_component('VM', 100.0)
        mock_vm_est.return_value = mock_res

        # Execute
        result = await estimate_deployment_cost('azure-virtual-machine', 'azure', {})

        # Assert
        assert result['total_monthly_cost'] == 100.0
        mock_vm_est.assert_called_once()

    async def test_dispatch_unknown_template(self):
        result = await estimate_deployment_cost('unknown-template', 'aws', {})
        assert "No specific cost model" in str(result['notes'])
        assert result['total_monthly_cost'] == 25.0  # Generic estimate
