'''
Class that handles
1. Extraction Message length --> sends to validator
2. Extraction of TPDU --> sends to validator
3. unpacking (parsing) and packing of the ISO 8583 messages

4. Prepares the Message Length (for response)
5. Prepares the TPDU Header (for response)
6. packs the ISO 8583 message, received from logic/sale, logic/void, logic/reversal

Does not handle validation
'''

from classes.ISO8583.ISO8583 import *

class Message(object):
    def __init__(self, req_data):
        self.bigEndian = True


        # Request Initializations
        self.req_data = req_data  # data is the hexed (un-ASCII-ed) socket data. (len +TPDU + ISO Frame)
        self.req_TPDU = '6000010000'
        self.req_length = ''
        self.req_header = ''
        self.req_body = self.req_ISOPayload = ''

        # Response Initializations
        self.res_data = None
        self.res_TPDU = '6000010000'
        self.res_length = ''
        self.res_header = ''
        self.res_body = self.res_ISOPayload = ''



    # Request Message Extractors
    def REQ_extract_components(self):
        # self.req_data[0:4]
        self.get_header()
        self.get_body()

    def get_header(self):
        self.get_length()
        self.get_TPDU()
        # Extract the Header
        self.req_header = self.req_length + self.req_TPDU
        print('[INFO][REQ] Header (Len + TPDU):' + self.req_header)


    def get_body(self):
        self.get_ISOPayload()



    # Individual components
    def get_length(self): # Header
        self.req_length = self.req_data[0:4] # this is fixed and defined 2 byte representation

    def get_TPDU(self): # Header
        self.req_TPDU = self.req_data[4:14]


    def get_ISOPayload(self): #body
        self.req_body = self.req_ISOPayload = self.req_data[14:]




    def parse_ISOPayload(self):
        # call the iso8583 library
        # this should return a list with all the data elements, or could be a
        # ord(dict({DE4:1230012, DE7:SIWOQ}))
        iso = ISO8583()
        iso.setIsoContent(self.req_ISOPayload)

        print ('[INFO][REQ] ISO Bitmap = %s' % iso.getBitmap())

        MTI = iso.getMTI()
        print ('[INFO][REQ] MTI = %s' % MTI)
        print ('[INFO][REQ] Bits .... ')

        req_ISO_dict = iso.getBitsAndValues()

        # Add the MTI Value too in the Dict
        # req_ISO_dict.append({'bit': '0', 'type': 'MTI', 'value': iso.getBitmap()})

        '''
            Dictionary after parse that is being returned.

            [{'bit': '3', 'type': 'N', 'value': '000000'}, ----> Processing Code
            {'bit': '4', 'type': 'N', 'value': '000000644000'},
            {'bit': '11', 'type': 'N', 'value': '010640'},
            {'bit': '12', 'type': 'N', 'value': '184710'},
            {'bit': '13', 'type': 'N', 'value': '0109'},
            {'bit': '22', 'type': 'N', 'value': '001'},
            {'bit': '24', 'type': 'N', 'value': '000'},
            {'bit': '25', 'type': 'N', 'value': '01'},
            {'bit': '37', 'type': 'N', 'value': '003030303031'},
            {'bit': '38', 'type': 'N', 'value': '313031'},
            {'bit': '41', 'type': 'N', 'value': '30363430'},
            {'bit': '42', 'type': 'A', 'value': '363736333132353'},
            {'bit': '49', 'type': 'A', 'value': '031'},
            {'bit': '57', 'type': 'LLL', 'value': '3831373633303030303032323031383739393838076400643274f8808506397b95a0d69f2e688b9f9180374f2d39a257b61d7c6a6a831411f3af64bd21373f416383bb8b605bd488d185cffa6e1e215883fb40c70fcfde67'},
            {'bit': '0', 'type': 'MTI', 'value': '303805800cc08080'}] <<------ MTI Value

        '''

        processing_code = None
        transaction_amount = None

        for DE in req_ISO_dict:
            print ('[INFO][REQ](1) Bit %s | Type %s | Value = %s' % (DE['bit'], DE['type'], DE['value']))

            # Extract some key DE
            if DE['bit'] == '3':
                processing_code = DE['value']

            if DE['bit'] == '4':
                transaction_amount = DE['value']

        return MTI, processing_code, transaction_amount, req_ISO_dict



    # Response Message Composer
    def RES_compose_components(self, response_dict, response_mti, value_DE_39):

        # look through the key-pair val in res dict and compute in a string.
        self.set_body(response_dict, response_mti, value_DE_39)
        self.set_header()


        # Combine the response headers and body and return
        self.res_data = self.res_header + self.res_body
        return self.res_data

    def set_header(self):
        # First set TPDU , else will throw error with length calculation
        self.set_TPDU()
        self.set_length()
        self.res_header = str(self.res_length) + self.res_TPDU


    def set_body(self, response_dict, response_mti, value_DE_39):
        self.set_ISOPayload(response_dict, response_mti, value_DE_39)


    # Indivudal Components
    def set_length(self): # Header
        decimal_length = len(str(self.res_TPDU + self.res_body))
        print('[INFO][RES] Msg Length (in Decimal) :' + str(decimal_length))
        self.res_length = str(hex(decimal_length))[2:].rjust(4, '0')

        print('[INFO][RES] Msg Length (in Hex):' + self.res_length)

    def set_TPDU(self): # Header
        self.res_TPDU = '6000000001'

    def set_ISOPayload(self, response_dict, response_mti, value_DE_39): # Body
        # TODO: Handle for Authorization, it wont be same as Sale and Void.
        # Trying to set Bit 39 will throw an error.

        packiso = ISO8583() #Create a Separate Object

        try:
            packiso.setMTI(response_mti)
            for DE in response_dict:
                # Insert before DE 41 --> DE 39
                if DE['bit'] == '41':
                    packiso.setBit(39, value_DE_39)
                    print('[INFO][RES] Set DE Bit No | Value :' + '39' + ' | ' + value_DE_39)
                    packiso.setBit(int(DE['bit']), DE['value'])
                else:
                    packiso.setBit(int(DE['bit']), DE['value'])

                print('[INFO][RES] Set DE Bit No | Value :' + DE['bit'] + ' | ' + DE['value'])

        except ValueToLarge, e:
            print ('[ERR] Value too large :( %s' % e)
        except InvalidMTI, i:
            print ('[ERR] This MTI is wrong :( %s' % i)

        self.res_body = packiso.getRawIso()








