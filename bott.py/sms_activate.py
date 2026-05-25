import requests

# ── خريطة أسماء الدول العربية إلى كود sms-activate ──
COUNTRY_CODES = {
    "روسيا": 0,
    "أوكرانيا": 1,
    "كازاخستان": 56,
    "الصين": 6,
    "الفلبين": 63,
    "إندونيسيا": 14,
    "ماليزيا": 7,
    "كينيا": 33,
    "فيتنام": 10,
    "الهند": 22,
    "إسرائيل": 9,
    "هونغ كونغ": 17,
    "بولندا": 15,
    "إنجلترا": 16,
    "نيجيريا": 39,
    "الولايات المتحدة": 187,
    "مصر": 36,
    "كمبوديا": 59,
    "باكستان": 46,
    "بنغلاديش": 68,
    "سنغافورة": 70,
    "أوزبكستان": 29,
    "تركيا": 52,
    "الإمارات": 224,
    "السعودية": 132,
    "العراق": 103,
    "المغرب": 107,
    "الجزائر": 133,
    "إثيوبيا": 108,
    "تايلاند": 60,
    "أذربيجان": 73,
    "البرازيل": 73,
    "المكسيك": 54,
    "كولومبيا": 57,
}

# ── خريطة الخدمات ──
SERVICE_CODES = {
    "واتساب": "wa",
    "تيليغرام": "tg",
    "انستغرام": "ig",
    "فيسبوك": "fb",
    "تويتر": "tw",
    "سناب شات": "sc",
    "تيك توك": "tk",
    "يوتيوب": "yt",
    "جوجل": "go",
    "أمازون": "am",
    "نتفليكس": "nf",
    "أي خدمة": "any",
}


class SmsActivate:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sms-activate.org/stubs/handler_api.php"

    def _get(self, params: dict):
        params["api_key"] = self.api_key
        try:
            r = requests.get(self.base_url, params=params, timeout=15)
            return r.text.strip()
        except Exception as e:
            return f"ERROR:{e}"

    def get_balance(self):
        """جلب الرصيد من sms-activate"""
        result = self._get({"action": "getBalance"})
        if result.startswith("ACCESS_BALANCE:"):
            return float(result.replace("ACCESS_BALANCE:", ""))
        return None

    def get_prices(self, country_code: int, service: str = "any"):
        """جلب أسعار الدولة"""
        result = self._get({
            "action": "getPrices",
            "service": service,
            "country": country_code,
        })
        try:
            import json
            return json.loads(result)
        except:
            return None

    def buy_number(self, country_code: int, service: str = "any"):
        """شراء رقم جديد — يرجع (activation_id, phone) أو None"""
        result = self._get({
            "action": "getNumber",
            "service": service,
            "country": country_code,
        })
        # مثال ناجح: ACCESS_NUMBER:12345678:79001234567
        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            if len(parts) >= 3:
                activation_id = parts[1]
                phone = parts[2]
                return activation_id, phone
        return None, None

    def get_sms_code(self, activation_id: str):
        """جلب كود SMS بعد الشراء — يرجع الكود أو None"""
        result = self._get({
            "action": "getStatus",
            "id": activation_id,
        })
        if result.startswith("STATUS_OK:"):
            return result.replace("STATUS_OK:", "")
        return None

    def cancel_number(self, activation_id: str):
        """إلغاء الرقم"""
        self._get({"action": "setStatus", "status": "8", "id": activation_id})

    def get_country_code(self, country_name: str):
        """تحويل اسم الدولة بالعربي إلى كود sms-activate"""
        return COUNTRY_CODES.get(country_name, None)

    def get_service_code(self, service_name: str):
        """تحويل اسم الخدمة بالعربي إلى كود sms-activate"""
        return SERVICE_CODES.get(service_name, "any")
