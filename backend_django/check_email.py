"""
Run this script OUTSIDE Django to test raw SMTP connection:
    python test_email.py
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==============================
# CONFIG
# ==============================

EMAIL        = "support@zoikomobile.co.uk"
PASSWORD     = "NoxxMC26070%!LGM"
RECIPIENT    = "support@zoikomobile.co.uk"   # change to YOUR personal email to confirm receipt

# ==============================
# TEST 1: SSL on port 465
# ==============================

def test_ssl_465():
    print("\n🔄 TEST 1: SSL on port 465 (smtpout.secureserver.net)")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtpout.secureserver.net", 465, context=context, timeout=15) as server:
            server.login(EMAIL, PASSWORD)
            msg = MIMEMultipart()
            msg["From"]    = EMAIL
            msg["To"]      = RECIPIENT
            msg["Subject"] = "Test Email - SSL 465"
            msg.attach(MIMEText("This is a test email via SSL port 465.", "plain"))
            server.sendmail(EMAIL, RECIPIENT, msg.as_string())
            print("✅ TEST 1 PASSED — Email sent via SSL 465!")
            return True
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        return False


# ==============================
# TEST 2: TLS on port 587
# ==============================

def test_tls_587():
    print("\n🔄 TEST 2: TLS on port 587 (smtpout.secureserver.net)")
    try:
        with smtplib.SMTP("smtpout.secureserver.net", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL, PASSWORD)
            msg = MIMEMultipart()
            msg["From"]    = EMAIL
            msg["To"]      = RECIPIENT
            msg["Subject"] = "Test Email - TLS 587"
            msg.attach(MIMEText("This is a test email via TLS port 587.", "plain"))
            server.sendmail(EMAIL, RECIPIENT, msg.as_string())
            print("✅ TEST 2 PASSED — Email sent via TLS 587!")
            return True
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        return False


# ==============================
# TEST 3: relay-hosting.secureserver.net (alternate host)
# ==============================

def test_relay_host():
    print("\n🔄 TEST 3: relay-hosting.secureserver.net on port 25")
    try:
        with smtplib.SMTP("relay-hosting.secureserver.net", 25, timeout=15) as server:
            server.ehlo()
            server.login(EMAIL, PASSWORD)
            msg = MIMEMultipart()
            msg["From"]    = EMAIL
            msg["To"]      = RECIPIENT
            msg["Subject"] = "Test Email - relay port 25"
            msg.attach(MIMEText("This is a test email via relay-hosting port 25.", "plain"))
            server.sendmail(EMAIL, RECIPIENT, msg.as_string())
            print("✅ TEST 3 PASSED — Email sent via relay-hosting!")
            return True
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        return False


# ==============================
# RUN ALL TESTS
# ==============================

if __name__ == "__main__":
    print("=" * 50)
    print("  GoDaddy SMTP Email Debug Test")
    print("=" * 50)

    r1 = test_ssl_465()
    r2 = test_tls_587()
    r3 = test_relay_host()

    print("\n" + "=" * 50)
    print("RESULTS:")
    print(f"  SSL  465  (smtpout)  : {'✅ PASS' if r1 else '❌ FAIL'}")
    print(f"  TLS  587  (smtpout)  : {'✅ PASS' if r2 else '❌ FAIL'}")
    print(f"  Port 25   (relay)    : {'✅ PASS' if r3 else '❌ FAIL'}")
    print("=" * 50)

    if not any([r1, r2, r3]):
        print("""
⚠️  ALL TESTS FAILED. Possible reasons:
   1. Wrong password — verify in GoDaddy webmail login
   2. GoDaddy has blocked SMTP — enable it in cPanel/Workspace settings
   3. Your network/firewall is blocking outbound SMTP ports
   4. 2FA or app password required — check GoDaddy account settings
        """)
    else:
        print("\n✅ Use the passing config in your Django settings.py")