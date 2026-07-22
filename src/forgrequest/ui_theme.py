"""Light, high-contrast Web Console theme override."""
from __future__ import annotations

LIGHT_THEME = r'''
<style id="forgrequest-light-theme">
:root{color-scheme:light;--bg:#eef4f8;--bg-alt:#f7fafc;--panel:#fff;--panel-2:#f4f8fb;--panel-3:#edf4f7;--line:#cbd9e3;--line-strong:#9fb5c4;--text:#162634;--muted:#587084;--muted-2:#758b9d;--accent:#0f9f9a;--accent-2:#087a80;--accent-soft:rgba(15,159,154,.10);--blue:#2678c8;--ok:#218653;--warn:#9a6714;--danger:#c53f62;--shadow:0 18px 48px rgba(36,62,80,.12)}
body{color:var(--text);background:radial-gradient(circle at 8% -10%,rgba(44,190,183,.16),transparent 30%),radial-gradient(circle at 92% 2%,rgba(66,141,209,.12),transparent 28%),linear-gradient(145deg,#eef4f8,#f8fbfd 72%)}
header{background:rgba(255,255,255,.92);border-bottom-color:rgba(84,121,145,.22);box-shadow:0 8px 28px rgba(56,82,98,.07)}
.brand-copy h1,.hero h2,.section-head h2,.card h3,.feature strong{color:#18384a}.brand-copy p,.hero p,.section-head p,.card-desc,.help-text,.feature span{color:var(--muted)}
.version{background:#effaf8;color:#087a80;border-color:rgba(15,159,154,.28)}.shortcut{background:#f7fafc;color:var(--muted);border-color:var(--line)}
.sidebar,.card,.summary-item,.feature{background:#fff;border-color:var(--line);box-shadow:0 10px 30px rgba(54,81,99,.08)}
.scope-note,.mode-card{background:#f4f8fb;color:var(--muted);border-color:var(--line)}
.tab{color:#587084}.tab:hover,.tab.active{color:#133345;background:linear-gradient(90deg,rgba(15,159,154,.13),rgba(15,159,154,.03));border-color:rgba(15,159,154,.22)}
.hero{background:linear-gradient(135deg,#fff,#eef8f8);border-color:#bedadf;box-shadow:var(--shadow)}.eyebrow,.section-tag,.mono{color:#087a80}.status-chip{background:rgba(255,255,255,.86);border-color:var(--line)}.status-chip strong,.summary-item strong{color:#17384a}
.card.accent{background:linear-gradient(145deg,#fff,#f1fbfa);border-color:#a9d5d5}
input:not([type=checkbox]),select,textarea{background:#fbfdfe;color:#173246;border-color:#bdcfdb;box-shadow:inset 0 1px 2px rgba(36,62,80,.03)}input::placeholder,textarea::placeholder{color:#93a6b3}input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(15,159,154,.12)}input:disabled,select:disabled,textarea:disabled{background:#eef3f6}
.check{background:#f8fbfd;color:#345366;border-color:#c7d7e1}.check:hover{border-color:#9fc7ca;background:#f2fbfa}.mode-option input:checked+.mode-card{background:#eefaf8;border-color:var(--accent);box-shadow:0 0 0 3px rgba(15,159,154,.08)}
.btn-secondary{background:#edf4f8;color:#244356;border-color:#bfd0dc}.btn-danger{background:#fff2f5;color:#a92e50;border-color:#e4afbd}.notice{background:#fff9ec;color:#78551a;border-color:#dfc38d}.success-notice{background:#effaf3;color:#26633c;border-color:#9fd0af}
.terminal{background:#07111d;border-color:#25425c;box-shadow:0 18px 44px rgba(22,43,59,.18)}.terminal-bar{background:#0c1c2c;border-bottom-color:#294861}.terminal-title{color:#d7e7f3}.run-status{color:#9fb4c5}.terminal pre{color:#dcf6ff}.artifact{color:#bdf7ed;border-color:#335a72;background:#10263a}
</style>
'''


def apply_light_theme(html: str) -> str:
    if 'id="forgrequest-light-theme"' in html:
        return html
    marker = "</head>"
    return html.replace(marker, LIGHT_THEME + "\n" + marker, 1) if marker in html else html + LIGHT_THEME
