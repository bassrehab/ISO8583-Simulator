'''
Class that delegates the logic depending upon the message type
'''
from auth import *
from sale import *
from reversal import *
from void import *
from test import *

class Delegate(object):
    def __init__(self, req_ISO_dict, mti='', processing_code='', transaction_amount=''):
        self.req_ISO_dict = req_ISO_dict
        self.req_MTI = mti
        self.req_processing_code = processing_code


        self.expected_response_code = transaction_amount[-2:]  # get the decimal value of the transaction amount DE4
        print('[INFO][REQ]Expected Response code (Decimal Value) of Transaction Amount:' + self.expected_response_code)
        # Get Response Code in Bit 39
        # self.get_response_bit()

    def get_response_bit(self):

        '''
            Function to get the Response DE 39 depending upon the
            MTI and Response Code of the request.

        '''



        if self.req_MTI == '0100':  # Authorization
            authObj = Authorization()
            return authObj.response(self.expected_response_code)


        elif self.req_MTI == '0200': # Sale

            '''
                :returns MTI, and response code
            '''

            if self.req_processing_code == '000000':  # Sales

                saleObj = Sale()
                return saleObj.response(self.expected_response_code, self.req_processing_code)

            elif self.req_processing_code == '020000':  # Void
                voidObj = Void()
                return voidObj.response(self.expected_response_code, self.req_processing_code)


            elif self.req_processing_code == '200000':  # Refund Sales
                saleObj = Sale()
                return saleObj.response(self.expected_response_code, self.req_processing_code)

            elif self.req_processing_code == '220000':  # Void Refund Sales
                voidObj = Void()
                return voidObj.response(self.expected_response_code, self.req_processing_code)


        elif self.req_MTI == '0400': # Reversal
            reversalObj = Reversal()
            # @Return res_MTI, res_processing_code, res_DE37
            return reversalObj.response(self.expected_response_code, self.req_processing_code)


        elif self.req_MTI == '0800': # Test Transaction
            testObj = TestTransaction()
            return testObj.response()


        else:
            # Default
            return None


# --------------------------------------

if __name__ == '__main__':
    print 'Not Allowed'