import os

svg_path = r'd:\CoE Y.4 T.1\241-353\code\Aphrodize\diagram\deployment-2machine-slide.svg'
html_path = r'd:\CoE Y.4 T.1\241-353\code\Aphrodize\diagram\render-slide.html'

with open(svg_path, 'r', encoding='utf-8') as f:
    svg_content = f.read()

template = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin: 0; padding: 0; }
    html, body {
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      background: #FFFFFF;
    }
    svg {
      width: 1920px;
      height: 1080px;
      display: block;
    }
  </style>
</head>
<body>
""" + svg_content + """
</body>
</html>"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(template)

print("render-slide.html written.")
