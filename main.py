import os
import sys
import time
import pytz
import asyncio
import requests
import traceback
import datetime
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, \
    ElementNotInteractableException, TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.chrome.service import Service
from argparse import ArgumentParser
from telegram.ext import ApplicationBuilder

SCT_FILE_NAME = "screenie.png"

TOKEN = "7466655704:AAHzDHvAeI3Sl84ZdvOzzwDI0343X5pzkKc"
# CHANNEL_ID = '-1002197378111'
CHANNEL_ID = '@tomacitas'
CHANNEL_LOG_ID = '-1002197378111'

CUSTOM_EXEC_PATH = True  # False when in path
EXEC_PATH = r'/home/michel/geckodriver-v0.34.0-linux64/geckodriver'
BIN_PATH = r'/home/michel/firefox/firefox'
# EXEC_PATH = r'/root/geckodriver'
# BIN_PATH = r'/root/firefox/firefox'

USE_SOCK_PROXY = False  # False to disable proxy usage
PROXY_SOCK_HOST = r'127.0.0.1'
PROXY_SOCK_PORT = 9050

USE_HTTP_PROXY = False  # False to disable proxy usage
PROXY_HTTP_HOST = r'127.0.0.1'
PROXY_HTTP_PORT = 3128

USE_SSL_PROXY = False  # False to disable proxy usage
PROXY_SSL_HOST = r'127.0.0.1'
PROXY_SSL_PORT = 8118

HEADLESS_MODE = True

ENV = '(Local) - '
# ENV = '(Server1) - '
# ENV = '(Server2) - '

tmp_vars = {}
driver = None
wait = None
bot = None
bot_proxy_url = None
tz_NY = pytz.timezone('America/New_York')
page_title = f"{ENV}Visados Nacionales - Visado de trabajo por cuenta ajena"


# Definir el enum ServiceType
class ServiceType(Enum):
    SERVICE_VISADO_AJENA = 1
    SERVICE_LEGALIZACION = 2
    SERVICE_MATRIMONIO = 3
    SERVICE_ALTA_CUALIFI = 4
    SERVICE_FAMILIAR_COM = 5
    SERVICE_ESTUDIO = 6
    SERVICE_SCHENGEN = 7

    def __str__(self):
        return self.value

    @staticmethod
    def from_integer(st):
        try:
            return ServiceType(st)
        except KeyError:
            raise ValueError()


# Diccionario con las URLs y selectores
service_dict = {
    ServiceType.SERVICE_VISADO_AJENA: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Visados&scs=Visados+Nacionales+-+Visado+de+trabajo+por+cuenta+ajena",
        "selector": "a:nth-child(1) > strong"
    },
    ServiceType.SERVICE_MATRIMONIO: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Familia&scs=Matrimonios",
        "selector": "p:nth-child(71) strong"
    },
    ServiceType.SERVICE_LEGALIZACION: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Legalización+o+Apostilla.+Compulsa+y+Registro&scs=Legalización+y+apostilla+de+la+Haya",
        "selector": "p > a > strong"
    },
    ServiceType.SERVICE_ALTA_CUALIFI: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Visados&scs=Visados+Nacionales+-+Visado+para+trabajador+altamente+cualificado+y+para"
               "+traslado+intraempresarial",
        "selector": "a:nth-child(1) > strong"
    },
    ServiceType.SERVICE_FAMILIAR_COM: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Visados&scs=Visados+Nacionales+-+Visado+de+reagrupaci%c3%b3n+familiar+en+r%c3%a9gimen"
               "+general",
        "selector": "a:nth-child(1) > strong"
    },
   ServiceType.SERVICE_ESTUDIO: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Visados&scs=Visados+Nacionales+-+Visado+de+estudios",
        "selector": "p:nth-child(49) strong"
    },
   ServiceType.SERVICE_SCHENGEN: {
        "url": "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scco=Cuba"
               "&scd=166&scca=Visados&scs=Visado+de+estancia+(visado+Schengen)",
        "selector": "p:nth-child(34) strong"

   }
}


