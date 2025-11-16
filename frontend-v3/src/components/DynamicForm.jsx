import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AZURE_REGIONS = [
  'norwayeast',
  'swedencentral',
  'polandcentral',
  'francecentral',
  'spaincentral'
];

const GCP_REGIONS = [
  'us-central1',
  'us-east1',
  'us-west1',
  'europe-west1',
  'europe-west2',
  'asia-east1',
  'asia-southeast1'
];

function DynamicForm({ provider, template, onSubmit, onCancel }) {
  const [parameters, setParameters] = useState([]);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (template) {
      fetchTemplateParameters();
      initializeFormData();
    }
  }, [template]);

  const initializeFormData = () => {
    // Set default values based on provider
    const defaults = {};

    if (provider === 'azure') {
      defaults.subscription_id = '58a01866-f499-4bc5-92ab-dc83166f7792';
      defaults.location = AZURE_REGIONS[0];
      defaults.resource_group_name = `rg-${template.name}-${Date.now()}`;
    } else if (provider === 'gcp') {
      defaults.project_id = 'peppy-booth-478115-i0';
      defaults.region = 'us-central1';
    }

    setFormData(defaults);
  };

  const fetchTemplateParameters = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(
        `${API_BASE_URL}/templates/${provider}/${template.name}/parameters`
      );

      if (response.data.success) {
        const params = response.data.data.parameters;
        setParameters(params);

        // Set default values from parameters
        const defaults = { ...formData };
        params.forEach(param => {
          if (param.default !== undefined && param.default !== null) {
            defaults[param.name] = param.default;
          }
        });
        setFormData(defaults);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load template parameters');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (paramName, value) => {
    setFormData(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const renderInput = (param) => {
    const value = formData[param.name] || '';
    const inputClasses = "mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm";

    // Special handling for known fields
    if (param.name === 'location' && provider === 'azure') {
      return (
        <select
          id={param.name}
          value={value}
          onChange={(e) => handleChange(param.name, e.target.value)}
          required={param.required}
          className={inputClasses}
        >
          {AZURE_REGIONS.map(region => (
            <option key={region} value={region}>{region}</option>
          ))}
        </select>
      );
    }

    if (param.name === 'region' && provider === 'gcp') {
      return (
        <select
          id={param.name}
          value={value}
          onChange={(e) => handleChange(param.name, e.target.value)}
          required={param.required}
          className={inputClasses}
        >
          {GCP_REGIONS.map(region => (
            <option key={region} value={region}>{region}</option>
          ))}
        </select>
      );
    }

    // Type-based rendering
    switch (param.type) {
      case 'bool':
      case 'boolean':
        return (
          <div className="flex items-center mt-1">
            <input
              type="checkbox"
              id={param.name}
              checked={value === true || value === 'true'}
              onChange={(e) => handleChange(param.name, e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor={param.name} className="ml-2 text-sm text-gray-700">
              {param.description}
            </label>
          </div>
        );

      case 'number':
      case 'int':
        return (
          <input
            type="number"
            id={param.name}
            value={value}
            onChange={(e) => handleChange(param.name, parseInt(e.target.value) || 0)}
            required={param.required}
            className={inputClasses}
            placeholder={param.default?.toString() || ''}
          />
        );

      case 'array':
      case 'list':
        return (
          <textarea
            id={param.name}
            value={Array.isArray(value) ? value.join('\n') : value}
            onChange={(e) => handleChange(param.name, e.target.value.split('\n').filter(Boolean))}
            required={param.required}
            rows={3}
            className={inputClasses}
            placeholder="Enter one item per line"
          />
        );

      case 'object':
      case 'map':
        return (
          <textarea
            id={param.name}
            value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                handleChange(param.name, parsed);
              } catch {
                handleChange(param.name, e.target.value);
              }
            }}
            required={param.required}
            rows={4}
            className={`${inputClasses} font-mono text-xs`}
            placeholder="{}"
          />
        );

      case 'string':
      default:
        // Check if there's a validation pattern suggesting password/secret
        const isSecret = param.name.toLowerCase().includes('password') ||
                        param.name.toLowerCase().includes('secret') ||
                        param.name.toLowerCase().includes('key');

        return (
          <input
            type={isSecret ? 'password' : 'text'}
            id={param.name}
            value={value}
            onChange={(e) => handleChange(param.name, e.target.value)}
            required={param.required}
            className={inputClasses}
            placeholder={param.default || ''}
          />
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-blue-600"></div>
          <p className="mt-2 text-sm text-gray-600">Loading form...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  // Group parameters by category
  const coreParams = parameters.filter(p =>
    ['subscription_id', 'project_id', 'location', 'region', 'resource_group_name'].includes(p.name)
  );

  const requiredParams = parameters.filter(p =>
    p.required && !coreParams.some(cp => cp.name === p.name)
  );

  const optionalParams = parameters.filter(p =>
    !p.required && !coreParams.some(cp => cp.name === p.name)
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Core Configuration */}
      {coreParams.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Core Configuration</h3>
          <div className="space-y-4">
            {coreParams.map(param => (
              <div key={param.name}>
                <label htmlFor={param.name} className="block text-sm font-medium text-gray-700">
                  {param.name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                  {param.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {renderInput(param)}
                {param.description && param.type !== 'bool' && (
                  <p className="mt-1 text-sm text-gray-500">{param.description}</p>
                )}
                {param.validation_message && (
                  <p className="mt-1 text-xs text-gray-400">{param.validation_message}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Required Parameters */}
      {requiredParams.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Required Parameters</h3>
          <div className="space-y-4">
            {requiredParams.map(param => (
              <div key={param.name}>
                <label htmlFor={param.name} className="block text-sm font-medium text-gray-700">
                  {param.name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                {renderInput(param)}
                {param.description && param.type !== 'bool' && (
                  <p className="mt-1 text-sm text-gray-500">{param.description}</p>
                )}
                {param.validation_message && (
                  <p className="mt-1 text-xs text-gray-400">{param.validation_message}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Optional Parameters */}
      {optionalParams.length > 0 && (
        <details className="border border-gray-200 rounded-lg">
          <summary className="px-4 py-3 cursor-pointer hover:bg-gray-50 rounded-lg">
            <span className="text-sm font-medium text-gray-700">
              Optional Parameters ({optionalParams.length})
            </span>
          </summary>
          <div className="px-4 pb-4 space-y-4 mt-2">
            {optionalParams.map(param => (
              <div key={param.name}>
                <label htmlFor={param.name} className="block text-sm font-medium text-gray-700">
                  {param.name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </label>
                {renderInput(param)}
                {param.description && param.type !== 'bool' && (
                  <p className="mt-1 text-sm text-gray-500">{param.description}</p>
                )}
                {param.validation_message && (
                  <p className="mt-1 text-xs text-gray-400">{param.validation_message}</p>
                )}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Deploy
        </button>
      </div>
    </form>
  );
}

export default DynamicForm;
