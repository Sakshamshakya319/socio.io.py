# Socio.io Bolt Backend

This is the backend for the Socio.io Bolt content filtering system. It consists of two services:
1. A Node.js API server
2. A Python Flask server for content filtration

## Deployment to Render

### Prerequisites

1. Create a [Render](https://render.com) account if you don't have one
2. Have your Google Cloud credentials ready (for Vertex AI)

### Deployment Steps

#### Option 1: Using the Render Dashboard

1. **Deploy the Python Service First**:
   - Go to the Render Dashboard
   - Click "New" and select "Web Service"
   - Connect your GitHub repository
   - Select the repository and branch
   - Configure the service:
     - Name: `socio-io-bolt-python`
     - Root Directory: `backend`
     - Environment: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn flask_server:app`
   - Add the following environment variables:
     - `PYTHON_PORT`: `10001`
     - `GOOGLE_APPLICATION_CREDENTIALS`: (paste your Google credentials JSON)
   - Click "Create Web Service"

2. **Deploy the Node.js Service**:
   - Go to the Render Dashboard
   - Click "New" and select "Web Service"
   - Connect your GitHub repository
   - Select the repository and branch
   - Configure the service:
     - Name: `socio-io-bolt-api`
     - Root Directory: `backend`
     - Environment: `Node`
     - Build Command: `npm install`
     - Start Command: `npm start`
   - Add the following environment variables:
     - `NODE_ENV`: `production`
     - `PORT`: `10000`
     - `PYTHON_PORT`: `10001`
     - `PYTHON_SERVER_URL`: `https://socio-io-bolt-python.onrender.com`
     - `GOOGLE_APPLICATION_CREDENTIALS`: (paste your Google credentials JSON)
   - Click "Create Web Service"

#### Option 2: Using render.yaml (Blueprint)

1. In the Render Dashboard, go to "Blueprints"
2. Click "New Blueprint Instance"
3. Connect your GitHub repository
4. Select the repository and branch
5. Render will detect the `render.yaml` file and configure the services
6. Add your Google Cloud credentials as environment variables for both services
7. Click "Apply"

### Important Notes

1. Make sure to set up the Google Cloud credentials correctly
2. The Python service must be deployed first, as the Node.js service depends on it
3. Update the `PYTHON_SERVER_URL` in the Node.js service to point to your deployed Python service URL

## Testing the Deployment

After deployment, you can test the services:

1. Test the Node.js API: `https://socio-io-bolt-api.onrender.com/health`
2. Test the Python service: `https://socio-io-bolt-python.onrender.com/health`

## Local Development

To run the services locally:

1. Install dependencies:
   ```
   npm install
   pip install -r requirements.txt
   ```

2. Start both services:
   ```
   npm run dev
   ```

Or start them separately:
   ```
   npm start
   python flask_server.py
   ```