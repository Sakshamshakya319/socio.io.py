// Application routes and middleware
const express = require('express');
const router = express.Router();
const axios = require('axios');
const multer = require('multer');
const FormData = require('form-data');

// Configure multer for in-memory storage
const storage = multer.memoryStorage();
const upload = multer({ 
  storage: storage,
  limits: { fileSize: 5 * 1024 * 1024 } // 5MB limit
});

// Get Python server URL from environment or use default
const PYTHON_SERVER_URL = process.env.PYTHON_SERVER_URL || 'http://localhost:5000';

// Middleware to check if Vertex API is properly set up
router.use((req, res, next) => {
  if (!process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    return res.status(500).json({ 
      error: "Google Cloud credentials not configured" 
    });
  }
  next();
});

// Welcome route
router.get('/', (req, res) => {
  res.json({ 
    message: "Welcome to Socio.io Content Filter API",
    version: "1.0.0",
    endpoints: [
      "/filter/text - Filter text content",
      "/filter/image - Filter image content",
      "/health - Server health check"
    ]
  });
});

// Text content filtering endpoint - forwards to Python server
router.post('/filter/text', async (req, res) => {
  try {
    const { text } = req.body;
    
    if (!text) {
      return res.status(400).json({ error: "No text provided" });
    }
    
    // Forward the request to the Python server
    const response = await axios.post(`${PYTHON_SERVER_URL}/filter/text`, {
      text: text,
      action: req.body.action || 'filter'
    });
    
    res.json(response.data);
  } catch (error) {
    console.error('Text filtering error:', error.message);
    // Forward error from Python server if available
    if (error.response && error.response.data) {
      return res.status(error.response.status).json(error.response.data);
    }
    res.status(500).json({ error: error.message });
  }
});

// Image content filtering endpoint - forwards to Python server
router.post('/filter/image', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No image provided" });
    }
    
    // Create a FormData object to send the image
    const formData = new FormData();
    formData.append('image', req.file.buffer, {
      filename: req.file.originalname || 'image.jpg',
      contentType: req.file.mimetype
    });
    
    // Forward the request to the Python server
    const response = await axios.post(`${PYTHON_SERVER_URL}/filter/image`, formData, {
      headers: {
        ...formData.getHeaders()
      }
    });
    
    res.json(response.data);
  } catch (error) {
    console.error('Image filtering error:', error.message);
    // Forward error from Python server if available
    if (error.response && error.response.data) {
      return res.status(error.response.status).json(error.response.data);
    }
    res.status(500).json({ error: error.message });
  }
});

// Health check endpoint
router.get('/health', async (req, res) => {
  try {
    // Check Python server health
    const pythonHealth = await axios.get(`${PYTHON_SERVER_URL}/health`)
      .then(response => ({ 
        status: 'ok', 
        message: response.data.message 
      }))
      .catch(error => ({ 
        status: 'error', 
        message: error.message 
      }));
    
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      services: {
        nodeServer: {
          status: 'ok'
        },
        pythonServer: pythonHealth,
        imageFiltering: {
          available: !!process.env.GOOGLE_APPLICATION_CREDENTIALS,
          method: 'vertex'
        },
        textFiltering: {
          available: !!process.env.GOOGLE_APPLICATION_CREDENTIALS
        }
      }
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

module.exports = router;