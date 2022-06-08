FROM scottyhardy/docker-wine:latest

# installing python 3.7
ARG VIRTUAL_ENV=/opt/python3
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y make curl git unzip graphviz python3.7 python3-pip python3.7-dev python3.7-venv
RUN python3.7 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN which pip
RUN pip install --upgrade pip


RUN mkdir /work
COPY . /work
WORKDIR /work
RUN python --version
RUN pip install -r requirements.txt
EXPOSE 8888
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--notebook-dir=notebooks"]
