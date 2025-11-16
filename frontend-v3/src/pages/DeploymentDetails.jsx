import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { deploymentAPI } from '../api/client';
import Breadcrumbs from '../components/Breadcrumbs';

function DeploymentDetails() {
  const { id } = useParams();
  const [deployment, setDeployment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDeployment = async () => {
    try {
      const response = await deploymentAPI.getById(id);
      setDeployment(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch deployment');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployment();
  }, [id]);

  useEffect(() => {
    if (deployment && (deployment.status === 'pending' || deployment.status === 'running')) {
      const interval = setInterval(fetchDeployment, 3000);
      return () => clearInterval(interval);
    }
  }, [deployment?.status]);

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase();
    switch (statusLower) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
        <div className="mt-4">
          <Link
            to="/"
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!deployment) {
    return (
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <p className="text-sm text-gray-500">Deployment not found</p>
        </div>
        <div className="mt-4">
          <Link
            to="/"
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <Breadcrumbs />

      <div className="md:flex md:items-center md:justify-between mb-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-gray-900">
            Deployment Details
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            ID: {deployment.deployment_id}
          </p>
        </div>
        <div className="mt-4 md:mt-0">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${getStatusColor(
              deployment.status
            )}`}
          >
            {deployment.status}
          </span>
        </div>
      </div>

      <div className="space-y-6">
        {/* Deployment Information */}
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Deployment Information
            </h3>
          </div>
          <div className="border-t border-gray-200">
            <dl>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Template Name</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {deployment.template_name}
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Provider Type</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {deployment.provider_type}
                </dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Location</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {deployment.location || 'N/A'}
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Created At</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(deployment.created_at).toLocaleString()}
                </dd>
              </div>
              {deployment.updated_at && (
                <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">Updated At</dt>
                  <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                    {new Date(deployment.updated_at).toLocaleString()}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        {/* Error Messages */}
        {deployment.error_message && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-red-900">
                Error Message
              </h3>
            </div>
            <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
              <div className="bg-red-50 rounded-md p-4">
                <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                  {deployment.error_message}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Outputs */}
        {deployment.outputs && Object.keys(deployment.outputs).length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Outputs
              </h3>
            </div>
            <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
              <div className="bg-gray-50 rounded-md p-4">
                <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono overflow-x-auto">
                  {JSON.stringify(deployment.outputs, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Parameters */}
        {deployment.parameters && Object.keys(deployment.parameters).length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Parameters
              </h3>
            </div>
            <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
              <div className="bg-gray-50 rounded-md p-4">
                <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono overflow-x-auto">
                  {JSON.stringify(deployment.parameters, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Status Info for In-Progress Deployments */}
        {(deployment.status === 'pending' || deployment.status === 'running') && (
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-blue-400 animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  This deployment is currently {deployment.status}. The page will auto-refresh every 3 seconds.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DeploymentDetails;
