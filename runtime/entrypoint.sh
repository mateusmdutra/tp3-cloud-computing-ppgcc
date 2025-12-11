#!/bin/bash
base64 -d /app/functionzipfileb64 > /app/functionzipfile.zip
unzip /app/functionzipfile.zip -d /app
python -m /app/main.py
