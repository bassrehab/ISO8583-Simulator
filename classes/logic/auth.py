'''
Handles Authorization Messages
'''

class Authorization(object):

    def __init__(self):
        self.res_mti = '0110'

    def response(self, code=''):
        # return code for DE39
        # In case of Authorization no failures.
        # @ return response_mti, response_code
        return self.res_mti, '00'
