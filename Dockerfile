FROM python:3.8

ARG user
ARG uid

ENV DEBIAN_FRONTEND=noninteractive

# trying to use minimum RUN commands
#RUN apt-get install
# installing google chrome with chinese fonts
RUN apt-get update && apt-get install -y apt-utils curl fonts-liberation xdg-utils postgresql wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf libxss1 \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*



WORKDIR /opt/scrapper/
COPY ./ /opt/scrapper/


RUN mkdir /home/$user && useradd -G root -u $uid -d /home/$user $user && \
    chown -R $user:$user /home/$user && \
    chown -R $user:$user /opt/scrapper/ && \
    touch /var/log/startex-scrapper-alibaba.log && \
    chown -R $user:$user /var/log/startex-scrapper-alibaba.log



USER $user
ENV PATH="/home/$user/.local/bin:${PATH}"
ENV NO_SANDBOX="1"

RUN pip3 install --upgrade pip && pip3 install -r /opt/scrapper/requirements.txt
    && \ chmod +x scrapper/chromedriver.linux
    && \ scrapper/chromedriver.linux -v
    && \ google-chrome --version

EXPOSE 80