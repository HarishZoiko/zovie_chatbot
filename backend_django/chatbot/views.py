from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.core.mail import get_connection
import json
import traceback

from .models import Feedback


# =============================
# LOAD CHATBOT PAGE
# =============================

def home(request):
    return render(request, "index.html")


# =============================
# CHAT API
# =============================

@csrf_exempt
def chat(request):

    if request.method == "POST":

        data = json.loads(request.body)

        message = data.get("message", "")

        return JsonResponse({
            "answer": "Please choose one of the menu options."
        })


# =============================
# FEEDBACK API
# =============================

@csrf_exempt
def feedback(request):

    if request.method == "POST":

        try:

            data = json.loads(request.body)

            rating   = data.get("rating")
            name     = data.get("name")
            phone    = data.get("phone")
            email    = data.get("email")
            message  = data.get("message")

            # =============================
            # SAVE TO DATABASE
            # =============================

            feedback_obj = Feedback.objects.create(
                rating=rating,
                name=name,
                phone=phone,
                email=email,
                message=message
            )

            # =============================
            # EMAIL ALERT TO SUPPORT TEAM
            # FIX: fail_silently=False so errors are visible
            # FIX: wrapped in try/except to catch and log email errors
            # =============================

            subject = "New Chatbot Support Request"

            email_body = f"""
A new support request was submitted through the Zoiko chatbot.

User Details:

Name    : {name}
Email   : {email}
Phone   : {phone}
Rating  : {rating}

User Issue:
{message}

You can reply directly to this email to contact the user.
"""

            try:

                mail = EmailMessage(
                    subject,
                    email_body,
                    "support@zoikomobile.co.uk",       # From
                    ["support@zoikomobile.co.uk"],     # To
                    reply_to=[email]                   # Reply-To = user's email
                )

                mail.send(fail_silently=False)         # ✅ FIXED: See real errors

                print("\n✅ Email sent successfully to support@zoikomobile.co.uk")

            except Exception as email_error:

                # ✅ FIXED: Log exact email error without crashing the whole request
                print("\n❌ EMAIL SEND FAILED:")
                print(str(email_error))
                traceback.print_exc()

            # =============================
            # TERMINAL LOG
            # =============================

            print("\n===== USER FEEDBACK RECEIVED =====")
            print("Name   :", name)
            print("Email  :", email)
            print("Phone  :", phone)
            print("Rating :", rating)
            print("Message:", message)
            print("==================================\n")

            return JsonResponse({"status": "success"})

        except Exception as e:

            print("Feedback error:", e)
            traceback.print_exc()

            return JsonResponse({"status": "error", "detail": str(e)})  # ✅ FIXED: indentation