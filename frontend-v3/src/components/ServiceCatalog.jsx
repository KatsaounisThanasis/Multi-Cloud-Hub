import { useState, useEffect } from 'react';
import { templateAPI } from '../api/client';
import { formatTemplateName as formatName, formatProviderName } from '../utils/formatters';
import { getTemplateIcon, getTemplateGradient } from '../utils/templateIcons';

// Template categories and icons
const CATEGORIES = {
  compute: {
    name: 'Compute',
    icon: '💻',
    description: 'Virtual machines, containers, and serverless compute',
    azure: ['virtual-machine', 'aks-cluster', 'container-instances', 'container-registry', 'vm-scale-set', 'function-app', 'web-app'],
    gcp: ['compute-instance', 'gke-cluster', 'cloud-run', 'cloud-function']
  },
  storage: {
    name: 'Storage & Databases',
    icon: '💾',
    description: 'Storage accounts, databases, and data warehouses',
    azure: ['storage-account', 'sql-database', 'cosmos-db', 'redis-cache'],
    gcp: ['storage-bucket', 'cloud-sql', 'bigquery']
  },
  networking: {
    name: 'Networking',
    icon: '🌐',
    description: 'Networks, load balancers, and CDN',
    azure: ['virtual-network', 'network-security-group', 'load-balancer', 'application-gateway', 'vpn-gateway', 'public-ip'],
    gcp: ['vpc-network', 'load-balancer', 'cloud-cdn', 'cloud-dns', 'cloud-armor']
  },
  messaging: {
    name: 'Messaging & Events',
    icon: '📨',
    description: 'Message queues and event streaming',
    azure: ['service-bus'],
    gcp: ['pub-sub']
  },
  management: {
    name: 'Management & Security',
    icon: '🔒',
    description: 'Security, monitoring, and management tools',
    azure: ['key-vault', 'log-analytics', 'api-management', 'data-factory'],
    gcp: []
  }
};

