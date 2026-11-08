# Runs the Streamlit app in a container (also used by the Hugging Face Space).
#   docker build -t phishing-detector .
#   docker run --rm -p 8501:8501 phishing-detector      then open http://localhost:8501
FROM python:3.11-slim

# Run as a normal user, not root.
RUN useradd --create-home --uid 1000 app
WORKDIR /home/app/src

# CPU-only PyTorch keeps the image small; the model is tiny enough to run without a GPU.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY phishing_detector ./phishing_detector
COPY models/MANIFEST.sha256 ./models/MANIFEST.sha256
RUN chown -R app:app /home/app
USER app

ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    HF_HOME=/home/app/.cache/huggingface
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8501/_stcore/health')"
# The model (257 MB) is downloaded and checksum-verified on first start, then cached in models/.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