def setup_browser():
    global driver
    global wait

    firefox_options = Options()
    firefox_options.binary_location = BIN_PATH

    if HEADLESS_MODE:
        firefox_options.add_argument("-headless")

    # Define Proxy
    if USE_SOCK_PROXY:
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference('network.proxy.socks', PROXY_SOCK_HOST)
        firefox_options.set_preference('network.proxy.socks_port', PROXY_SOCK_PORT)
        firefox_options.set_preference('network.proxy.socks_remote_dns', False)

    if USE_HTTP_PROXY:
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference('network.proxy.http', PROXY_HTTP_HOST)
        firefox_options.set_preference('network.proxy.http_port', PROXY_HTTP_PORT)
        firefox_options.set_preference('network.proxy.http_remote_dns', False)

    if USE_SSL_PROXY:
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference('network.proxy.ssl', PROXY_SSL_HOST)
        firefox_options.set_preference('network.proxy.ssl_port', PROXY_SSL_PORT)
        firefox_options.set_preference('network.proxy.ssl_remote_dns', False)

    if CUSTOM_EXEC_PATH:
        serviceDriver = Service(executable_path=EXEC_PATH)
        driver = webdriver.Firefox(options=firefox_options, service=serviceDriver)
    else:
        driver = webdriver.Firefox(options=firefox_options)

    driver.implicitly_wait(30)

    errors = [NoSuchElementException, ElementNotInteractableException, NoAlertPresentException,
              UnexpectedAlertPresentException]
    wait = WebDriverWait(driver, timeout=2, ignored_exceptions=errors)


def close_browser():
    if driver is not None:
        driver.quit()


def setup_bot():
    global bot
    global bot_proxy_url

    # Define Proxy
    if USE_SOCK_PROXY:
        bot_proxy_url = f"socks5://{PROXY_SOCK_HOST}:{PROXY_SOCK_PORT}"

    if USE_HTTP_PROXY:
        bot_proxy_url = f"http://{PROXY_HTTP_HOST}:{PROXY_HTTP_PORT}"

    if USE_SSL_PROXY:
        bot_proxy_url = f"https://{PROXY_SSL_HOST}:{PROXY_SSL_PORT}"

    # bot = telegram.Bot(token=TOKEN)
    bot_proxy_url = None # Disabled proxy for Telegram
    try:
        if bot_proxy_url is None:
            app = ApplicationBuilder().token(TOKEN).build()
        else:
            app = ApplicationBuilder().token(TOKEN).proxy(bot_proxy_url).build()
    except Exception as e:
        date_str = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
        print("\n_____________________________________________________________________________________________\n")
        print(f"Error at <ApplicationBuilder.setup_bot> on {date_str}\n\nException: {str(e)}")
        print("\n_____________________________________________________________________________________________\n")
        app = ApplicationBuilder().token(TOKEN).build()

    bot = app.bot

    # Remove photo
    if os.path.isfile(SCT_FILE_NAME):
        os.remove(SCT_FILE_NAME)


# Función que toma un valor del enum y retorna la URL y el selector
def get_service_info(service_type):
    if service_type in service_dict:
        return service_dict[service_type]
    else:
        raise ValueError("Invalid service type")


def wait_for_window(timeout=2):
    time.sleep(round(timeout / 1000))
    wh_now = driver.window_handles
    wh_then = tmp_vars["window_handles"]
    if len(wh_now) > len(wh_then):
        return set(wh_now).difference(set(wh_then)).pop()
    return False


