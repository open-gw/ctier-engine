FROM python:3.13-alpine
COPY echo.py /echo.py
EXPOSE 8080
CMD ["python", "-u", "/echo.py"]
