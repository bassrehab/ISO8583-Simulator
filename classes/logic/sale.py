'''
Handles Sales Messages
'''

class Sale(object):

    def __init__(self):
        self.res_mti = '0210'
        self.response_code_map = [
            {
                'req': '00',
                'res': '00',
                'desc': 'Success/Approved'
            },
            {
                'req': '03',
                'res': '03',
                'desc': 'Invalid Merchant'
            },

            {
                'req': '12',
                'res': '12',
                'desc': 'Wrong Transaction Date/Time'
            },
            {
                'req': '14',
                'res': '14',
                'desc': 'Invalid Card'
            },
            {
                'req': '57',
                'res': '57',
                'desc': 'Refund Not Allowed'
            },
            {
                'req': '58',
                'res': '58',
                'desc': 'Invalid Transaction'
            },
            {
                'req': '94',
                'res': '94',
                'desc': 'Duplicate Transaction'
            },
            {
                'req': '95',
                'res': '9C',
                'desc': 'Not a registered Member'
            },
            {
                'req': '96',
                'res': '9D',
                'desc': 'No Merchant Program'
            },
        ]

    def response(self, expected_code, processing_code):

        if processing_code == 000000 or processing_code == 200000: # Normal Sales, Refund Sales
            # Normal Sales
            for d in self.response_code_map:
                if expected_code is d['req']:
                    return self.res_mti, d['res']
                else:
                    return self.res_mti, '00'
                    # Return Success for any other codes
        else:
            return self.res_mti, '99'



#------------------------------

if __name__ =='__main__':
    print('Not allowed')