<h1 align="center">Account Record Cleaner</h1>

<p align="center">
  <em>Removes the local "expired account" record the Windscribe Windows client stores in the registry.</em>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white">
  <img alt="PowerShell" src="https://img.shields.io/badge/PowerShell-5.1%2B-5391FE?logo=powershell&logoColor=white">
  <img alt="Admin rights" src="https://img.shields.io/badge/admin%20rights-not%20required-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
</p>

<p align="center">
  <a href="#english">English</a> &nbsp;&middot;&nbsp; <a href="#persian">فارسی</a>
</p>

---

<h2 id="english">English</h2>

### What is this?

A small PowerShell utility that backs up and deletes the registry key in which the
**Windscribe desktop client for Windows** records a *previously expired* free account.

It touches **one key under `HKCU`** and nothing else. It is not a patch, a crack, or a
modified client — it just removes a local record and keeps a `.reg` backup so you can put
it back.

> [!IMPORTANT]
> This is a local cleanup tool. It does **not** change anything on Windscribe's servers,
> and it does not grant, extend, or restore any subscription. See [Limitations](#limitations).

### The problem

When the client sees a free account whose status is expired (`status == 2`), it stores that
account's `username`, `userId`, and `date` — encrypted — in the registry, under a key named
to look like a stock Windows key:

```
HKCU\Software\Microsoft\Windows\CurrentVersion\NetControlPort
    Version  REG_DWORD    0x1
    State    REG_BINARY   <encrypted blob>
```

On a later run, if the current account is free and differs from the stored record, the client
enters `CONNECT_BLOCKED_MULTI_ACCOUNT` and shows:

> Your original account `<username>` has expired.
> Creating multiple accounts to bypass free tier limitations is prohibited.

The message is not about a wrong password or a broken connection — it is this local record.

### Requirements

- Windows 10 / 11
- Windows PowerShell 5.1 (built in) or PowerShell 7+
- No Administrator rights — the key lives under `HKCU`

### Install

```powershell
git clone https://github.com/Alirezaaliniya/vpn-bypass.git
cd vpn-bypass
```

Or download the repository as a ZIP and extract it anywhere.

### Usage

```powershell
# Normal run — backs up, then deletes
.\clear-account-record.ps1

# Recommended: close the client first so the record isn't rewritten immediately
.\clear-account-record.ps1 -KillClient

# Skip the backup
.\clear-account-record.ps1 -NoBackup

# Custom backup location
.\clear-account-record.ps1 -BackupDir D:\backups
```

Or just double-click **`clear-account-record.bat`**, which launches the script with
`-ExecutionPolicy Bypass` and UTF-8 console output. Arguments pass straight through it:

```bat
clear-account-record.bat -KillClient
```

### What each run does

1. If `-KillClient` was passed, terminates any `Windscribe` processes.
2. If the key does not exist, reports "clean" and exits `0`. **Repeated runs are safe.**
3. Prints the current key contents (`Version`, and a hex preview of `State`).
4. Writes a `.reg` backup named `netcontrolport-YYYYMMDD-HHMMSS.reg`. If the backup fails,
   **nothing is deleted** and it exits `1`.
5. Deletes the key and verifies it is gone. If it still exists, exits `1`.

| Exit code | Meaning |
|---|---|
| `0` | Key deleted, or no key was present |
| `1` | Backup failed, or the key survived deletion |

### Restoring

Backups land in `backups/` next to the script (or wherever `-BackupDir` pointed).
Pick the timestamp you want and import it:

```powershell
reg.exe import .\backups\netcontrolport-20260823-174900.reg
```

> [!WARNING]
> `backups/` and `*.reg` are gitignored on purpose — a backup contains your encrypted
> account record. Never commit one.

### Repository layout

| File | Description |
|---|---|
| [clear-account-record.ps1](clear-account-record.ps1) | The cleanup script |
| [clear-account-record.bat](clear-account-record.bat) | Double-click launcher (bypasses ExecutionPolicy, sets UTF-8 output) |
| [connection-error-fix.txt](connection-error-fix.txt) | Original analysis notes (Persian) |
| `backups/` | Timestamped `.reg` backups — gitignored, created on first run |

### Where this comes from

The paths below live in the **upstream Windscribe client source**
([Windscribe/Desktop-App](https://github.com/Windscribe/Desktop-App)) — they are not files in
this repository. They are listed so the behaviour described above can be verified rather than
taken on trust.

| File | Role |
|---|---|
| `src/client/frontend/frontend-common/multipleaccountdetection/secretvalue_win.cpp` | Reads/writes/deletes the registry key (encrypted with a fixed key, `0xFA7234AAF37A31BE`) |
| `src/client/frontend/gui/mainwindow.cpp` | The multi-account detection condition |
| `src/client/frontend/frontend-common/blockconnect.cpp` | Builds the error message text |

The detection fires when all of these hold: a previous free account with `status == 2` is on
record, that record exists in local storage, the current account is free rather than premium,
it differs from the stored one (compared by username or user ID), and it is otherwise active.

### Limitations

- **Not permanent.** `setValue()` recreates the same key whenever the client next sees an
  expired account. Preventing that for good would require a code-level change around
  `MultipleAccountDetection_win::userBecomeExpired()`.
- **Local only.** It changes nothing server-side. If Windscribe has applied a restriction on
  their end, this tool has no effect on it.
- **Windows only.** macOS and Linux use `multipleaccountdetection_posix.cpp`, which stores the
  record differently.

### Disclaimer

Published for research and educational purposes — documenting how a client-side detection
mechanism stores state on your own machine, and how to inspect and reset it. Complying with
Windscribe's Terms of Service is your responsibility. Not affiliated with or endorsed by
Windscribe. No warranty; use at your own risk.

### License

MIT — see [LICENSE](LICENSE).

---

<div dir="rtl">

<h2 id="persian">فارسی</h2>

### این چیست؟

یک اسکریپت کوچک PowerShell که از کلید رجیستریِ مربوط به رکورد حساب منقضی‌شده در کلاینت دسکتاپ Windscribe روی ویندوز بکاپ می‌گیرد و سپس آن را حذف می‌کند.

فقط یک کلید زیر `HKCU` را دست می‌زند و نه چیز دیگری. نه پچ است، نه کرک، نه کلاینت دستکاری‌شده — صرفاً یک رکورد محلی را حذف می‌کند و بکاپ `.reg` نگه می‌دارد تا بتوانید برش گردانید.

> [!IMPORTANT]
> این ابزار فقط محلی است. هیچ تغییری در سمت سرور Windscribe ایجاد نمی‌کند و هیچ اشتراکی را تمدید یا فعال نمی‌کند. بخش محدودیت‌ها را ببینید.

### مسئله

وقتی کلاینت یک حساب رایگان با وضعیت منقضی (`status == 2`) ببیند، مشخصات آن حساب — `username`، `userId` و `date` — را به‌صورت رمزگذاری‌شده در رجیستری ذخیره می‌کند. اسم کلید طوری انتخاب شده که شبیه کلیدهای خود ویندوز به نظر برسد:

</div>

```
HKCU\Software\Microsoft\Windows\CurrentVersion\NetControlPort
    Version  REG_DWORD    0x1
    State    REG_BINARY   <encrypted blob>
```

<div dir="rtl">

در اجرای بعدی، اگر حساب فعلی رایگان و متفاوت از رکورد ذخیره‌شده باشد، کلاینت وارد حالت `CONNECT_BLOCKED_MULTI_ACCOUNT` می‌شود و این پیام را نشان می‌دهد:

</div>

> Your original account `<username>` has expired.
> Creating multiple accounts to bypass free tier limitations is prohibited.

<div dir="rtl">

این پیام ربطی به اشتباه‌بودن رمز عبور یا قطع‌بودن اینترنت ندارد؛ علتش همین رکورد محلی است.

### پیش‌نیازها

- ویندوز ۱۰ یا ۱۱
- ‏Windows PowerShell 5.1 (از قبل نصب است) یا PowerShell 7+
- نیازی به دسترسی Administrator نیست — کلید زیر `HKCU` است

### نصب

</div>

```powershell
git clone https://github.com/Alirezaaliniya/vpn-bypass.git
cd vpn-bypass
```

<div dir="rtl">

یا فایل ZIP مخزن را دانلود و در هر مسیری استخراج کنید.

### نحوه‌ی استفاده

</div>

```powershell
# حالت عادی — بکاپ می‌گیرد و حذف می‌کند
.\clear-account-record.ps1

# توصیه‌شده: اول کلاینت را ببند تا رکورد بلافاصله دوباره نوشته نشود
.\clear-account-record.ps1 -KillClient

# بدون بکاپ
.\clear-account-record.ps1 -NoBackup

# مسیر دلخواه برای بکاپ
.\clear-account-record.ps1 -BackupDir D:\backups
```

<div dir="rtl">

یا کافی است روی `clear-account-record.bat` دابل‌کلیک کنید؛ این فایل اسکریپت را با `-ExecutionPolicy Bypass` و خروجی UTF-8 اجرا می‌کند. آرگومان‌ها را هم می‌توانید از همان طریق بدهید:

</div>

```bat
clear-account-record.bat -KillClient
```

<div dir="rtl">

### هر بار اجرا چه اتفاقی می‌افتد

۱. اگر `-KillClient` داده شده باشد، پروسه‌های `Windscribe` بسته می‌شوند.

۲. اگر کلید وجود نداشته باشد، پیام «تمیز است» و خروج با کد `0`. اجرای مکرر بی‌خطر است.

۳. محتوای فعلی کلید نمایش داده می‌شود (`Version` و پیش‌نمایش هگز `State`).

۴. بکاپ `.reg` با نام `netcontrolport-YYYYMMDD-HHMMSS.reg` ساخته می‌شود. اگر بکاپ ناموفق باشد، حذف انجام نمی‌شود و خروج با کد `1`.

۵. کلید حذف و حذف‌شدنش تأیید می‌شود. اگر هنوز موجود باشد، خروج با کد `1`.

| کد خروج | معنی |
|---|---|
| `0` | کلید حذف شد، یا اصلاً وجود نداشت |
| `1` | بکاپ ناموفق بود، یا کلید بعد از حذف باقی مانده |

### بازگردانی

بکاپ‌ها در پوشه‌ی `backups/` کنار اسکریپت ساخته می‌شوند (یا هر مسیری که به `-BackupDir` داده‌اید). تاریخ‌ومهر مورد نظر را انتخاب و import کنید:

</div>

```powershell
reg.exe import .\backups\netcontrolport-20260823-174900.reg
```

<div dir="rtl">

> [!WARNING]
> پوشه‌ی `backups/` و فایل‌های `*.reg` عمداً در `.gitignore` هستند — هر بکاپ حاوی رکورد رمزگذاری‌شده‌ی حساب شماست. هرگز آن را commit نکنید.

### ساختار مخزن

| فایل | توضیح |
|---|---|
| [clear-account-record.ps1](clear-account-record.ps1) | اسکریپت اصلی پاک‌سازی |
| [clear-account-record.bat](clear-account-record.bat) | اجرا با دابل‌کلیک (ExecutionPolicy را دور می‌زند، خروجی را UTF-8 می‌کند) |
| [connection-error-fix.txt](connection-error-fix.txt) | یادداشت‌های اولیه‌ی تحلیل |
| `backups/` | بکاپ‌های `.reg` با تاریخ‌ومهر — در `.gitignore` است و در اولین اجرا ساخته می‌شود |

### این اطلاعات از کجا آمده

مسیرهای زیر مربوط به سورس کلاینت Windscribe هستند ([Windscribe/Desktop-App](https://github.com/Windscribe/Desktop-App))، نه فایل‌های این مخزن. آورده شده‌اند تا رفتار توضیح‌داده‌شده قابل بررسی باشد.

| فایل | نقش |
|---|---|
| `src/client/frontend/frontend-common/multipleaccountdetection/secretvalue_win.cpp` | خواندن/نوشتن/حذف کلید رجیستری (رمزگذاری با کلید ثابت `0xFA7234AAF37A31BE`) |
| `src/client/frontend/gui/mainwindow.cpp` | شرط تشخیص وضعیت چند-حسابی |
| `src/client/frontend/frontend-common/blockconnect.cpp` | ساخت متن پیام خطا |

تشخیص وقتی فعال می‌شود که همه‌ی این شرط‌ها برقرار باشند: یک حساب رایگان قبلی با `status == 2` ثبت شده باشد، رکوردش در storage محلی موجود باشد، حساب فعلی رایگان (نه premium) باشد، با حساب ذخیره‌شده متفاوت باشد (مقایسه با username یا user ID)، و در غیر این صورت فعال باشد.

### محدودیت‌ها

- دائمی نیست. تابع `setValue()` هر بار که کلاینت دوباره یک حساب منقضی ببیند، همین کلید را از نو می‌سازد. برای جلوگیری دائمی باید در سطح کد جلوی `MultipleAccountDetection_win::userBecomeExpired()` گرفته شود.
- فقط محلی است. هیچ تغییری در وضعیت سمت سرور Windscribe ایجاد نمی‌کند. اگر محدودیتی سمت سرور اعمال شده باشد، این ابزار تأثیری روی آن ندارد.
- فقط ویندوز. روی macOS و لینوکس از `multipleaccountdetection_posix.cpp` استفاده می‌شود که مکانیزم ذخیره‌سازی متفاوتی دارد.

### سلب مسئولیت

این مخزن با هدف پژوهشی و آموزشی منتشر شده است — مستندسازی این‌که یک مکانیزم تشخیص سمت-کلاینت چطور روی دستگاه خودتان اطلاعات ذخیره می‌کند و چطور می‌شود آن را بررسی و ریست کرد. رعایت شرایط استفاده‌ی (ToS) شرکت Windscribe بر عهده‌ی خود شماست. این پروژه هیچ وابستگی یا تأییدی از سوی Windscribe ندارد. بدون هیچ ضمانتی ارائه می‌شود؛ مسئولیت استفاده با شماست.

### لایسنس

MIT — فایل [LICENSE](LICENSE) را ببینید.

</div>
