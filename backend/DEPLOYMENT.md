# Deploying to Render - Step by Step Guide

This guide will walk you through deploying the Socio.io Bolt backend to Render.

## Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com)
3. Your Google Cloud credentials (for Vertex AI)

## Step 1: Prepare Your Repository

1. Make sure your code is in a GitHub repository
2. Ensure all the necessary files are committed:
   - `flask_server.py`
   - `server.js`
   - `app.js`
   - `requirements.txt`
   - `package.json`
   - `Procfile`
   - `render.yaml` (optional, for Blueprint deployment)

## Step 2: Deploy the Python Service

1. Log in to your Render dashboard: https://dashboard.render.com
2. Click on the "New +" button in the top right corner
3. Select "Web Service" from the dropdown menu
4. Connect your GitHub repository if you haven't already
5. Select the repository containing your code
6. Configure the service:
   - **Name**: `socio-io-bolt-python` (or any name you prefer)
   - **Root Directory**: `backend` (if your code is in a subdirectory)
   - **Environment**: `Python 3`
   - **Region**: Choose the region closest to your users
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn flask_server:app`
   - **Plan**: Choose the Free plan for testing, or a paid plan for production

7. Add environment variables:
   - Click on "Advanced" to expand additional options
   - Click on "Add Environment Variable"
   - Add the following variables:
     - `PYTHON_PORT`: `10001`
     - `GOOGLE_APPLICATION_CREDENTIALS`: Paste your entire Google credentials JSON

8. Click "Create Web Service"
9. Wait for the deployment to complete (this may take a few minutes)
10. Note the URL of your Python service (e.g., `https://socio-io-bolt-python.onrender.com`)

## Step 3: Deploy the Node.js Service

1. Go back to the Render dashboard
2. Click on the "New +" button again
3. Select "Web Service"
4. Select the same repository
5. Configure the service:
   - **Name**: `socio-io-bolt-api` (or any name you prefer)
   - **Root Directory**: `backend` (same as before)
   - **Environment**: `Node`
   - **Region**: Choose the same region as your Python service
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
   - **Plan**: Choose the Free plan for testing, or a paid plan for production

6. Add environment variables:
   - Click on "Advanced" to expand additional options
   - Click on "Add Environment Variable"
   - Add the following variables:
     - `NODE_ENV`: `production`
     - `PORT`: `10000`
     - `PYTHON_PORT`: `10001`
     - `PYTHON_SERVER_URL`: The URL of your Python service from Step 2 (e.g., `https://socio-io-bolt-python.onrender.com`)
     - `GOOGLE_APPLICATION_CREDENTIALS`: Paste your entire Google credentials JSON

7. Click "Create Web Service"
8. Wait for the deployment to complete

## Step 4: Test Your Deployment

1. Test the Node.js API:
   - Open your browser and navigate to `https://socio-io-bolt-api.onrender.com/health`
   - You should see a JSON response with status "ok"

2. Test the Python service:
   - Navigate to `https://socio-io-bolt-python.onrender.com/health`
   - You should see a JSON response with status "ok"

## Troubleshooting

If you encounter any issues:

1. **Check the logs**: In the Render dashboard, click on your service and then click on "Logs" to see what's happening.

2. **Common issues**:
   - **Missing dependencies**: Make sure all required packages are in `requirements.txt` or `package.json`
   - **Environment variables**: Ensure all environment variables are set correctly
   - **Port configuration**: Render assigns a PORT environment variable, make sure your app uses it
   - **Google credentials**: Verify your Google Cloud credentials are valid and properly formatted

3. **Service communication**: If the Node.js service can't communicate with the Python service, check:
   - The Python service is running correctly
   - The `PYTHON_SERVER_URL` is set correctly in the Node.js service
   - There are no network restrictions between services

## Updating Your Deployment

When you push changes to your GitHub repository:

1. Render will automatically detect the changes
2. It will rebuild and redeploy your services
3. You can disable auto-deploy in the service settings if needed

## Additional Resources

- Render Documentation: https://render.com/docs
- Render Python Services: https://render.com/docs/python
- Render Node.js Services: https://render.com/docs/node