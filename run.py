from app.core.notifier import SMSSender

email  = 'voip@sgatechsolutions.com'
api_password = '7Df#kP2!qzX9'
message = "Thank you for calling SGA Tech Solutions. If you need immediate assistance, please call 431-478-1200 again and leave a voice message. If this is not urgent, please email us at support@sgatechsolutions.com and we will respond in one business day.\n\nOur business hours are Monday through Friday, 8 AM to 4:30 PM CST."
did = '4314780719'
call_duration = 15
timezone_diff = -1 # if there is not daylight time saving in the host we don't have to worry about this.
agent = SMSSender(email,api_password,did,call_duration,message,log=True,timezone_diff=timezone_diff)
agent.run()