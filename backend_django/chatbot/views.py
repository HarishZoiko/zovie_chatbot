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
#  Set this in your settings.py or .env file:
#    OPENAI_API_KEY = "sk-..."
# ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", "")
# ⚠️  Set OPENAI_API_KEY in settings.py — never hardcode it here.


# ═══════════════════════════════════════════════════════════════
#  ZOIKO KNOWLEDGE BASE
#  GPT uses this to answer ALL free-text questions from users.
#  Every typed question that is NOT a menu button goes through
#  this system prompt, so answers will always be contextual
#  and different per question — never a repeated fallback.
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

IMPORTANT BEHAVIOUR RULES:
- Be friendly, warm, and concise.
- Give a SPECIFIC answer to each question — never give the same generic response.
- If the user asks about plans, give them the exact plan details from the knowledge base above.
- If the user asks about devices, activation, top-up, or any other topic, answer that topic specifically.
- Never invent prices or plan details not listed above.
- Always end your reply with: [MENU_ITEMS: option1 | option2 | option3]
- Keep chip options short and relevant (max 4 items).
- Always include "🏠 Main Menu" as the last chip option.
- Suggested chips should match what the user might want to do next based on their question.

EXAMPLES OF GOOD CHIP SUGGESTIONS:
- After answering about student plans: [MENU_ITEMS: Student Plans | 30 Day Plans | Contact Us | 🏠 Main Menu]
- After answering about international calls: [MENU_ITEMS: Zoiko Plans | International Calls | 🏠 Main Menu]
- After answering about activation: [MENU_ITEMS: Activate SIM | Top Up | Contact Us | 🏠 Main Menu]
- After answering about devices: [MENU_ITEMS: Devices | Zoiko Plans | 🏠 Main Menu]
"""


# ═══════════════════════════════════════════════════════════════
#  HOME  —  renders the chatbot HTML page
# ═══════════════════════════════════════════════════════════════
def home(request):
    return render(request, "index.html")


# ═══════════════════════════════════════════════════════════════
#  CHAT  (POST /chat/)
#
#  Called for ALL free-text user input that is not a menu button.
#  Every question gets a unique, context-aware GPT answer.
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

        # ── Check API key is configured ───────────────────────
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set in settings.py")
            # Return a helpful fallback that still gives useful info
            fallback = _fallback_response(message)
            return JsonResponse({
                "reply":   fallback["reply"],
                "items":   fallback["items"],
                "history": history,
            })

        # ── Import OpenAI client ──────────────────────────────
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            logger.error("openai package is not installed. Run: pip install openai")
            return JsonResponse({
                "reply":   "Service temporarily unavailable. Please contact support@zoikomobile.co.uk or call us directly.",
                "items":   ["Contact Us", "🏠 Main Menu"],
                "history": history,
            })

        # ── Build GPT message list with conversation history ──
        messages = [{"role": "system", "content": ZOIKO_KB}]

        for turn in history[-10:]:   # Keep last 10 turns for context
            if isinstance(turn, dict) and "role" in turn and "content" in turn:
                messages.append(turn)

        messages.append({"role": "user", "content": message})

        # ── Call GPT-4o ───────────────────────────────────────
        try:
            response = client.chat.completions.create(
                model       = "gpt-4o",
                messages    = messages,
                max_tokens  = 450,
                temperature = 0.65,
            )
            raw = response.choices[0].message.content.strip()

        except Exception as gpt_err:
            logger.error(f"OpenAI API error: {gpt_err}")
            fallback = _fallback_response(message)
            return JsonResponse({
                "reply":   fallback["reply"],
                "items":   fallback["items"],
                "history": history,
            })

        # ── Parse [MENU_ITEMS: ...] tag out of the GPT reply ──
        items = []
        match = re.search(r'\[MENU_ITEMS:\s*(.+?)\]', raw, re.IGNORECASE)
        if match:
            items = [i.strip() for i in match.group(1).split("|") if i.strip()]
            raw   = re.sub(r'\[MENU_ITEMS:[^\]]+\]', '', raw).strip()

        if not items:
            items = ["🏠 Main Menu"]

        # Ensure Main Menu is always available
        if not any("Main Menu" in (i if isinstance(i, str) else "") for i in items):
            items.append("🏠 Main Menu")

        # ── Update conversation history (keep last 20 messages) ──
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
#  FALLBACK  — keyword-based answers when OpenAI is unavailable
#  This ensures users always get a relevant, non-repeated answer
#  even without an API key configured.
# ═══════════════════════════════════════════════════════════════
def _fallback_response(message: str) -> dict:
    """
    Simple keyword matcher that returns a relevant response
    when the OpenAI API is not available.
    Each branch gives a distinct, helpful answer.
    """
    msg = message.lower()

    if any(w in msg for w in ["student", "uni", "university", "college", "discount"]):
        return {
            "reply": "🎓 Our Student Plans start from just £6.99/month!\n\n• 5GB — £6.99/mo | 500 Calls & Texts\n• 15GB — £9.99/mo | Unlimited Calls & Texts ⭐ Most Popular\n• 30GB — £12.99/mo | Unlimited Calls & Texts\n\nAll include EU Roaming, Wi-Fi Calling & eSIM. Student verification required.\n\nVisit: zoikomobile.co.uk/student-discount-programme/",
            "items": ["Student Plans", "Zoiko Plans", "Contact Us", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["business", "company", "corporate", "enterprise", "office", "team"]):
        return {
            "reply": "💼 Zoiko Business Plans — built for teams:\n\n• Starter 20GB — £14.99/mo | Account Manager + Priority Support\n• Pro 50GB — £24.99/mo | 5 SIMs included ⭐ Most Popular\n• Unlimited — £39.99/mo | 10 SIMs + everything unlimited\n\nAll plans include a dedicated account manager.\n\nVisit: zoikomobile.co.uk/business-deals_sim-only-plans/",
            "items": ["Business Deals", "Contact Us", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["data", "gb", "gigabyte", "internet", "data only"]):
        return {
            "reply": "📶 Our Data Only SIM plans:\n\n• 10GB — £8.99/mo\n• 30GB — £14.99/mo ⭐ Most Popular\n• Unlimited — £22.99/mo\n\nPerfect for tablets, dongles, or secondary devices. Includes EU Roaming.\n\nVisit: zoikomobile.co.uk/data-only-plans/",
            "items": ["Data Only Plans", "Zoiko Plans", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["international", "abroad", "overseas", "india", "pakistan", "nigeria", "call", "calling"]):
        return {
            "reply": "🌍 Zoiko offers FREE international calls to 35+ countries on eligible plans, including India, Pakistan, Bangladesh, Nigeria, USA, Canada, Australia and all EU countries.\n\nEligible plans: Zoiko Max 30GB (£16.99/mo), Elite 100GB (£28.34/mo) and Unlimited (£29.50/mo).\n\nFull country list: zoikomobile.co.uk/international-calling/",
            "items": ["Zoiko Plans", "International Calls", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["activate", "activation", "new sim", "start", "setup", "set up"]):
        return {
            "reply": "✅ Activating your Zoiko SIM is simple:\n\n1. Physical SIM — delivered in 2-3 working days\n2. eSIM — activated instantly via QR code\n3. Keep your number — text PAC to 65075, then enter it when ordering\n\nActivation page: zoikomobile.co.uk/activate-your-sim/",
            "items": ["Activate SIM", "Top Up", "Support", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["top up", "topup", "recharge", "credit", "add credit"]):
        return {
            "reply": "💳 Top up your Zoiko SIM easily online:\n\n• Visit zoikomobile.co.uk/recharge/\n• Auto top-up available via My Account\n• Instant activation after payment\n\nNeed help? Contact support@zoikomobile.co.uk",
            "items": ["Top Up", "Activate SIM", "Support", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["switch", "switching", "transfer", "port", "pac", "keep my number"]):
        return {
            "reply": "🔄 Switching to Zoiko is easy — keep your existing number!\n\n1. Text PAC to 65075 (free, from your current provider)\n2. You'll receive your PAC code by text\n3. Enter it when ordering at zoikomobile.co.uk\n4. Switch completes within 1 working day\n\nMore info: zoikomobile.co.uk/switch-and-save/",
            "items": ["Switch & Save", "Zoiko Plans", "Contact Us", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["price", "cost", "cheap", "afford", "how much", "cheapest"]):
        return {
            "reply": "💰 Zoiko plans start from just £3.99/month!\n\n• Social 3GB — £3.99/mo (benefits customers)\n• Essential 5GB — £5.99/mo (no contract)\n• Student 5GB — £6.99/mo (student discount)\n• Zoiko Plus 3GB — £5.66/mo (30-day rolling)\n\nAll plans include EU Roaming and Wi-Fi Calling.\n\nVisit zoikomobile.co.uk to see all plans.",
            "items": ["Zoiko Plans", "Student Plans", "30 Day Plans", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["esim", "e-sim", "qr", "digital sim"]):
        return {
            "reply": "📱 Zoiko supports eSIM on all plans!\n\n• Activate instantly via QR code — no physical SIM needed\n• Compatible with most modern smartphones (iPhone XS+, Google Pixel 3+, Samsung S20+)\n• Switch between physical SIM and eSIM anytime\n\nContact us if you need help: support@zoikomobile.co.uk",
            "items": ["Activate SIM", "Zoiko Plans", "Contact Us", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["roaming", "eu", "europe", "travel", "holiday", "abroad"]):
        return {
            "reply": "🇪🇺 EU Roaming is included on ALL Zoiko plans!\n\n• Standard plans: 5GB roaming data + 500 min/texts\n• Max plans: 15GB roaming data + 1000 min/texts\n• Elite plans: 30GB roaming data + 2000 min/texts\n• Unlimited plans: 40GB roaming + unlimited calls\n\nNo extra charges — just use your phone as normal in the EU!",
            "items": ["Zoiko Plans", "International Calls", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["contact", "support", "help", "problem", "issue", "complaint"]):
        return {
            "reply": "🤝 Our support team is here to help!\n\n📧 Email: support@zoikomobile.co.uk\n🌐 Contact form: zoikomobile.co.uk/contact-us/\n📚 Help centre: zoikomobile.co.uk/support/\n\nWe aim to respond within 24 hours. Priority customers get a 2-hour response time.",
            "items": [{"text": "Contact Us", "url": "https://zoikomobile.co.uk/contact-us/"}, "Support", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["device", "phone", "handset", "smartphone"]):
        return {
            "reply": "📱 Zoiko offers a range of modern smartphones and devices, designed to work seamlessly with our network.\n\nVisit our devices page to see the latest available handsets and accessories.",
            "items": [{"text": "View Devices", "url": "https://zoikomobile.co.uk/devices/"}, "Zoiko Plans", "🏠 Main Menu"],
        }

    if any(w in msg for w in ["social", "benefit", "low income", "universal credit", "pip"]):
        return {
            "reply": "💙 Zoiko Social Tariff plans — affordable connectivity for those on benefits:\n\n• Social 3GB — £3.99/mo | Unlimited Calls & Texts + Social Media\n• Social 10GB — £7.49/mo | Unlimited Calls & Texts + Social Media ⭐\n\nAvailable to those receiving qualifying benefits. Visit zoikomobile.co.uk/social-tariff-plans/",
            "items": ["Zoiko Plans", "Contact Us", "🏠 Main Menu"],
        }

    # Generic fallback — still informative, not a repeated error message
    return {
        "reply": "Thanks for your message! 😊 I'm Zovie, your Zoiko Mobile assistant.\n\nI can help you with:\n• Plan recommendations & pricing\n• SIM activation & top-up\n• International calling\n• Switching networks\n• Business plans\n• Technical support\n\nPlease use the menu below or type a specific question and I'll do my best to help!",
        "items": ["Zoiko Plans", "Contact Us", "Support", "🏠 Main Menu"],
    }


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