from datetime import datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from .settings import EMAIL_TO


def send_email(spider_name: str, updated_records: list, update_mode: bool) -> None:
    html = get_template('updated_records.html').render({
        'spider': spider_name,
        'end_date': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        'records': updated_records,
        'update_status': '' if update_mode else 'НЕ ',
    })
    message = EmailMultiAlternatives(
        subject=f'Парсер {spider_name} обнаружил обновление товаров',
        to=EMAIL_TO,
        from_email='scraper'
    )
    message.attach_alternative(html, 'text/html')
    message.send()
