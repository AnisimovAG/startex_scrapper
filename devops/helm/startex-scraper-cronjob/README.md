
### docker image
script takes image hive.star-tex.ru/startex-scraper:latest
if you need to specify other release version, specify tag: in values.yaml

### other jobs

just add another job to the values.yaml with different command

ex:
```
  - name: startex-scraper-NEWMARKET-cronjob
    image:
      repository: hive.star-tex.ru/startex-scraper
      tag: latest
      imagePullPolicy: Always
    # running at 5:31 every day
    schedule: "31 5 * * *"
    command:
      - /bin/sh
      - -c
      - |
        export PYTHONPATH="$PYTHONPATH:/opt/scraper/"
        cd /opt/scraper/NEWMARKET
        scrapy crawl NEWMARKET
    failedJobsHistoryLimit: 1
    successfulJobsHistoryLimit: 3
    concurrencyPolicy: Forbid
    restartPolicy: Never

```
