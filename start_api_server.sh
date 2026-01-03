#!/bin/bash
# Start Rubix Recorder API Server on Linux/Mac

echo "Starting Rubix Recorder API Server..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: Conda not found. Please install Anaconda or Miniconda first."
    exit 1
fi

# Initialize conda for shell usage
eval "$(conda shell.bash hook)"

# Activate the environment
echo "Activating conda environment..."
conda activate rubix-recorder-api

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "Creating conda environment from environment.yml..."
    conda env create -f environment.yml
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create conda environment."
        exit 1
    fi
    conda activate rubix-recorder-api
fi

# Start the API server
echo "Starting API server..."
python api_server.py