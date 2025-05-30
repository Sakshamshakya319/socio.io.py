// Extension configuration
const config = {
  // Backend API URL (deployed on Render)
  apiUrl: 'https://socio-io-py.onrender.com', // No trailing slash
  
  // Version
  version: '1.0.0',
  
  // Default settings
  defaults: {
    enabled: true,
    filterText: true,
    filterImages: true,
    isConfigured: true // Set to true by default
  }
};

export default config;