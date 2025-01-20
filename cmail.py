import smtplib
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('yasaswini099@gmail.com','gsvk guum lluh ucip')
    msg=EmailMessage()
    msg['FROM']='yasaswini099@gmail.com.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()