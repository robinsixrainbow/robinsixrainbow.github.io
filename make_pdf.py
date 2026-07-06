"""合併三面 SVG 產出的 PDF 並寫入印刷框。先跑 gen_cards.py 再跑本檔。"""
from pypdf import PdfWriter, PdfReader
from pypdf.generic import RectangleObject
MM=72/25.4; w,h,b=97*MM,61*MM,3*MM
trim=RectangleObject((b,b,w-b,h-b)); bleed=RectangleObject((0,0,w,h))
wr=PdfWriter()
for f in ("zh","en","jp"):
    p=PdfReader(f"{f}.pdf").pages[0]; p.trimbox=trim; p.bleedbox=bleed; wr.add_page(p)
wr.write("名片_planetarian_中英日.pdf")
print("done")