async def check_cita(service_type):
    global page_title

    service_info = get_service_info(service_type)
    url = service_info.get('url')

    driver.get(url)
    driver.set_window_size(1229, 672)

    if is_element_present(By.CSS_SELECTOR, "p.section__header-title"):
        target_element = driver.find_element(By.CSS_SELECTOR, "p.section__header-title")
        if target_element:
            page_title = ENV + target_element.get_attribute("innerHTML")

    print(page_title)
    # Sending a welcome message
    send_welcome()
    # ----------------
    tmp_vars["window_handles"] = driver.window_handles
    driver.find_element(By.CSS_SELECTOR, service_info.get('selector')).click()
    tmp_vars["win6169"] = wait_for_window(2000)
    driver.switch_to.window(tmp_vars["win6169"])
    # -----------------
    # Close alert windows
    close_alert()
    # Resolve captcha
    if is_element_present(By.ID, "idCaptchaButton"):
        driver.find_element(By.ID, "idCaptchaButton").click()
    else:
        wait.until(EC.visibility_of_element_located((By.ID, "idCaptchaButton")))
        driver.find_element(By.ID, "idCaptchaButton").click()

    # Find slots
    time_slots = []
    if is_element_present(By.ID, "idTimeListTable"):
        time_slots = driver.find_elements(By.CSS_SELECTOR, "#idTimeListTable a")
        # Tomar una captura de pantalla
        try:
            target_element = driver.find_element(By.CLASS_NAME, "clsBktWidgetVersion5")
            target_element.screenshot(SCT_FILE_NAME)
        except Exception as e:
            date_str = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
            print("\n_____________________________________________________________________________________________\n")
            print(f"Error at <Selenium.screenshot> on {date_str}\n\nException: {str(e)}")
            print("\n_____________________________________________________________________________________________\n")
            driver.save_screenshot(SCT_FILE_NAME)

    items = []
    text = u'\U00002705'
    channel_id = CHANNEL_LOG_ID
    time_slot_len = len(time_slots)
    has_children = time_slot_len > 0

    try:
        if not has_children:
            items.append(u'\U0001F620' + f"   ***No hay horas disponibles***   """ + u'\U0001F620' + f"\n\n\n")
        else:
            channel_id = CHANNEL_ID
            items.append(u'\U0001F4C5' + f"   ***Horas disponibles:***   " + u'\U0001F4C5' + f"\n\n")
            # Crear la lista no ordenada
            for slot in time_slots:
                # Extraer la hora
                time_text = slot.find_element(By.CSS_SELECTOR, "span.clsDivDatetimeSlotTime").get_attribute("innerHTML")
                # Extraer los huecos libres
                free_slots_text = slot.find_element(By.CSS_SELECTOR, "div.clsDivDatetimeSlotFree").get_attribute(
                    "innerHTML")
                url = slot.get_attribute("href")

                items.append(f"""   [Hora: {str(time_text).strip()}, {str(free_slots_text).strip()}]({url})\n\n""")
    except Exception as e:
        channel_id = CHANNEL_ID
        bugs = u'\U00002705' + f"""   ***Revisa la captura de pantalla no tenemos los detalles pero parece haber 
        {time_slot_len} slots disponible***   """ + u'\U00002705' + f"""\n\n{str(e)}"""
        items.append(bugs)

    now = datetime.datetime.now(tz_NY)
    fecha = u'\U0001F4C6' + f"   ***Fecha:*** " + now.strftime("%d/%m/%Y") + f"\n\n"
    hora = u'\U0001F55C' + f"   ***Hora:*** " + now.strftime("%I:%M:%S %p")
    header_caption = u'\U0001F6A8' + f"""   ***{page_title}***  """ + u'\U0001F6A8' + f"\n\n"

    # Construir el mensaje Markdown con la imagen y el texto
    caption = f"""{header_caption}{fecha}{hora}\n\n{text.join(items)}\n\n"""

    # Sending a message
    if os.path.exists(SCT_FILE_NAME):
        if has_children:
            await send_message(
                chat_id=channel_id,
                text=caption,
                parse_mode='MARKDOWN'
            )
        else:
            header_caption = caption

        await send_photo(
            chat_id=channel_id,
            caption=header_caption,
            photo=open(SCT_FILE_NAME, 'rb'),
            parse_mode='MARKDOWN'
        )
    else:
        await send_message(
            chat_id=channel_id,
            text=caption,
            parse_mode='MARKDOWN'
        )


def close_alert():
    try:
        if is_alert_present():
            alert = driver.switch_to.alert
            alert.accept()
        else:
            alert = wait.until(lambda d: d.switch_to.alert)
            alert.accept()
    except Exception as e:
        print("Close alert: " + str(e))
        time.sleep(3)
        close_alert()


def is_element_present(how, what):
    try:
        driver.find_element(by=how, value=what)
    except NoSuchElementException as e:
        print(str(e))
        return False
    return True


def is_alert_present():
    try:
        driver.switch_to.alert
    except NoAlertPresentException:
        print("No hay alerta presente")
        return False
    except UnexpectedAlertPresentException:
        print("No ha aparecido la alerta de bienvenida")
        return False
    return True


