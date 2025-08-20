import asyncio
from time import sleep

from seleniumbase import SB
import random
import string
import time
# from email_api import EmailApi
from service.email_api import TempMailClient


async def create_account_go_login():
    email_client = TempMailClient()
    with SB(uc=True, incognito=True, locale="en", test=True) as sb:
        page_url = "https://app.gologin.com/sign_up"
        email_address = await email_client.create_account()

        sb.uc_open_with_reconnect(page_url)

        sb.type('input[placeholder="Email address"]', email_address)
        sb.type('input[placeholder="Password"]', email_address)
        sb.type('input[placeholder="Confirm password"]', email_address)
        sb.wait_for_element('button[type="submit"]')
        sb.uc_click('button[type="submit"]')

        sb.uc_gui_click_captcha()

        sb.wait_for_text_not_visible("I already", timeout=15)

        sb.assert_text("Let’s customize GoLogin for your needs", "body")

        sb.click('span:contains("No, this is my first time")')
        sb.click('span:contains("Create new accounts")')

        sb.click('span:contains("No, I’ve never used proxies")')
        sb.click('span:contains("Outreach & Lead Generation")')
        sb.uc_open('https://app.gologin.com/personalArea/TokenApi')
        sb.click('span:contains("New Token")')
        sb.click('span:contains("Confirm")')
        confirm_link = await email_client.wait_confirm_link()
        sb.uc_open(confirm_link)
        sb.uc_open('https://app.gologin.com/personalArea/TokenApi')
        sb.click('span:contains("New Token")')

        sb.wait_for_element_present('span:contains("Reveal token")', timeout=20)

        sb.js_click('span:contains("Reveal token")')
        sb.wait_for_element('div.css-8ojdky-InputToken')
        api_token = sb.get_text('div.css-8ojdky-InputToken')
        await email_client.close()
        return email_address, api_token

