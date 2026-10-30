# AURA BOT
### Telegram Automation · Python

<div align="center">

**مساعد Telegram بإعداد آمن وتشغيل قابل للتحقق.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/zkwr1081-source/AURA-BOT/actions) [![Telegram](https://img.shields.io/badge/Platform-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)

</div>

---

## ✨ عن المشروع

AURA BOT مشروع بوت Telegram مبني باستخدام Python ومكتبة python-telegram-bot. يهدف المستودع إلى إبقاء منطق البوت واضحاً، وإعداد التشغيل خارج الشيفرة، والتحقق من التغييرات آلياً.

## 🚀 الإعداد

1. ثبّت Python 3.12 أو إصداراً متوافقاً.
2. ثبّت الاعتماديات:

   ```bash
   pip install -r requirements.txt
   ```
3. عيّن رمز البوت في متغير البيئة **TELEGRAM_BOT_TOKEN** باستخدام مدير أسرار آمن.
4. شغّل نقطة الدخول:

   ```bash
   python main.py
   ```

لا تضع رمز Telegram أو أي مفتاح API في الملفات أو سجل Git. أبقِ ملف الأسرار المحلي خارج التتبع.

## 🧪 التحقق المستمر

يتضمن المستودع GitHub Actions لفحص الاعتماديات وصياغة Python والتحقق من إعداد التشغيل.

[عرض GitHub Actions](https://github.com/zkwr1081-source/AURA-BOT/actions)

## 🛡️ الأمان

- الأسرار تُمرّر عبر متغيرات البيئة أو GitHub Secrets.
- لا تنشر سجلات تحتوي على رموز أو بيانات مستخدمين.
- إذا سبق نشر رمز بوت في Git، فأبطله وأصدر رمزاً جديداً من BotFather؛ حذف الرمز من الملف الحالي لا يمحو ظهوره من تاريخ Git.

## 🤝 المساهمة

استخدم Issues لتوثيق الأخطاء والاقتراحات، وقدّم Pull Requests مع وصف موجز واختبارات مناسبة.

<div align="center">

**AURA BOT · Simple. Secure. Reliable.**

</div>
