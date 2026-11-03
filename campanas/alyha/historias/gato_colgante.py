"""Graba la cara del gato (fotograma de su vídeo) sobre el colgante e3-mano.png. Uso: python3 gato_colgante.py <dir_scratch con hist_in/ y gato/cara.png>"""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageChops
S=sys.argv[1]
base=Image.open(f'{S}/hist_in/e3-mano.png').convert('RGB')
cx,cy,r=407,1050,84
box=(cx-110,cy-110,cx+110,cy+110)
reg=base.crop(box)
# silver background without engraving: remove dark lines with max filter then blur
clean=reg.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(22))
# cat engraving
cat=Image.open(f'{S}/gato/cara.png').convert('L')
cat=ImageOps.autocontrast(cat,cutoff=2)
cat=ImageOps.equalize(cat)
cat=cat.filter(ImageFilter.UnsharpMask(3,180,2))
size=int(r*1.55)
cat=cat.resize((size,size),Image.LANCZOS)
# soft elliptical vignette so background fades into silver
m=Image.new('L',(size,size),0)
dm_=ImageDraw.Draw(m)
dm_.ellipse((int(size*.17),int(size*.20),int(size*.84),int(size*.97)),fill=255)
dm_.polygon([(int(size*.14),int(size*.13)),(int(size*.40),int(size*.28)),(int(size*.22),int(size*.45))],fill=255)
dm_.polygon([(int(size*.90),int(size*.14)),(int(size*.62),int(size*.28)),(int(size*.80),int(size*.45))],fill=255)
m=m.filter(ImageFilter.GaussianBlur(size*.03))
inv=ImageOps.invert(cat)  # darkness amount
inv=ImageChops.multiply(inv,m)
inv=inv.point(lambda v:int(min(255,v*1.05)))
# darken clean silver by engraving amount
eng=clean.copy()
dark=Image.new('RGB',eng.size,(38,38,42))
mask_full=Image.new('L',eng.size,0)
off=((eng.width-size)//2,(eng.height-size)//2-2)
mask_full.paste(inv,off)
# limit to disc interior, avoid bail at top
dm=Image.new('L',eng.size,0)
c=110
ImageDraw.Draw(dm).ellipse((c-r-3,c-r,c+r+3,c+r+8),fill=255)
ImageDraw.Draw(dm).rectangle((0,0,eng.width,c-r+14),fill=0)
dm=dm.filter(ImageFilter.GaussianBlur(3))
eng=Image.composite(dark,eng,mask_full)
# subtle noise/texture like laser
eng=eng.filter(ImageFilter.GaussianBlur(0.6))
out=base.copy()
out.paste(Image.composite(eng,reg,dm),box[:2])
out.save(f'{S}/hist_in/e5-gato-colgante.png')
out.crop((250,880,560,1230)).resize((620,700)).save(f'{S}/gato-colg-z.jpg')
