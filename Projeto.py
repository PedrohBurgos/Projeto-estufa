from machine import Pin, ADC, I2C, RTC, SoftI2C
import dht
import time
import network
from time import sleep
import urequests  # Importa apenas urequests para MicroPython
import ssd1306
import ntptime
import esp
esp.osdebug(None)
import gc
gc.collect()


# Configuração dos pinos
led_vermelho = Pin(15, Pin.OUT)
led_verde = Pin(2, Pin.OUT)
led_amarelo = Pin(4, Pin.OUT)
led_azul = Pin(17, Pin.OUT)
botaoZap = Pin(23, Pin.IN)
ldr_pin = ADC(Pin(34))
ldr_pin.atten(ADC.ATTN_0DB)

TIMEZONE_OFFSET = -3  # UTC-3 para São Paulo
rtc = RTC()
rtc.datetime((2024, 12, 2, 1, 14, 30, 0, 0))  # Ano, Mês, Dia, Dia da semana, Hora, Minuto, Segundo, Subsegundo

dht22 = dht.DHT22(Pin(16))
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
station = ''

# Função para ler o dht
def read_dht22():
    try:
        dht22.measure()
        return dht22.temperature(), dht22.humidity()
    except OSError:
        print('Erro ao ler o DHT22')
        return None, None

#funçao para controlar os leds
def controlar_leds(temperatura):
    if temperatura > 28:
        led_vermelho.on()
        led_verde.off()
        led_azul.off()
        led_amarelo.off()
    elif temperatura > 20 and temperatura <= 27:
        led_vermelho.off()
        led_verde.off()
        led_azul.off()
        led_amarelo.on()
    elif temperatura > 15 and temperatura <= 20:
        led_vermelho.off()
        led_amarelo.off()
        led_azul.off()
        led_verde.on()
    elif temperatura <= 15:
        led_vermelho.off()
        led_amarelo.off()
        led_verde.off()
        led_azul.on()
    else:
        led_vermelho.off()
        led_verde.off()
        led_amarelo.off()
        led_azul.off()


def ler_luminosidade():
    return ldr_pin.read()

# Sincronização do horário
def sincronizar_relogio():
    try:
        ntptime.host = 'pool.ntp.org'
        ntptime.settime()
        print("RTC sincronizado com sucesso")
    except Exception as e:
        print("Falha ao sincronizar o RTC:", e)

def obter_horario_local():
    tm = rtc.datetime()
    hora_local = (tm[4] + TIMEZONE_OFFSET) % 24
    if hora_local < 0:
        hora_local += 24
    data_hora = "{:02d}/{:02d}/{:04d} {:02d}:{:02d}:{:02d}".format(
        tm[2], tm[1], tm[0], hora_local, tm[5], tm[6])
    return data_hora

# Função para enviar a mensagem via WhatsApp quando o botão for pressionado
def enviar_mensagem_whatsapp(temperatura, umidade, luminosidade):
    global ultimo_envio
    if time.time() - ultimo_envio < 10:  # Limite de 10 segundos entre envios
        print("Aguarde antes de enviar outra mensagem.")
        exibir_mensagem_oled("Aguarde envio!")
        return
    ultimo_envio = time.time()

    message = f'Alerta:+Temperatura+({temperatura}°C)+Humidade+({umidade})+Luminosidade+({luminosidade})'
    url = f'https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={message}&apikey={api_key}'
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            print("Mensagem enviada com sucesso!")
            exibir_mensagem_oled("Mensagem enviada!")
        else:
            print(f"Erro ao enviar mensagem: {response.text}")
            exibir_mensagem_oled("Erro ao enviar!")
    except Exception as e:
        print(f"Erro na requisição: {e}")
        exibir_mensagem_oled("Erro de conexão!")

# Função para exibir mensagem no display OLED
def exibir_mensagem_oled(mensagem):
    try:
        oled.fill(0)
        oled.text(mensagem, 0, 30)  # Mensagem no centro 
        oled.show()
        sleep(3)  # Exibir mensagem por 3 segundos
    except Exception as e:
        print(f"Erro ao exibir mensagem no OLED: {e}")

def atualizar_display(temperatura, umidade, luminosidade, data_hora, ip):
    oled.fill(0)
    oled.text('Temp: {} C'.format(temperatura), 0, 0)
    oled.text('Umid: {} %'.format(umidade), 0, 10)
    oled.text('Lum: {}'.format(luminosidade), 0, 20)
    oled.text(data_hora, 0, 30)
    oled.text(f"IP: {ip}", 0, 40)
    oled.show()

def connect_wifi(ssid, password):
    global station

    station = network.WLAN(network.STA_IF)
    station.active(False)
    sleep(2)
    station.active(True)
    station.connect(ssid, password)
    while not station.isconnected():
        print('.', end='')
        sleep(0.2)
    print('\nConexão bem-sucedida!')
    print(station.ifconfig())
    print("IP: " , station.ifconfig()[0])

# Configuração Wi-Fi e CallMeBot
ssid = 'Wokwi-GUEST'
password = ''
phone_number = 'Numero de telefone' 
api_key = 'API do chatbot' 

# Conectar ao Wi-Fi
connect_wifi(ssid, password)

# Variáveis globais
ultimo_envio = 0

# Loop principal
while True:
    temperatura, umidade = read_dht22()
    luminosidade = ler_luminosidade()
    data_hora = obter_horario_local()
    ip = station.ifconfig()[0]

    if temperatura is not None:
        print('-------------------------------')
        print('Temperatura:', temperatura, '°C')
        print('Umidade:', umidade, '%')
        atualizar_display(temperatura, umidade, luminosidade, data_hora, ip)
        time.sleep(2)
    print('Luminosidade:', luminosidade)
    print('-------------------------------')
    time.sleep(2)

    controlar_leds(temperatura)
    
    # Verifica se o botão foi pressionado
    if botaoZap.value() == 1:  # Botão pressionado
        print("\n[Botão WhatsApp Pressionado]")
        enviar_mensagem_whatsapp(temperatura, umidade, luminosidade)

    sleep(0.1)  # Reduz o tempo para melhorar a resposta ao botão

    time.sleep(2)  # Delay entre as leituras
