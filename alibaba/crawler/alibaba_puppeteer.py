from scrapy_puppeteer import PuppeteerRequest


class AlibabaPuppeteerRequest(PuppeteerRequest):
    def __init__(self, url, callback=None, screenshot=False, wait_until=None, wait_for=None, scroll_page=False,
                 attempt=1, *args, **kwargs):
        self.scroll_page = scroll_page
        self.attempt = attempt
        super(AlibabaPuppeteerRequest, self).__init__(url, callback, screenshot, wait_until, wait_for,
                                                      *args, **kwargs)
