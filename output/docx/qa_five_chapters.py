from pathlib import Path
import sys
from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageDraw
root=Path(__file__).resolve().parent/(sys.argv[1] if len(sys.argv)>1 else 'qa-five-chapters')
d=convert_from_path(str(root/'report.pdf'),dpi=110,poppler_path='C:/Users/ACER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
for i,page in enumerate(d):
    page.save(root/f'page-{i+1}.png')
for start in range(0,len(d),4):
    board=Image.new('RGB',(1300,1800),'#dddddd')
    for j in range(4):
        ix=start+j
        if ix>=len(d):break
        im=Image.open(root/f'page-{ix+1}.png')
        im.thumbnail((620,845))
        x=20+(j%2)*650;y=30+(j//2)*900
        board.paste(im,(x,y))
        ImageDraw.Draw(board).text((x,y-20),str(ix+1),fill='black')
    board.save(root/f'contact-{start//4+1}.png')
