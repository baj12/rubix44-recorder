#!/bin/bash
# Quick recording script

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate audio-recorder

# Run recorder (customize these parameters)
python rubix_recorder.py \
    playback_files/your_file.wav \
    --duration 3600 \
    --output session

# Deactivate environment
conda deactivate

