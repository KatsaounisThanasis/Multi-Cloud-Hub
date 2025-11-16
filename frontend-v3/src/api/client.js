import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const deploymentAPI = {
  // Get all deployments
  getAll: () => api.get('/deployments'),

  // Get deployment by ID
  getById: (id) => api.get(`/deployments/${id}`),

  // Create new deployment
  create: (data) => api.post('/deploy', data),

  // Delete deployment
  delete: (id) => api.delete(`/deployments/${id}`),

  // Get templates
  getTemplates: (providerType) =>
    api.get(`/templates/${providerType}`),
};

export default api;
