#!/bin/bash
export CUDA_VISIBLE_DEVICES=0
uvicorn app.main:app --host 0.0.0.0 --port 8080
