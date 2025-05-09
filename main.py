import os
import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Cursuri BNR
def get_bnr_api_rate(currency):
    response = requests.get('https://www.bnr.ro/nbrfxrates.xml')
    tree = ET.fromstring(response.content)
    ns = {'ns': 'http://www.bnr.ro/xsd'}
    for rate in tree.findall('.//ns:Rate', ns):
        if rate.attrib.get('currency') == currency:
            return rate.text
    return None

# Trimitere email
def send_email(subject, body, to_email):
    from_email = os.environ['EMAIL_SENDER']
    app_password = os.environ['EMAIL_PASS']

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(from_email, app_password)
        smtp.send_message(msg)

# Job principal
def job():
    currencies = ['EUR', 'USD', 'GBP']
    rates = {cur: get_bnr_api_rate(cur) for cur in currencies}

    today = datetime.now().strftime("%d.%m.%Y")
    body = f"Curs BNR - {today}\n\n"
    for cur, val in rates.items():
        body += f"{cur}: {val or 'Curs indisponibil'}\n"

    print(body)  # Poți verifica în consolă
    send_email(subject=f"Curs BNR {today}",
               body=body,
               to_email=os.environ['EMAIL_RECIPIENT'])

# Do not run job immediately if it's a cron trigger
if __name__ == "__main__":
    job()
