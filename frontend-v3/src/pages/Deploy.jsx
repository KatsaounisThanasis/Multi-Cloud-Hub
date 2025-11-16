import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ServiceCatalog from '../components/ServiceCatalog';
import DynamicForm from '../components/DynamicForm';
import Breadcrumbs from '../components/Breadcrumbs';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function Deploy() {
  const navigate = useNavigate();
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState(null);

  const handleSelectTemplate = (template) => {
    setSelectedTemplate(template);
    setError(null);
  };

  const handleBackToCatalog = () => {
    setSelectedTemplate(null);
    setError(null);
  };

  const handleDeploy = async (formData) => {
    setDeploying(true);
    setError(null);

    try {
      // Determine provider type based on template
      const providerType = selectedTemplate.cloud_provider;

      const payload = {
        provider_type: providerType,
        template_name: selectedTemplate.name,
        parameters: formData
      };

      const response = await axios.post(`${API_BASE_URL}/deploy`, payload);

      if (response.data.success) {
        // Navigate to deployment details or dashboard
        const deploymentId = response.data.data.deployment_id;
        navigate(`/deployments/${deploymentId}`);
      }
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to create deployment'
      );
      setDeploying(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Breadcrumbs />

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {selectedTemplate ? 'Configure Deployment' : 'New Deployment'}
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                {selectedTemplate
                  ? `Deploy ${selectedTemplate.display_name} to ${selectedTemplate.cloud_provider.toUpperCase()}`
                  : 'Select a template from the service catalog below'}
              </p>
            </div>
            {selectedTemplate && (
              <button
                onClick={handleBackToCatalog}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                ← Back to Catalog
              </button>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 rounded-lg bg-red-50 p-4 border border-red-200">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Deployment Error</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {!selectedTemplate ? (
            // Service Catalog View
            <ServiceCatalog onSelectTemplate={handleSelectTemplate} />
          ) : (
            // Configuration Form View
            <div className="max-w-4xl mx-auto">
              {/* Template Info Card */}
              <div className="mb-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {selectedTemplate.display_name}
                    </h3>
                    <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                      <span className="inline-flex items-center">
                        <span className="mr-1">
                          {selectedTemplate.cloud_provider === 'azure' ? '☁️' : '🌩️'}
                        </span>
                        {selectedTemplate.cloud_provider.toUpperCase()}
                      </span>
                      <span className="inline-flex items-center">
                        <span className="mr-1">
                          {selectedTemplate.format === 'terraform' ? '🔧' : '💪'}
                        </span>
                        {selectedTemplate.format.toUpperCase()}
                      </span>
                    </div>
                    {selectedTemplate.description && (
                      <p className="mt-2 text-sm text-gray-700">
                        {selectedTemplate.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Form */}
              {deploying ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
                  <p className="mt-4 text-lg font-medium text-gray-900">Creating Deployment...</p>
                  <p className="mt-2 text-sm text-gray-600">This may take a few moments</p>
                </div>
              ) : (
                <DynamicForm
                  provider={selectedTemplate.cloud_provider}
                  template={selectedTemplate}
                  onSubmit={handleDeploy}
                  onCancel={handleBackToCatalog}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Deploy;
