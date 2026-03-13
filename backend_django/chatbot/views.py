import json
import logging
import re
import traceback
from datetime import datetime

from django.conf        import settings
from django.core.mail   import EmailMessage
from django.http        import JsonResponse
from django.shortcuts   import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Feedback

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  OpenAI API key
#  getattr() is used so the server starts cleanly even if
#  OPENAI_API_KEY is not yet in settings.py — add it there or
#  in your .env file:  OPENAI_API_KEY = "sk-..."
# ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", "")


# ═══════════════════════════════════════════════════════════════
#  ZOIKO KNOWLEDGE BASE
#  GPT uses this to answer any free-text questions from users
# ═══════════════════════════════════════════════════════════════
ZOIKO_KB = """
You are Zovie, the friendly AI assistant for Zoiko Mobile UK.
Website: https://zoikomobile.co.uk

ABOUT ZOIKO MOBILE:
- UK MVNO (Mobile Virtual Network Operator) offering SIM-only plans
- Uses a major UK network with excellent coverage
- Offers eSIM and physical SIM cards
- No long-term contracts on most plans
- Supports Wi-Fi Calling and VoLTE
- Free international calls on many plans (35+ countries)
- EU Roaming included on all plans

ZOIKO PLANS (Flagship — 24 month):
- Zoiko Standard 10GB:  £12.14/month | 500 Calls & Texts | Wi-Fi Calling & eSIM | EU Roaming: 5GB/500min/500Texts
- Zoiko Max 30GB:       £16.99/month | Unlimited Calls & Texts | Free International Calls | EU Roaming: 15GB/1000min
- Zoiko Elite 100GB:    £28.34/month | Unlimited Calls & Texts | Free International Calls | EU Roaming: 30GB/2000min
- Zoiko Unlimited Data: £29.50/month | Unlimited Calls & Texts | Free International Calls | EU Roaming: 40GB/Unlimited

STUDENT PLANS:
- Zoiko Student 5GB:  £6.99/month  | 500 Calls & Texts | Student Discount
- Zoiko Student 15GB: £9.99/month  | Unlimited Calls & Texts | Student Discount  (MOST POPULAR)
- Zoiko Student 30GB: £12.99/month | Unlimited Calls & Texts | Student Discount
More info: https://zoikomobile.co.uk/student-discount-programme/

ESSENTIAL PLANS (Public sector / Civil servants):
- Zoiko Essential 5GB:  £5.99/month  | 250 Calls & Texts | No Contract
- Zoiko Essential 10GB: £8.49/month  | 500 Calls & Texts | No Contract  (MOST POPULAR)
- Zoiko Essential 20GB: £11.99/month | Unlimited Calls & Texts | No Contract
More info: https://zoikomobile.co.uk/civilservants/

SOCIAL TARIFF PLANS (Low income / benefits customers):
- Zoiko Social 3GB:  £3.99/month | Unlimited Calls & Texts | Social Media Included
- Zoiko Social 10GB: £7.49/month | Unlimited Calls & Texts | Social Media Included  (MOST POPULAR)
More info: https://zoikomobile.co.uk/social-tariff-plans/

DATA ONLY PLANS:
- Zoiko Data 10GB:      £8.99/month  | Data Only SIM
- Zoiko Data 30GB:      £14.99/month | Data Only SIM  (MOST POPULAR)
- Zoiko Data Unlimited: £22.99/month | Data Only SIM
More info: https://zoikomobile.co.uk/data-only-plans/

30 DAY ROLLING PLANS (cancel anytime):
- Zoiko Plus 3GB:    £5.66/month  | Unlimited Calls & Texts
- Zoiko Max 30GB:    £16.99/month | Unlimited Calls & Texts | Free International Calls  (MOST POPULAR)
- Zoiko Elite 100GB: £28.34/month | Unlimited Calls & Texts | Free International Calls
More info: https://zoikomobile.co.uk/30-day-plan/

BUSINESS DEALS:
- Business Starter 20GB: £14.99/month | Unlimited Calls & Texts | Dedicated Account Manager | Priority Support
- Business Pro 50GB:     £24.99/month | Unlimited Calls & Texts | Dedicated Account Manager | 5 SIMs (MOST POPULAR)
- Business Unlimited:    £39.99/month | Unlimited Everything | 10 SIMs Included
More info: https://zoikomobile.co.uk/business-deals_sim-only-plans/

CHECKOUT URL FORMAT:
https://zoikomobile.co.uk/checkout/?add-to-cart=PRODUCT_ID

DEVICES:         https://zoikomobile.co.uk/devices/
ANIMALS & MUSIC: https://zoikomobile.co.uk/animals-and-music/
ABOUT US:        https://zoikomobile.co.uk/about-us/

SIM ACTIVATION:
- Physical SIM delivered in 2-3 working days
- eSIM activated instantly via QR code
- Port your number with PAC code (text PAC to 65075)
- Activation page: https://zoikomobile.co.uk/activate-your-sim/

TOP UP:
- Online portal: https://zoikomobile.co.uk/recharge/
- Auto top-up available via My Account

SWITCH & SAVE:
- Get PAC code by texting PAC to 65075
- Enter it when ordering on zoikomobile.co.uk
- Keep existing number, switch in up to 1 working day
- Page: https://zoikomobile.co.uk/switch-and-save/

INTERNATIONAL CALLS (free on eligible plans, 35+ countries):
- Countries include: India, Pakistan, Bangladesh, Nigeria, USA, Canada, Australia, all EU/EEA
- Full list: https://zoikomobile.co.uk/international-calling/

SUPPORT & CONTACT:
- Email:   support@zoikomobile.co.uk
- Contact: https://zoikomobile.co.uk/contact-us/
- Support: https://zoikomobile.co.uk/support/
- Response within 24 hours (priority customers: 2 hours)

RESPONSE RULES:
- Be friendly, warm, and concise
- Never invent prices or plan details not listed above
- Always end your reply with: [MENU_ITEMS: option1 | option2 | option3]
- Keep chip options short and relevant (max 4 items)
- Always include "🏠 Main Menu" as the last chip option
"""


