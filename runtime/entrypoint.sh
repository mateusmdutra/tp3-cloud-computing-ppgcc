#!/bin/bash
base64 -d /app/functionzipfile64 > /app/functionzipfile.zip
unzip /app/functionzipfile.zip -d /app
ls -a function
python /app/main.py
