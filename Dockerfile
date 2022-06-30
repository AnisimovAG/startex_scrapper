FROM python:3.8

ENV DEBIAN_FRONTEND=noninteractive

# trying to use minimum RUN commands
RUN apt-get install
# installing google chrome with chinese fonts
RUN apt-get update && apt-get install -y apt-utils curl fonts-liberation xdg-utils postgresql wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf libxss1 \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

WORKDIR /opt/scrapper/
COPY . /opt/scrapper/

RUN pip3 install -r /opt/scrapper/requirements.txt


RUN chmod +x scrapper/chromedriver.linux \
    && scrapper/chromedriver.linux -v \
    && google-chrome --version

EXPOSE 80

# if you want to make container permanent
#ENTRYPOINT ["tail", "-f", "/dev/null"]
# or run a sample command
#CMD ["/bin/bash","start-alibaba.sh"]


