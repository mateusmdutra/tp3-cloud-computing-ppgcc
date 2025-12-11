#!/bin/bash
base64 -d /app/functionzipfile64 > /app/functionzipfile.zip
unzip /app/functionzipfile.zip -d /app
python -m /app/main.py
