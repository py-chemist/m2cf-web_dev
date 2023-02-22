FROM debian:10

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1

RUN apt-get update \
  && apt-get -y install netcat gcc python python-pip \
  python-rdkit python-indigo texlive-base texlive-fonts-extra texlive-fonts-recommended texlive-latex-base texlive-latex-extra texlive-latex-recommended texlive-pictures && apt-get clean

RUN pip install --upgrade pip
COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY . .
