from PIL import Image, ImageDraw
import io, zipfile, random, os
job = os.environ.get('JOB') or 'demo_manual'
resdir = os.environ.get('RESDIR') or '.'
path = os.path.join(resdir, f'result_{job}.zip')
imgs = []
for i in range(6):
    im = Image.new('RGB', (960, 600), (random.randint(0,255),random.randint(0,255),random.randint(0,255)))
    d = ImageDraw.Draw(im); d.text((24,24), f'{job} #{i+1}', fill=(255,255,255))
    imgs.append(im)
with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
    for i, im in enumerate(imgs, 1):
        buf = io.BytesIO(); im.save(buf, 'PNG'); z.writestr(f'img_{i}.png', buf.getvalue())
print(path)
