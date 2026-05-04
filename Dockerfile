FROM python:3.11-slim

# Install all conversion tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    ffmpeg \
    imagemagick \
    ghostscript \
    wkhtmltopdf \
    poppler-utils \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy for PDF
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml 2>/dev/null || true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
