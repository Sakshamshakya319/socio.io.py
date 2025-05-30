// Script to start both Node.js and Python servers
const { spawn } = require('child_process');
const path = require('path');
require('dotenv').config();

// Configuration
const PYTHON_PORT = process.env.PYTHON_PORT || 5000;
const NODE_PORT = process.env.PORT || 3000;

// Set environment variables for the Python server
process.env.PYTHON_PORT = PYTHON_PORT;

// Function to start the Python Flask server
function startPythonServer() {
  console.log('Starting Python Flask server...');
  
  // Determine the Python command based on the platform
  const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
  
  // Start the Python server
  const pythonProcess = spawn(pythonCommand, ['flask_server.py'], {
    cwd: __dirname,
    stdio: 'inherit',
    env: { ...process.env }
  });
  
  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python server:', err);
  });
  
  pythonProcess.on('close', (code) => {
    if (code !== 0) {
      console.log(`Python server process exited with code ${code}`);
      // Restart the Python server if it crashes
      setTimeout(startPythonServer, 5000);
    }
  });
  
  return pythonProcess;
}

// Function to start the Node.js server
function startNodeServer() {
  console.log('Starting Node.js server...');
  
  // Start the Node.js server
  const nodeProcess = spawn('node', ['server.js'], {
    cwd: __dirname,
    stdio: 'inherit',
    env: { 
      ...process.env,
      PYTHON_SERVER_URL: `http://localhost:${PYTHON_PORT}`
    }
  });
  
  nodeProcess.on('error', (err) => {
    console.error('Failed to start Node.js server:', err);
  });
  
  nodeProcess.on('close', (code) => {
    if (code !== 0) {
      console.log(`Node.js server process exited with code ${code}`);
      // Restart the Node.js server if it crashes
      setTimeout(startNodeServer, 5000);
    }
  });
  
  return nodeProcess;
}

// Start both servers
const pythonProcess = startPythonServer();
// Wait for Python server to start before starting Node.js server
setTimeout(() => {
  const nodeProcess = startNodeServer();
  
  // Handle process termination
  process.on('SIGINT', () => {
    console.log('Shutting down servers...');
    pythonProcess.kill();
    nodeProcess.kill();
    process.exit(0);
  });
}, 3000); // Wait 3 seconds for Python server to initialize

console.log(`Python server will be available at: http://localhost:${PYTHON_PORT}`);
console.log(`Node.js server will be available at: http://localhost:${NODE_PORT}`);