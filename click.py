"""Click.uz online payments (SHOP-API: prepare + complete).
Enabled when CLICK_SERVICE_ID, CLICK_MERCHANT_ID and CLICK_SECRET_KEY are set. The signature rules and error codes follow Click's public
documentation, but this has NOT been run against Click's real servers: test it in their sandbox before taking real money."""
import hashlib
import hmac
import os
import urllib.parse

from . import services
from .models import Payment


def cfg():
    return {k: os.environ.get(f"CLICK_{k}", "").strip() for k in ("SERVICE_ID", "MERCHANT_ID", "SECRET_KEY")}


def enabled():
    return all(cfg().values())


def pay_url(payment, return_url):
    c = cfg()
    q = urllib.parse.urlencode({"service_id": c["SERVICE_ID"], "merchant_id": c["MERCHANT_ID"], "amount": payment.amount,
                                "transaction_param": payment.pk, "return_url": return_url})
    return "https://my.click.uz/services/pay?" + q


def sign(*parts):
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


def handle(data):
    """data: the POSTed form as a dict. Returns the JSON dict to send back."""
    c = cfg()
    g = lambda k, d="": str(data.get(k, d))
    resp = {"click_trans_id": g("click_trans_id"), "merchant_trans_id": g("merchant_trans_id"), "error": 0, "error_note": "Success"}

    def fail(code, note):
        resp.update(error=code, error_note=note)
        return resp

    if not enabled():
        return fail(-8, "Click is not configured")
    try:
        action = int(g("action"))
        amount = float(g("amount"))
    except ValueError:
        return fail(-8, "Error in request from click")
    if g("service_id") != c["SERVICE_ID"]:
        return fail(-8, "Error in request from click")
    if action == 0:
        expected = sign(g("click_trans_id"), g("service_id"), c["SECRET_KEY"], g("merchant_trans_id"), g("amount"), g("action"), g("sign_time"))
    elif action == 1:
        expected = sign(g("click_trans_id"), g("service_id"), c["SECRET_KEY"], g("merchant_trans_id"), g("merchant_prepare_id"), g("amount"), g("action"), g("sign_time"))
    else:
        return fail(-3, "Action not found")
    if not hmac.compare_digest(expected, g("sign_string")):
        return fail(-1, "SIGN CHECK FAILED!")
    pay = Payment.objects.filter(pk=g("merchant_trans_id") if g("merchant_trans_id").isdigit() else 0, method="click").first()
    if not pay:
        return fail(-5, "User does not exist")
    if pay.status == Payment.Status.PAID:
        return fail(-4, "Already paid")
    if pay.status == Payment.Status.CANCELLED:
        return fail(-9, "Transaction cancelled")
    if abs(amount - pay.amount) > 0.01:
        return fail(-2, "Incorrect parameter amount")
    if action == 0:
        pay.gateway_ref = g("click_trans_id")[:40]
        pay.save(update_fields=["gateway_ref"])
        resp["merchant_prepare_id"] = pay.pk
        return resp
    if g("merchant_prepare_id") != str(pay.pk) or pay.gateway_ref != g("click_trans_id"):
        return fail(-6, "Transaction does not exist")
    if g("error", "0").lstrip("-").isdigit() and int(g("error", "0")) < 0:
        pay.status = Payment.Status.CANCELLED
        pay.save(update_fields=["status"])
        return fail(-9, "Transaction cancelled")
    services.confirm_payment(pay)
    resp["merchant_confirm_id"] = pay.pk
    return resp
