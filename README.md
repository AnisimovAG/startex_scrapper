# Startex web scraper
scraper models don't manage tables in database. This is the task of site models. It is necessary to synchronize the site and scraper models when they change

## docker usage
```shell
cp .env.sample to .env
```
add develop_settings or local_settings if needed (aka. db connection, find settings sample in ./scraper/settings.py)
```shell
touch ./env/develop_settings.py
```


```shell
chmod +x scraper/chromedriver.linux
docker compose up --build
```
once started
```shell
docker exec -it scraper bash
cd alibaba
scrapy crawl alibaba
```

## How to install
git clone https://gitlab.star-tex.ru/startex/site.git

cd site/scraper

### Install chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

apt-get install fonts-liberation xdg-utils

dpkg -i google-chrome-stable_current_amd64.deb
#### Check chromedriver and google-chrome major versions are compatible
scraper/chromedriver -v && google-chrome --version

### Install environment
pip install -r requirements.txt

## Run crawler
The crawler for each partner site is located in the directory of the same name

E.g. for Alibaba:

cd alibaba

scrapy crawl alibaba

## Logs
Look at the logs in the file /var/log/startex-scraper-{partner_name}.log



