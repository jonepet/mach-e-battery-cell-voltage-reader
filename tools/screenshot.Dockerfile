FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

RUN pip install --no-cache-dir --break-system-packages playwright==1.48.0

COPY screenshot.py /tools/
CMD ["python3", "/tools/screenshot.py"]
