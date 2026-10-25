# -*- coding: utf-8 -*-
"""Direct Windows WIA scanning helper for Canon scanners with a WIA driver."""
from pathlib import Path
import tempfile, os


def list_wia_devices():
    """Return scanners visible to the Windows WIA driver layer."""
    if os.name != 'nt':
        return []
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            manager = win32com.client.Dispatch('WIA.DeviceManager')
            result = []
            for info in manager.DeviceInfos:
                try:
                    device_id = str(info.DeviceID)
                    name = device_id
                    for prop in info.Properties:
                        try:
                            if str(prop.Name).lower() == 'name':
                                name = str(prop.Value)
                                break
                        except Exception:
                            pass
                    result.append({'id': device_id, 'name': name})
                except Exception:
                    continue
            return result
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def scan_to_pdf(output_path, options=None):
    """Acquire one or more pages through the Windows WIA dialog and save as PDF.
    Requires Windows, pywin32, and Pillow. Returns number of pages.
    """
    options = options or {}
    if os.name != 'nt':
        raise RuntimeError('المسح المباشر عبر WIA يعمل على Windows فقط.')
    try:
        import pythoncom
        import win32com.client
        from PIL import Image
        import ctypes
    except Exception as exc:
        raise RuntimeError('ثبّت pywin32 وPillow من ملف install_dependencies.bat أولاً.') from exc
    pythoncom.CoInitialize()
    tmpdir = Path(tempfile.mkdtemp(prefix='admin_wia_scan_'))
    images=[]
    try:
        dialog = win32com.client.Dispatch('WIA.CommonDialog')
        while True:
            try:
                selected_id = str(options.get('device_id', '') or '').strip()
                if selected_id:
                    manager = win32com.client.Dispatch('WIA.DeviceManager')
                    info_match = None
                    for info in manager.DeviceInfos:
                        try:
                            if str(info.DeviceID) == selected_id:
                                info_match = info
                                break
                        except Exception:
                            continue
                    if info_match is None:
                        raise RuntimeError('الماسح المختار لم يعد ظاهراً في Windows. حدّث الصفحة واختر جهازاً متاحاً.')
                    device = info_match.Connect()
                    source_item = device.Items(1)
                    image_file = dialog.ShowTransfer(source_item, '{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}', False)
                    jpg = tmpdir / f'page_{len(images)+1:04d}.jpg'
                    image_file.SaveFile(str(jpg))
                    images.append(jpg)
                else:
                    choose_device = str(options.get('select_device','1')) == '1'
                    item = dialog.ShowAcquireImage(1, 0, 0, '{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}', choose_device, True, False)
                    jpg = tmpdir / f'page_{len(images)+1:04d}.jpg'
                    item.SaveFile(str(jpg))
                    images.append(jpg)
            except Exception as exc:
                if not images:
                    raise RuntimeError('ألغيت عملية المسح أو تعذر الوصول إلى الماسح. تأكد من تشغيل تعريف Canon WIA.') from exc
                break
            sides = str(options.get('sides','simplex'))
            if sides == 'duplex':
                prompt = 'تم مسح صفحة من كتاب مضبوط على وضع الوجهين. ضع الوجه التالي (الخلفي/الصفحة التالية) في الماسح ثم اختر نعم للمتابعة، أو لا لإنهاء الكتاب.'
            else:
                prompt = 'تم مسح صفحة. هل تريد مسح صفحة أخرى للكتاب نفسه؟'
            answer = ctypes.windll.user32.MessageBoxW(None, prompt, 'الماسح الضوئي Canon', 4 | 32)
            if answer != 6: break
        if not images:
            raise RuntimeError('لم يتم مسح أي صفحة.')
        from PIL import ImageEnhance, ImageStat, ImageOps
        pil=[]
        skipped=0
        brightness=float(options.get('brightness',100))/100.0
        contrast=float(options.get('contrast',110))/100.0
        quality=max(45,min(95,int(options.get('quality',80))))
        resolution=max(100,min(300,int(options.get('resolution',200))))
        skip_blank=str(options.get('skip_blank','0'))=='1'
        for p in images:
            im=Image.open(p).convert('RGB')
            # Mild automatic correction before user-selected brightness/contrast.
            im=ImageOps.autocontrast(im, cutoff=1)
            if brightness != 1.0: im=ImageEnhance.Brightness(im).enhance(brightness)
            if contrast != 1.0: im=ImageEnhance.Contrast(im).enhance(contrast)
            if skip_blank:
                gray=im.convert('L')
                stat=ImageStat.Stat(gray)
                mean=stat.mean[0]
                std=stat.stddev[0]
                # Conservative blank-page filter; avoids removing pages with meaningful text.
                if mean >= 250 and std <= 5:
                    skipped += 1
                    im.close()
                    continue
            pil.append(im)
        if not pil:
            raise RuntimeError('كل الصفحات بدت فارغة حسب خيار تجاوز الصفحات الفارغة. أعد المسح وألغِ هذا الخيار إذا كان الكتاب باهتاً.')
        out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
        pil[0].save(out, 'PDF', save_all=True, append_images=pil[1:], resolution=float(resolution), quality=quality)
        for im in pil: im.close()
        return {'pages':len(pil),'skipped_blank':skipped,'quality':quality,'resolution':resolution}
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        pythoncom.CoUninitialize()
