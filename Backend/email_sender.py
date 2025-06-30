import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import dotenv_values

# Load environment variables
env = dotenv_values(".env")
EMAIL_ADDRESS = env.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = env.get("EMAIL_PASSWORD")

def send_otp_email(to_email, otp_code):
    subject = "Your OTP Code for Password Reset"
    body = f"""
    <html>
    <body>
        <h2>Jarvis AI - Password Reset</h2>
        <p>Your OTP code is: <strong>{otp_code}</strong></p>
        <p>This code will expire in 5 minutes.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"✅ OTP sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False  # 🚨 Important for flow control
