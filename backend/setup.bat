@echo off
echo Setting up Socio.io Bolt Backend for local development...

echo Installing Node.js dependencies...
call npm install

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! You can now run the application with:
echo npm run dev
echo.
echo Or start the services separately:
echo - Node.js server: npm start
echo - Python server: python flask_server.py

pause