FROM python:3.11

RUN mkdir /script
WORKDIR /script
ADD . /script/
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["python", "/script/evn-kaifa-ma309.py", "--log=INFO"]