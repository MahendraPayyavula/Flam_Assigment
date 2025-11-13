#!/bin/bash
# Quick start script for QueueCTL

echo "========================================"
echo "QueueCTL - Quick Start Script"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python installation..."
python_version=$(python3 --version 2>&1)
if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed"
    exit 1
fi
echo "✓ Found: $python_version"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Install package
echo "Installing queuectl..."
pip install -e .
if [ $? -ne 0 ]; then
    echo "Error: Failed to install queuectl"
    exit 1
fi
echo "✓ QueueCTL installed"
echo ""

# Verify installation
echo "Verifying installation..."
queuectl --version
if [ $? -ne 0 ]; then
    echo "Error: Installation verification failed"
    exit 1
fi
echo ""

# Run tests
echo "Running tests..."
echo ""
python tests/test_integration.py
if [ $? -ne 0 ]; then
    echo "Warning: Some tests failed, but setup is complete"
    echo ""
fi

echo "========================================"
echo "✓ Setup Complete!"
echo "========================================"
echo ""
echo "Quick start:"
echo "  1. Enqueue a job:"
echo "     queuectl enqueue \"echo 'Hello World'\""
echo ""
echo "  2. Start workers:"
echo "     queuectl worker start --count 2"
echo ""
echo "  3. View status:"
echo "     queuectl status"
echo ""
echo "  4. List jobs:"
echo "     queuectl list --state pending"
echo ""
echo "For more information, run: queuectl --help"
echo ""
