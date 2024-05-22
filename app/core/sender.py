from datetime import datetime, timezone
from voipms.api import Client,VoipException
from app.core.utils.extended_voipms import ExtendedSMS
# from app.core.extended_voipms import ExtendedSMS
from time import sleep,time
from collections import deque
import pandas as pd
import re


class SMSSender:
    def __init__(self,user_name,password,sender_did,call_duration:int,message,check_interval:int=10,delayed_minutes:int=3,log=False,log_length=100,timezone_diff:int=0) -> None:
        self.email = user_name
        self.api_pasword = password
        self.client = None
        self.message = message
        self.did  = sender_did
        self.history = deque([],maxlen=20)
        self.log_it = log
        self.call_duration = call_duration
        self.check_interval = check_interval
        self.delayed_minutes = delayed_minutes# Voip.ms sometimes takes time to register the call so I'm checking last 3 mins instead of the last minute
        self.log_history = deque([], maxlen=log_length)
        self.timezone_diff = timezone_diff

    def auth(self) -> None:
        #Authenticate the client with Voip.ms API
        self.client = Client(self.email, self.api_pasword)
    
    def json_to_dataframe(self,records):
        return pd.DataFrame(records)

    def get_history(self,params):
        #Get the misscall history
        try:
            return self.json_to_dataframe(self.client.call_detail_records.records.fetch(params=params)['cdr'])
        
        except VoipException as ve:
            #if the expection is no call history it will not log it.
            if not('There are no CDR entries for the filter' in str(ve)):
                self.log(f"VoipException occurred: {ve}")

        return pd.DataFrame([])

    def extract_value_between_tags(self,text):
        pattern = r'<(.*?)>'
        match = re.search(pattern, text)
        if match:
            return match.group(1) 
        else:
            return 'None'
    
    def filter_inbound (self,records:pd.DataFrame)->bool:
        #Filter to get only the inbound calls
        inbound_type = 'IN:CAN'
        return records[records['destination_type']==inbound_type].reset_index()

    def filter_missed (self,records:pd.DataFrame)->bool:
        #Filter to get calls less than 5 seconds long
        return records[records['seconds'].astype(int)<=self.call_duration].reset_index()

    def send_sms(self,sms_params,called_at):
        try:
            self.log(f"Sending SMS: {sms_params['dst']} called at:{called_at}")
            mms = ExtendedSMS(self.client)
            return mms.send_mms(params=sms_params)

        except:
            self.log('No Number')
            return None 
    
    def datetime_to_epoch(self,datetime_str):
        # Convert datetime to epoch time
        dt_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        dt_object_utc = dt_object.replace(tzinfo=timezone.utc)
        epoch_time = dt_object_utc.timestamp()
        
        return int(epoch_time)
        
    def within_last_min(self,last_record_time:int):
        last_min = 60*self.delayed_minutes # Voip.ms sometimes takes time to register the call so I'm checking last 3 mins instead of the last minute
        return int(time()) - last_record_time < last_min

    def log(self,log_item):
        if self.log_it:
            print(int(time()),"::|     ",log_item)
        self.log_history.append(log_item)


    def run_check(self,records:pd.DataFrame)->None:

        # Will return the list of caller ids for the last min
        if not(records.empty):
            records = self.filter_inbound(records)
            records = self.filter_missed(records)
            for index, record in records.iterrows():
                last_record_time = self.datetime_to_epoch(record['date'])
        
                if self.within_last_min(last_record_time):
                    #Extracting the caller ID
                    caller_id  = str(record['callerid'])
                    caller_id  = self.extract_value_between_tags(caller_id)
                    
                    if len(caller_id)>10: # Remove +1
                        caller_id = caller_id[-10:]

                    history_item = [caller_id,last_record_time]
                    
                    if not(history_item in self.history):
                        
                        sms_params={'did':self.did,'dst':caller_id,'message':self.message}
                        self.send_sms(sms_params,last_record_time)
                        
                        self.history.append(history_item)
                        # self.log(f"SMS Sent to {caller_id} called at {last_record_time}")

    def run(self):
        #Removed the while loop since it will go in the app.py
        today_date = datetime.utcfromtimestamp(time()).strftime('%Y-%m-%d')
        params = {'date_from': today_date,
                    'date_to': today_date,
                    'timezone':self.timezone_diff,
                    'answered':1,
                    'noanswer':1,
                    'busy':1,
                    'failed':1}
        
        self.auth()

        records = self.get_history(params)
        if not(records.empty):
            self.run_check(records)

        sleep(self.check_interval) 

#Example Use
# email  = 'voip@sgatechsolutions.com'
# api_password = '7Df#kP2!qzX9'
# message = "Thank you for calling SGA Tech Solutions. If you need immediate assistance, please call 431-478-1200 again and leave a voice message. If this is not urgent, please email us at support@sgatechsolutions.com and we will respond in one business day.\n\nOur business hours are Monday through Friday, 8 AM to 4:30 PM CST."
# did = '4314780719'
# call_duration = 15
# timezone_diff = -1 # if there is not daylight time saving in the host we don't have to worry about this.
# agent = SMSSender(email,api_password,did,call_duration,message,log=True,timezone_diff=timezone_diff)
# agent.run()