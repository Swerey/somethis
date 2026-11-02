import time
import mss
import numpy as np
from rapidocr_onnxruntime import RapidOCR

t0 = time.perf_counter()
engine = RapidOCR()
print(f"OCR engine init: {(time.perf_counter()-t0)*1000:.0f}ms", flush=True)

with mss.mss() as sct:
    img = np.array(sct.grab(sct.monitors[1]))[:, :, :3]  # 全屏
print(f"capture: {img.shape}", flush=True)

t1 = time.perf_counter()
result, elapse = engine(img)
dt = (time.perf_counter() - t1) * 1000
print(f"OCR time: {dt:.0f}ms, items: {len(result) if result else 0}", flush=True)
if result:
    for box, text, score in result[:20]:
        print(f"  [{score:.2f}] {text}", flush=True)
else:
    print("  (未识别到文字)", flush=True)
