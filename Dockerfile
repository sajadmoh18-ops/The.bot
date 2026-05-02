FROM python:3.9-slim

# تنصيب LibreOffice والاعتمادات
RUN apt-get update && apt-get install -y libreoffice && apt-get clean

# نقل ملفات السيرفر
WORKDIR /app
COPY . /app

# تنصيب المكتبات
RUN pip install python-telegram-bot==22.7 openpyxl python-pptx Pillow fpdf2

# تشغيل البوت
CMD ["python", "main.py"]
