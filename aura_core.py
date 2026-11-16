""""Pure application data and validation for the AURA Telegram bot."""
from __future__ import annotations

SECTIONS: dict[str, str] = {
    "serv_enterprise": "🏢 قسم Enterprise\\nحلول إدارة الأعمال والمشاريع.",
    "serv_multi": "🤖 قسم Multi-Agent\\nتنسيق الوكلاء وتوزيع المهام.",
    "serv_chat": "💬 قسم Chat\\nتكاملات المحادثة وخدمة العملاء.",
    "serv_code": "🎨 قسم Code & Design\\nأدوات البرمجة والتصميم.",
    "serv_analytics": "📊 قسم Analytics\\nتحليل البيانات والتقارير.",
    "serv_automation": "⚡ قسم Automation\\nأتمتة المهام المتكررة.",
}

MENU_ROWS: tuple[tuple[tuple[str, str], ...], ...] = (
    (("🏢 Enterprise", "serv_enterprise"), ("🤖 Multi-Agent", "serv_multi")),
    (("💬 Chat", "serv_chat"), ("🎨 Code & Design", "serv_code")),
    (("📊 Analytics", "serv_analytics"), ("⚡ Automation", "serv_automation")),
    (("💳 الاشتراكات", "pay_sub"),),
)

PAYMENT_DISABLED_MESSAGE = (
    "💳 الدفع غير مفعّل بعد. لن نعرض روابط دفع تجريبية أو غير موثوقة. "
    "يرجى التواصل مع إدارة البوت لتفعيل وسيلة دفع رسمية."
)
UNKNOWN_CALLBACK_MESSAGE = "الخيار غير معروف. أرسل /start لعرض الأقسام المتاحة."


def get_section_text(callback_data: str) -> str | None:
    """Return the description for a supported section callback."""
    return SECTIONS.get(callback_data)


def is_supported_callback(callback_data: str) -> bool:
    """Accept only explicitly declared menu callback identifiers."""
    return callback_data == "pay_sub" or callback_data in SECTIONS
