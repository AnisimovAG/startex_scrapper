# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import asyncio
from timeit import default_timer as timer

from pyppeteer import launch
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import HtmlResponse
from scrapy_puppeteer import PuppeteerMiddleware
from pyppeteer.errors import NetworkError, TimeoutError as PyppeteerTimeoutError

from alibaba.models import AlibabaProduct
from .settings import MAX_ATTEMPTS, PAGE_LOAD_TIMEOUT


class AlibabaRetryMiddleware(RetryMiddleware):
    def process_exception(self, request, exception, spider):
        if isinstance(exception, (PyppeteerTimeoutError, NetworkError)) and request.attempt <= MAX_ATTEMPTS:
            request.attempt += 1
            spider.logger.warning(f'Timeout reached for {request.url}. Retry attempt {request.attempt}')
            return self._retry(request, exception, spider)


class AlibabaPuppeteerMiddleware(PuppeteerMiddleware):
    @classmethod
    async def _from_crawler(cls, crawler):
        """Start the browser"""

        middleware = cls()
        start_params = {
            'logLevel': crawler.settings.get('LOG_LEVEL'),
            'headless': True,
            # 'autoClose': False
        }
        if args := crawler.settings.get('BROWSER_ARGS'):
            start_params.update({'args': args})
        middleware.browser = await launch(start_params)
        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)

        return middleware

    @classmethod
    def from_crawler(cls, crawler):
        AlibabaProduct.objects.update(not_found=True)

        """Initialize the middleware"""

        loop = asyncio.get_event_loop()
        middleware = loop.run_until_complete(
            asyncio.ensure_future(cls._from_crawler(crawler))
        )

        return middleware

    async def _process_request(self, request, spider):
        """Handle the request using Puppeteer"""

        page = await self.browser.newPage()

        # Cookies
        # if isinstance(request.cookies, dict):
        #     await page.setCookie(*[
        #         {'name': k, 'value': v}
        #         for k, v in request.cookies.items()
        #     ])
        # else:
        #     await page.setCookie(request.cookies)

        # # The headers must be set using request interception
        # await page.setRequestInterception(True)
        #
        # @page.on('request')
        # async def _handle_headers(pu_request):
        #     overrides = {
        #         'headers': {
        #             k.decode(): ','.join(map(lambda v: v.decode(), v))
        #             for k, v in request.headers.items()
        #         }
        #     }
        #     await pu_request.continue_(overrides=overrides)

        start = timer()
        response = await page.goto(
            request.url,
            {
                'waitUntil': request.wait_until,
                'timeout': PAGE_LOAD_TIMEOUT
            },
        )
        spider.logger.info(f'Goto {request.url} took {timer() - start}')

        start = timer()
        if request.scroll_page:
            await page.evaluate("""{window.scrollBy(0, document.body.scrollHeight);}""")
        spider.logger.info(f'Scroll {request.url} took {timer() - start}')

        start = timer()
        if request.wait_for:
            if isinstance(request.wait_for, list):
                for wait_for in request.wait_for:
                    await page.waitFor(**wait_for)
            else:
                await page.waitFor(**request.wait_for)
        spider.logger.info(f'wait_for {request.url} took {timer() - start}')

        if request.screenshot:
            request.meta['screenshot'] = await page.screenshot()

        start = timer()
        content = await page.content()
        spider.logger.info(f'Get content {request.url} took {timer() - start}')
        body = str.encode(content)

        await asyncio.sleep(5)
        start = timer()
        await page.close()
        spider.logger.info(f'Close {request.url} took {timer() - start}')

        # Necessary to bypass the compression middleware (?)
        response.headers.pop('content-encoding', None)
        response.headers.pop('Content-Encoding', None)

        return HtmlResponse(
            page.url,
            status=response.status,
            headers=response.headers,
            body=body,
            encoding='utf-8',
            request=request
        )