function ServiceCatalog({ onSelectTemplate }) {
  const [provider, setProvider] = useState('azure');
  const [templates, setTemplates] = useState([]);
  const [templateCounts, setTemplateCounts] = useState({ azure: 0, gcp: 0 });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Fetch template counts on mount
  useEffect(() => {
    fetchTemplateCounts();
  }, []);

  useEffect(() => {
    if (provider) {
      fetchTemplates();
    }
  }, [provider]);

  const fetchTemplateCounts = async () => {
    try {
      const [azureRes, gcpRes] = await Promise.all([
        templateAPI.getTemplates('azure'),
        templateAPI.getTemplates('gcp')
      ]);
      setTemplateCounts({
        azure: azureRes.data.success ? azureRes.data.data.templates.length : 0,
        gcp: gcpRes.data.success ? gcpRes.data.data.templates.length : 0
      });
    } catch (err) {
      console.error('Failed to fetch template counts:', err);
    }
  };

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await templateAPI.getTemplates(provider);
      if (response.data.success) {
        setTemplates(response.data.data.templates);
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const getTemplateCategory = (templateName) => {
    for (const [categoryKey, category] of Object.entries(CATEGORIES)) {
      const providerTemplates = provider === 'azure' ? category.azure : category.gcp;
      if (providerTemplates.includes(templateName)) {
        return categoryKey;
      }
    }
    return 'other';
  };

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.display_name.toLowerCase().includes(searchQuery.toLowerCase());

    if (selectedCategory === 'all') {
      return matchesSearch;
    }

    return matchesSearch && getTemplateCategory(template.name) === selectedCategory;
  });

  const groupedTemplates = {};
  filteredTemplates.forEach(template => {
    const category = getTemplateCategory(template.name);
    if (!groupedTemplates[category]) {
      groupedTemplates[category] = [];
    }
    groupedTemplates[category].push(template);
  });

  // Note: Using imported formatName (smart formatter with acronym handling)

  // Clean template description - remove separator lines
  const cleanDescription = (description) => {
    if (!description) return '';
    // Remove lines that are just separators (=, -, _, etc.)
    return description
      .replace(/^[=\-_]+$/gm, '')  // Remove lines with only separators
      .replace(/^\s*$/gm, '')       // Remove empty lines
      .trim();
  };

  const handleTemplateClick = (template) => {
    // Direct selection - no format selection needed (all Terraform)
    onSelectTemplate(template);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Service Catalog</h2>
        <p className="mt-2 text-sm text-gray-600">
          Browse and deploy cloud infrastructure templates
        </p>
      </div>

      {/* Provider Selector */}
      <div className="flex space-x-4">
        <button
          onClick={() => setProvider('azure')}
          className={`flex-1 py-3 px-4 rounded-lg border-2 transition-all ${
            provider === 'azure'
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <span className="text-2xl">☁️</span>
            <span className="font-semibold">Azure</span>
          </div>
          <div className="text-xs mt-1 opacity-75">
            {templateCounts.azure} templates
          </div>
        </button>
        <button
          onClick={() => setProvider('gcp')}
          className={`flex-1 py-3 px-4 rounded-lg border-2 transition-all ${
            provider === 'gcp'
              ? 'border-green-500 bg-green-50 text-green-700'
              : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
          }`}
        >
          <div className="flex items-center justify-center space-x-2">
            <span className="text-2xl">🌩️</span>
            <span className="font-semibold">Google Cloud</span>
          </div>
          <div className="text-xs mt-1 opacity-75">
            {templateCounts.gcp} templates
          </div>
        </button>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="all">All Categories</option>
          {Object.entries(CATEGORIES).map(([key, category]) => (
            <option key={key} value={key}>
              {category.icon} {category.name}
            </option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-blue-600"></div>
          <p className="mt-2 text-sm text-gray-600">Loading templates...</p>
        </div>
      )}

      {/* Templates Grid */}
      {!loading && (
        <div className="space-y-8">
          {Object.entries(groupedTemplates).map(([categoryKey, categoryTemplates]) => {
            const category = CATEGORIES[categoryKey];
            if (!category) return null;

            return (
              <div key={categoryKey}>
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <span className="text-2xl mr-2">{category.icon}</span>
                    {category.name}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1 ml-9">{category.description}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categoryTemplates.map((template) => {
                    const gradient = getTemplateGradient(template.name);
                    return (
                      <div
                        key={`${template.name}-${template.format}`}
                        onClick={() => handleTemplateClick(template)}
                        className="relative bg-white border border-gray-200 rounded-2xl p-5 hover:shadow-2xl hover:border-transparent hover:-translate-y-1 transition-all duration-300 cursor-pointer group overflow-hidden"
                      >
                        {/* Subtle gradient background on hover */}
                        <div className={`absolute inset-0 bg-gradient-to-br ${gradient.bg} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}></div>

                        <div className="relative flex items-start space-x-4">
                          <div className={`flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br ${gradient.from} ${gradient.to} flex items-center justify-center text-white shadow-lg ${gradient.shadow} group-hover:scale-110 transition-transform duration-300`}>
                            {getTemplateIcon(template.name)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-bold text-gray-900 group-hover:text-gray-800 transition-colors text-base leading-tight mb-1">
                              {formatName(template.name)}
                            </h4>
                            <div className="flex items-center space-x-2">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                provider === 'azure'
                                  ? 'bg-blue-100 text-blue-700'
                                  : 'bg-green-100 text-green-700'
                              }`}>
                                {provider === 'azure' ? 'Azure' : 'GCP'}
                              </span>
                            </div>
                          </div>
                          <div className={`text-transparent bg-gradient-to-r ${gradient.from} ${gradient.to} bg-clip-text opacity-0 group-hover:opacity-100 transition-opacity text-xl font-bold`}>
                            →
                          </div>
                        </div>
                        {template.description && cleanDescription(template.description) && (
                          <p className="relative mt-3 text-sm text-gray-600 line-clamp-2 leading-relaxed">
                            {cleanDescription(template.description)}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* No Results */}
      {!loading && filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600">No templates found</p>
        </div>
      )}

    </div>
  );
}

export default ServiceCatalog;
