import markdown
import subprocess
import os
import time

md_file = r"C:\Users\amitk\.gemini\antigravity\brain\a286534b-85f5-4e9e-ab20-6ef78063debc\glofcast_progress_report.md"
html_file = os.path.abspath("glofcast_progress_report.html")
pdf_file = os.path.abspath("GLOFCast_Progress_Report.pdf")

with open(md_file, "r", encoding="utf-8") as f:
    md_text = f.read()

# Replace placeholders with actual image tags
md_text = md_text.replace("`[INSERT FIGURE 1 HERE]`", "")
md_text = md_text.replace("`[INSERT FIGURE 2 HERE]`", "")
md_text = md_text.replace("`[INSERT FIGURE 3 HERE]`", "<img src='comparison_chart.png' style='width:100%; max-width:700px; display:block; margin: 20px auto;'>")
md_text = md_text.replace("`[INSERT FIGURE 4 HERE]`", "<img src='segmentation_overlay.png' style='width:100%; max-width:800px; display:block; margin: 20px auto;'>")

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: 'Times New Roman', serif; line-height: 1.6; color: #000; max-width: 900px; margin: 0 auto; }}
    h1, h2, h3 {{ color: #111; font-family: 'Segoe UI', Arial, sans-serif; }}
    h1 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-top: 0; }}
    h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 30px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 14px; page-break-inside: avoid; }}
    th, td {{ border: 1px solid #666; padding: 10px 12px; text-align: left; }}
    th {{ background-color: #f0f0f0; font-weight: bold; }}
    tr:nth-child(even) {{ background-color: #fdfdfd; }}
    .note {{ background: #f9f9f9; padding: 15px; border-left: 5px solid #0455BF; font-style: italic; margin: 20px 0; }}
    img {{ page-break-inside: avoid; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 1px solid #ddd; }}
</style>
</head>
<body>
{html_body.replace('<blockquote>\n<p>[!NOTE]', '<div class="note"><strong>NOTE:</strong>').replace('<blockquote>\n<p>[!IMPORTANT]', '<div class="note"><strong>IMPORTANT:</strong>').replace('</blockquote>', '</div>')}
</body>
</html>
"""

with open(html_file, "w", encoding="utf-8") as f:
    f.write(full_html)

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cmd = [edge_path, "--headless", "--print-to-pdf=" + pdf_file, "file:///" + html_file.replace("\\", "/")]

print("Converting HTML to PDF via Edge...")
subprocess.run(cmd, check=True)
print(f"Success! PDF created at: {pdf_file}")