def send_boostrap_message(text, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=markdown"

    return requests.get(url)


async def send_message(text, chat_id, parse_mode):
    tries = 0
    max_tries = 3
    retry_delay = 2
    while tries < max_tries:
        try:
            async with bot:
                await bot.send_message(text=text, chat_id=chat_id, parse_mode=parse_mode)
        except Exception as e:
            date_str = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
            print("\n_____________________________________________________________________________________________\n")
            print(f"Error at <Telegram.send_message> on {date_str}, Retry #{tries}\n\nException: {str(e)}")
            print("\n_____________________________________________________________________________________________\n")
            time.sleep(retry_delay)
            tries += 1
        else:
            break

    if tries >= max_tries:
        send_boostrap_message(
            text=text,
            chat_id=chat_id,
        )


async def send_photo(photo, caption, chat_id, parse_mode):
    tries = 0
    max_tries = 3
    retry_delay = 2
    while tries < max_tries:
        try:
            async with bot:
                await bot.send_photo(photo=photo, chat_id=chat_id, caption=caption, parse_mode=parse_mode)
        except Exception as e:
            date_str = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
            print("\n_____________________________________________________________________________________________\n")
            print(f"Error at <Telegram.send_photo> on {date_str}, Retry #{tries}\n\nException: {str(e)}")
            print("\n_____________________________________________________________________________________________\n")
            time.sleep(retry_delay)
            tries += 1
        else:
            break

    if tries >= max_tries:
        send_boostrap_message(
            text=caption,
            chat_id=chat_id,
        )


async def main(service_type):
    # Initialize Telegram bot
    setup_bot()
    # Initialize driver
    setup_browser()

    try:
        await check_cita(service_type)
    except Exception as e:
        # Get current system exception
        ex_type, ex_value, ex_traceback = sys.exc_info()

        # Extract unformatter stack traces as tuples
        trace_back = traceback.extract_tb(ex_traceback)

        # Format stacktrace
        stack_trace = list()

        for trace in trace_back:
            stack_trace.append(
                "File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))

        datetimeStr = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
        print("\n_____________________________________________________________________________________________\n")
        print("At: %s " % datetimeStr)
        print("Exception type : %s " % ex_type.__name__)
        print("Exception message : %s" % ex_value)
        print("Stack trace : %s" % stack_trace)
        print("\n_____________________________________________________________________________________________\n")

        send_boostrap_message(
            text=u'\U0001F41B' + f"""   ***{ENV}Error at ({datetimeStr})***   """ + u'\U0001F41B'
                 + f"""\n\n{str(ex_value)}\n\n""",
            chat_id=CHANNEL_LOG_ID
        )
    finally:
        # Close browser
        close_browser()


def send_welcome():
    datetimeStr = datetime.datetime.now(tz_NY).strftime("%d/%m/%Y, %I:%M:%S %p")
    #     wellcome = f"""
    # ***¡Bienvenido/a a nuestro servicio de citas!***
    #
    # Estamos emocionados de que hayas decidido unirte a nosotros en tu búsqueda de la cita. Nuestro equipo está aquí para apoyarte en cada paso del camino y ayudarte a encontrar a esa cita especial.
    #
    # Recuerda mantener una actitud positiva y abierta. _¡El amor puede llegar cuando menos lo esperas y la cita tambien!_
    # Disfruta de la experiencia y no dudes en contactarnos si tienes alguna pregunta o necesitas ayuda.
    #
    # _¡Que tengas mucha suerte en tu viaje hacia el amor y la cita!_
    # """

    send_boostrap_message(
        text=u'\U0001F6A9' + f"   ***{ENV}Inicio de la búsqueda de citas disponibles***   " + u'\U0001F6A9' + f"\n\n"
             + u'\U0001F514' + f"   ***Servicio Consular:***  {page_title}\n\n"""
             + u'\U0001F4C6' + f"   ***Fecha y Hora:***  {datetimeStr}"
             + f"""\n\n"""
             + u'\U0001F4CC' + f"""   [Citas-M@chete](https://t.me/toma_cita_bot)   """ + u'\U0001F4CC' + f"\n\n",
        chat_id=CHANNEL_LOG_ID
    )


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--serv', type=int, default=1)
    opts = parser.parse_args()

    asyncio.run(main(ServiceType.from_integer(opts.serv)))