# ═══════════════════════════════════════════════════════════════
#  HOME  —  renders the chatbot HTML page
# ═══════════════════════════════════════════════════════════════
def home(request):
    return render(request, "index.html")


# ═══════════════════════════════════════════════════════════════
#  CHAT  (POST /chat/)
#
#  Called only when the user types a free-text question.
#  All menu chip clicks (Zoiko Plans, Student Plans, etc.)
#  are handled entirely in the frontend JS — they never
#  reach this endpoint.
# ═══════════════════════════════════════════════════════════════
@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    try:
        body    = json.loads(request.body)
        message = body.get("message", "").strip()
        history = body.get("history", [])

        if not message:
            return JsonResponse({"error": "No message provided"}, status=400)

        # Check API key is configured
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set in settings.py")
            return JsonResponse({
                "reply":   "AI responses are not configured yet. Please contact us at support@zoikomobile.co.uk",
                "items":   ["Contact Us", "🏠 Main Menu"],
                "history": history,
            })

        # Import and create client here — avoids any module-level crash
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            logger.error("openai package is not installed. Run: pip install openai")
            return JsonResponse({
                "reply":   "Service temporarily unavailable. Please contact support@zoikomobile.co.uk",
                "items":   ["Contact Us", "🏠 Main Menu"],
                "history": history,
            })

        # Build GPT message list with conversation history
        messages = [{"role": "system", "content": ZOIKO_KB}]

        for turn in history[-10:]:
            if isinstance(turn, dict) and "role" in turn and "content" in turn:
                messages.append(turn)

        messages.append({"role": "user", "content": message})

        # Call GPT-4o
        try:
            response = client.chat.completions.create(
                model       = "gpt-4o",
                messages    = messages,
                max_tokens  = 400,
                temperature = 0.65,
            )
            raw = response.choices[0].message.content.strip()

        except Exception as gpt_err:
            logger.error(f"OpenAI API error: {gpt_err}")
            return JsonResponse({
                "reply":   "I'm having a little trouble right now. Please try again or contact us at support@zoikomobile.co.uk",
                "items":   ["🏠 Main Menu", "Contact Us"],
                "history": history,
            })

        # Parse [MENU_ITEMS: ...] tag out of the GPT reply
        items = []
        match = re.search(r'\[MENU_ITEMS:\s*(.+?)\]', raw, re.IGNORECASE)
        if match:
            items = [i.strip() for i in match.group(1).split("|") if i.strip()]
            raw   = re.sub(r'\[MENU_ITEMS:[^\]]+\]', '', raw).strip()

        if not items:
            items = ["🏠 Main Menu"]

        # Update and trim conversation history (keep last 20 messages)
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant", "content": raw})
        history = history[-20:]

        return JsonResponse({
            "reply":   raw,
            "items":   items,
            "history": history,
        })

    except Exception as e:
        logger.error(f"Chat endpoint error:\n{traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════
#  FEEDBACK  (POST /feedback/)
#
#  Called by the star-rating widget at the end of a chat.
#  Saves to the database and emails the support team.
# ═══════════════════════════════════════════════════════════════
@csrf_exempt
@require_http_methods(["POST"])
def feedback(request):
    try:
        data    = json.loads(request.body)
        rating  = data.get("rating",  0)
        name    = data.get("name",    "Anonymous")
        phone   = data.get("phone",   "")
        email   = data.get("email",   "")
        message = data.get("message", "")

        # ── 1. Save to database ───────────────────────────────
        try:
            Feedback.objects.create(
                rating  = rating,
                name    = name,
                phone   = phone,
                email   = email,
                message = message,
            )
        except Exception as db_err:
            # Non-fatal — log and carry on so the email still sends
            logger.warning(f"Feedback DB save failed: {db_err}")

        # ── 2. Email the support team ─────────────────────────
        stars      = "★" * int(rating) + "☆" * (5 - int(rating))
        email_body = f"""
New Chatbot Feedback / Support Request
=======================================

Name    : {name}
Email   : {email}
Phone   : {phone}
Rating  : {stars}  ({rating} / 5)

Message:
{message}

Received: {datetime.now().strftime('%d %b %Y at %H:%M')}

Reply directly to this email to contact the user.
"""
        try:
            mail = EmailMessage(
                subject    = f"[Zovie] New Feedback — {rating}★ from {name}",
                body       = email_body,
                from_email = "support@zoikomobile.co.uk",
                to         = ["support@zoikomobile.co.uk"],
                reply_to   = [email] if email else [],
            )
            mail.send(fail_silently=False)
            print(f"\n✅ Feedback email sent  |  {name}  |  {rating}★")

        except Exception as mail_err:
            # Log the real error without crashing the response
            print(f"\n❌ EMAIL SEND FAILED: {mail_err}")
            traceback.print_exc()

        # ── 3. Terminal log ───────────────────────────────────
        print("\n===== ZOVIE FEEDBACK =====")
        print(f"Name   : {name}")
        print(f"Email  : {email}")
        print(f"Phone  : {phone}")
        print(f"Rating : {stars} ({rating}/5)")
        print(f"Message: {message}")
        print("==========================\n")

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error(f"Feedback error:\n{traceback.format_exc()}")
        return JsonResponse({"status": "error", "detail": str(e)}, status=500)