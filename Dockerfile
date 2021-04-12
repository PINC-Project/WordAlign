FROM python:3.8.8-buster

#WORKDIR /setup
#RUN wget http://download.sgjp.pl/morfeusz/20210307/Linux/18.04/64/morfeusz2_1.9.17-18.04_amd64.deb && \
#    wget http://download.sgjp.pl/morfeusz/20210307/Linux/18.04/64/libmorfeusz2_1.9.17-18.04_amd64.deb && \
#    wget http://download.sgjp.pl/morfeusz/20210307/Linux/18.04/morfeusz2-dictionary-sgjp_20210307_all.deb && \
#    dpkg -i *.deb && \
#    wget http://download.sgjp.pl/morfeusz/20210307/Linux/18.04/64/morfeusz2-1.9.17-cp38-cp38-linux_x86_64.whl && pip install morfeusz2-1.9.17-cp38-cp38-linux_x86_64.whl && \
#    rm /setup/*

ADD requirements.txt /tmp/

RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

#RUN wget -O pl_spacy_model_morfeusz-0.1.3.tar.gz "http://zil.ipipan.waw.pl/SpacyPL?action=AttachFile&do=get&target=pl_spacy_model_morfeusz-0.1.3.tar.gz" && \
#    pip install pl_spacy_model_morfeusz-0.1.3.tar.gz && rm /setup/*

WORKDIR /app

#ADD data ./data
ADD static ./static
ADD templates ./templates
ADD *.py ./

EXPOSE 80

CMD gunicorn --bind 0.0.0.0:80 --timeout=1800 --workers=4 --threads=4 --max-requests=30 --max-requests-jitter=20 --name=gunicorn  main