FROM debian:bullseye-slim

ENV PYTHON_VERSION 3.9.5
ENV HOME /root
ENV PYTHON_ROOT $HOME/local/python-$PYTHON_VERSION
ENV PATH $PYTHON_ROOT/bin:$PATH
ENV PYENV_ROOT $HOME/.pyenv

# タイムゾーン設定。一応設定 #
ENV TZ Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y wget \
                    build-essential \
                    libreadline-dev \
                    libncursesw5-dev \
                    libssl-dev \
                    libsqlite3-dev \
                    libgdbm-dev \
                    libbz2-dev \
                    liblzma-dev \
                    zlib1g-dev \
                    uuid-dev \
                    libffi-dev \
                    libdb-dev \
		    git 

RUN wget --no-check-certificate https://www.python.org/ftp/python/3.9.5/Python-3.9.5.tgz \
&& tar -xf Python-3.9.5.tgz \
&& cd Python-3.9.5 \
&& ./configure --enable-optimizations\
&& make \
&& make install

# 先達に倣い、Pythonのライブラリはrequirements.txtに入っている。 #

COPY . /iccd2025
WORKDIR /iccd2025

RUN pip3 install --no-cache-dir -r requirements.txt

# ロケール設定 #
# 自環境でBashのプロンプトが壊れた為入っている。問題があれば報告してほしい # 
RUN apt-get install -y locales
RUN echo "ja_JP UTF-8" > /etc/locale.gen
RUN locale-gen
