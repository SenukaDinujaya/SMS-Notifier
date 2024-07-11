from voipms.api.dids.sms import SMS

class ExtendedSMS(SMS):

    def __init__(self, base):
        super().__init__(base)
        
    def send_mms(self, params={}):
        self.method = "sendMMS"
        return self.base.request(self.method, params=params)
    
    def send_sms(self, params={}):
        self.method = "sendSMS"
        return self.base.request(self.method, params=params)