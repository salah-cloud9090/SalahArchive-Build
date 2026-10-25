@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "MSI=%~dp0offline_packages\mysql-8.4.13-winx64.msi"
if not exist "%MSI%" (
 echo [ERROR] ملف تثبيت MySQL الكامل غير موجود:
 echo %MSI%
 echo نزّل mysql-8.4.13-winx64.msi من صفحة MySQL الرسمية وضعه داخل offline_packages.
 echo لن يتم تنزيل أي شيء تلقائيا ولن تُمسح أي قاعدة بيانات.
 pause
 exit /b 2
)
echo هذا سيبدأ مثبت MySQL الرسمي. لا تستخدم إعدادات إزالة أو ترقية لقاعدة موجودة دون نسخة احتياطية.
echo بعد تثبيت الخادم، أنشئ قاعدة محلية ومستخدم تطبيق محدود الصلاحيات وفق README_MYSQL_OFFLINE_AR.txt.
start /wait msiexec.exe /i "%MSI%"
if errorlevel 1 echo تحقق من نتيجة مثبت MySQL يدويا.
pause
