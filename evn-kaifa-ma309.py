import os
import serial
from gurux_dlms.GXByteBuffer import GXByteBuffer
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
from gurux_dlms.GXDLMSTranslatorMessage import GXDLMSTranslatorMessage
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Configuration
conf_evnKey = os.environ['evn_key']  # Key Provided by EVN
conf_comport = os.environ['comport']  # Used Comport (i.e. /dev/ttyUSB0)
conf_print_value = os.environ['printValue'].lower() == 'true'
conf_debug = os.environ['debug'].lower() == 'true'
conf_influxdb = os.environ['influxDB'].lower() == 'true'

# Influx DB Client Initialization
if conf_influxdb:
    # Config
    conf_influxdb_org = os.environ['influxDBOrg']
    conf_influxdb_token = os.environ['influxDBToken']
    conf_influxdb_bucket = os.environ['influxDBBucket']
    conf_influxdb_server = os.environ['influxDBServer']

    # Create Client
    client_influxdb = InfluxDBClient(url=conf_influxdb_server, token=conf_influxdb_token, org=conf_influxdb_org)

#
tr = GXDLMSTranslator()
tr.blockCipherKey = GXByteBuffer(conf_evnKey)
tr.comments = True
ser = serial.Serial(port=conf_comport,
                    baudrate=2400,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    )


def create_xml_from_serial_data(serialdata):
    """
    Tries to create xml from the serial data.
    Returns a String if everything works fine, otherwise None.

    :param serialdata:
    :return: String or None
    """
    try:
        msg = GXDLMSTranslatorMessage()
        msg.message = GXByteBuffer(serialdata)
        xml = ""
        pdu = GXByteBuffer()
        tr.completePdu = True
        while tr.findNextFrame(msg, pdu):
            pdu.clear()
            xml += tr.messageToXml(msg)

        return xml
    except:
        if conf_print_value:
            print('Unable to extract XML due to invalid data')
        return None


def extract_data_from_xml(xmldata):
    """
    Extracts all relevant data from the xml and returns it as a dictionary
    :param xmldata:
    :return:
    """
    soup = BeautifulSoup(xmldata, 'lxml')

    results_32 = soup.find_all('uint32')
    results_16 = soup.find_all('uint16')

    #
    wirkenergie_p = int(str(results_32)[16:16 + 8], 16)
    wirkenergie_n = int(str(results_32)[52:52 + 8], 16)

    momentanleistung_p = int(str(results_32)[88:88 + 8], 16)
    momentanleistung_n = int(str(results_32)[124:124 + 8], 16)

    spannung_l1 = int(str(results_16)[16:20], 16) / 10
    spannung_l2 = int(str(results_16)[48:52], 16) / 10
    spannung_l3 = int(str(results_16)[80:84], 16) / 10

    strom_l1 = int(str(results_16)[112:116], 16) / 100
    strom_l2 = int(str(results_16)[144:148], 16) / 100
    strom_l3 = int(str(results_16)[176:180], 16) / 100

    leistungsfaktor = int(str(results_16)[208:212], 16) / 1000

    return {
        "WirkenergieP": wirkenergie_p,
        "WirkenergieN": wirkenergie_n,
        "MomentanleistungP": momentanleistung_p,
        "MomentanleistungN": momentanleistung_n,
        "SpannungL1": spannung_l1,
        "SpannungL2": spannung_l2,
        "SpannungL3": spannung_l3,
        "StromL1": strom_l1,
        "StromL2": strom_l2,
        "StromL3": strom_l3,
        "Leistungsfaktor": leistungsfaktor,
    }


def print_data(extracted_data_kaifa):
    """
    Prints all data from the dictionary
    :param extracted_data_kaifa:
    :return:
    """
    print('---------- Extrahierte Daten ----------')
    print()
    print('Wirkenergie+: ' + str(extracted_data_kaifa["WirkenergieP"]) + ' Wh')
    print('Wirkenergie-: ' + str(extracted_data_kaifa["WirkenergieN"]) + ' Wh')
    print('Momentanleistung+: ' + str(extracted_data_kaifa["MomentanleistungP"]) + ' W')
    print('Momentanleistung-: ' + str(extracted_data_kaifa["MomentanleistungN"]) + ' W')
    print('Spannung L1: ' + str(extracted_data_kaifa["SpannungL1"]) + ' V')
    print('Spannung L2: ' + str(extracted_data_kaifa["SpannungL2"]) + ' V')
    print('Spannung L3: ' + str(extracted_data_kaifa["SpannungL3"]) + ' V')
    print('Strom L1: ' + str(extracted_data_kaifa["StromL1"]) + ' A')
    print('Strom L2: ' + str(extracted_data_kaifa["StromL2"]) + ' A')
    print('Strom L3: ' + str(extracted_data_kaifa["StromL3"]) + ' A')
    print('Leistungsfaktor: ' + str(extracted_data_kaifa["Leistungsfaktor"]))
    print('Momentanleistung: ' + str(
        extracted_data_kaifa["MomentanleistungP"] - extracted_data_kaifa["MomentanleistungN"]) + ' W')
    print()
    print('---------------------------------------')


def write_to_influxdb2(extracted_data_kaifa):
    """
    Writes all the extracted data to InfluxDBv2
    :param extracted_data_kaifa:
    :return:
    """
    write_api = client_influxdb.write_api()

    #
    write_api.write(conf_influxdb_bucket,
                    conf_influxdb_org,
                    [
                        {
                            "measurement": "strom",
                            "fields": {"wirkenergieP": extracted_data_kaifa["WirkenergieP"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"wirkenergieN": extracted_data_kaifa["WirkenergieN"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"momentanleistungP": extracted_data_kaifa["MomentanleistungP"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"momentanleistungN": extracted_data_kaifa["MomentanleistungN"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"spannungL1": extracted_data_kaifa["SpannungL1"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"spannungL2": extracted_data_kaifa["SpannungL2"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"spannungL3": extracted_data_kaifa["SpannungL3"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"stromL1": extracted_data_kaifa["StromL1"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"stromL2": extracted_data_kaifa["StromL2"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"stromL3": extracted_data_kaifa["StromL3"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {"leistungsfaktor": extracted_data_kaifa["Leistungsfaktor"]},
                        },
                        {
                            "measurement": "strom",
                            "fields": {
                                "momentanleistung": extracted_data_kaifa["MomentanleistungP"] - extracted_data_kaifa[
                                    "MomentanleistungN"]},
                        },
                    ]
                    )


# Main Loop
while 1:
    # Read data
    data = ser.read(size=282).hex()

    # Debug output
    if conf_debug:
        print(data)

    # XML Creation
    xml = create_xml_from_serial_data(data)
    if xml is None:
        continue

    # Data extraction
    extracted_data = extract_data_from_xml(xml)

    # Print data
    if conf_print_value:
        print_data(extracted_data)

    # InfluxDB
    if conf_influxdb:
        write_to_influxdb2(extracted_data)
