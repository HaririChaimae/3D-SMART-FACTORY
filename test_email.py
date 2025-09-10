import os
from dotenv import load_dotenv
load_dotenv()
import smtplib
from email.mime.text import MIMEText

print('Testing email configuration...')
print(f'Email user: {os.environ.get("EMAIL_USER")}')
print(f'Password length: {len(os.environ.get("EMAIL_PASSWORD", ""))}')

try:
    print('Attempting to connect to Gmail SMTP...')
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    print('TLS connection established')

    print('Attempting login...')                                                                                                    
    server.login(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD'))
    print('SUCCESS: Login successful!')

    print('Sending test email...')
    msg = MIMEText('This is a test email from your recruitment system.')
    msg['Subject'] = 'Test Email - Recruitment System'
    msg['From'] = os.environ.get('EMAIL_USER')
    msg['To'] = os.environ.get('EMAIL_USER')

    server.sendmail(msg['From'], msg['To'], msg.as_string())
    print('SUCCESS: Email sent successfully!')

    server.quit()

except smtplib.SMTPAuthenticationError as e:
    print(f'AUTHENTICATION FAILED: {e}')
    print('\nTroubleshooting steps:')
    print('1. Check if your password is correct')
    print('2. If you have 2FA enabled, use an App Password instead:')
    print('   - Go to Google Account settings')
    print('   - Security > 2-Step Verification > App passwords')
    print('   - Generate a new app password for "Mail"')
    print('   - Use that 16-character password in .env')
    print('3. Enable "Less secure app access" in Gmail settings (not recommended)')

except smtplib.SMTPConnectError as e:
    print(f'CONNECTION FAILED: {e}')
    print('Check your internet connection')

except Exception as e:
    print(f'UNEXPECTED ERROR: {e}')
    print(f'Error type: {type(e).__name__}')

print('\nCurrent .env configuration:')
print(f'EMAIL_USER={os.environ.get("EMAIL_USER")}')
print(f'EMAIL_PASSWORD={"*" * len(os.environ.get("EMAIL_PASSWORD", ""))}')