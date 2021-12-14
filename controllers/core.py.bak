'''
    Main Controller Class
'''
from classes.ISO8583.message import *
from classes.logic.delegate import *



class Controller(object):

    def __init__(self, msg_req):
        self.ISO_request = msg_req  # the full hex ISO8583 message
        self.ISO_response = None
        print('\n -------- REQUEST -------- \n')

    #Main Handler
    def handler_core(self):

        # delegates to all other handlers
        self.ISO_response = self.handler_transaction() # send the socket message

        self.handler_logging()
        self.handler_reporting()

        return self.ISO_response



    # Handler for Transactions.
    def handler_transaction(self):

        # parse the incoming message
        # call Message Class (extracts the Message Length + TPDU + ISO 8583 payload)
        msgObj = Message(self.ISO_request)
        msgObj.REQ_extract_components()  # Components are Length + TPDU + ISO Payload


        mti, \
        processing_code, \
        transaction_amount, \
        req_ISO_dict = msgObj.parse_ISOPayload()


        # Send to Logic Object
        logicObj = Delegate(req_ISO_dict, mti, processing_code, transaction_amount)

        # Get the appropriate response code
        # TODO: Do a try catch here, or cater for None being retured for default/error
        response_mti, response_DE39 = logicObj.get_response_bit()
        print('\n -------- RESPONSE -------- \n')
        print('[INFO][RES] DE 39:' + response_DE39)

        # Copy the fields from request onto response dict
        res_ISO_dict = req_ISO_dict


        # Delegate to Logic Handler
        return msgObj.RES_compose_components(res_ISO_dict, response_mti, response_DE39)



    def handler_logging(self):
       pass
    def handler_reporting(self):
        # generates report
        pass


#-------------------
if __name__ == "__main__":
    print('[DEBUG] Running in DEBUG Mode..')

    hex_string = '01fc60000100000200303805800cc080' \
                 '80000000000000644000010640184710' \
                 '01090010000100303030303131303130' \
                 '36343036373633313235303138313736' \
                 '33303030303032323031383739393838' \
                 '076400643274f8808506397b95a0d69f' \
                 '2e688b9f9180374f2d39a257b61d7c6a' \
                 '6a831411f3af64bd21373f416383bb8b' \
                 '605bd488d185cffa6e1e215883fb40c7' \
                 '0fcfde67000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '00000000000000000000000000000000' \
                 '0000000000000000000000000000'

    data = '00F7600001000002003238000101c080801000000000000012001207231505000012231505120711010200000000029876543230350009876543276412858F780AC38E1AC6D446FA103191326CE8316041DBB6F0F18B58EEF445FAD222C91EC8B6E9E343FEA1DCC843A6C899BD9DA3CC15EEA019B6C30A027243FB640C4'
    ctrlObj = Controller(hex_string)
    response = ctrlObj.handler_core()
    print ('[DEBUG] Response:' + response)