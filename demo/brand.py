from pathlib import Path

import gradio as gr

from deadwax.agent.evidence import HEADERS

FAVICON = Path(__file__).parent / "assets" / "deadwax-favicon.svg"

INK = "#201f1d"
GOLD = "#b68235"
PAPER = "#faf8f4"
SURFACE = "#fffdf9"
RULE = "#e4dfd6"
MUTED = "#6b6762"

INK_DARK = "#e8e4dd"
GOLD_DARK = "#e1ad66"
GROUND_DARK = "#1b1a18"
SURFACE_DARK = "#232120"
RULE_DARK = "#3a3631"
MUTED_DARK = "#a39d94"

DISPLAY_FONT = "Cormorant Garamond"

ENERGY_COLUMN = HEADERS.index("Energy (estimate)")
LAST_PLAYED_COLUMN = HEADERS.index("Last played")

HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Cormorant+Garamond:wght@400;500&display=swap">'
)

THEME = gr.themes.Base(
    font=["system-ui", "-apple-system", "Segoe UI", "sans-serif"],
    radius_size=gr.themes.sizes.radius_sm,
).set(
    body_background_fill=PAPER,
    body_background_fill_dark=GROUND_DARK,
    body_text_color=INK,
    body_text_color_dark=INK_DARK,
    body_text_color_subdued=MUTED,
    body_text_color_subdued_dark=MUTED_DARK,
    background_fill_primary=SURFACE,
    background_fill_primary_dark=SURFACE_DARK,
    background_fill_secondary=PAPER,
    background_fill_secondary_dark=GROUND_DARK,
    block_background_fill=SURFACE,
    block_background_fill_dark=SURFACE_DARK,
    block_border_color=RULE,
    block_border_color_dark=RULE_DARK,
    border_color_primary=RULE,
    border_color_primary_dark=RULE_DARK,
    input_background_fill=SURFACE,
    input_background_fill_dark=SURFACE_DARK,
    color_accent=GOLD,
    color_accent_soft="#f3e7d3",
    color_accent_soft_dark="#3a2f1f",
    link_text_color=GOLD,
    link_text_color_dark=GOLD_DARK,
    button_primary_background_fill=INK,
    button_primary_background_fill_hover="#3a3835",
    button_primary_text_color=PAPER,
    button_primary_background_fill_dark=GOLD_DARK,
    button_primary_background_fill_hover_dark="#ecc188",
    button_primary_text_color_dark=GROUND_DARK,
    button_secondary_background_fill=SURFACE,
    button_secondary_background_fill_dark=SURFACE_DARK,
)

CSS = f"""
:root {{ --dw-ink: {INK}; --dw-gold: {GOLD}; --dw-muted: {MUTED}; }}
.dark {{ --dw-ink: {INK_DARK}; --dw-gold: {GOLD_DARK}; --dw-muted: {MUTED_DARK}; }}

.dw-header {{ display: flex; align-items: center; gap: 22px; padding: 12px 0 4px; }}
.dw-header svg {{ width: 68px; height: 68px; flex: none; color: var(--dw-ink); }}
.dw-header .dw-gold {{ stroke: var(--dw-gold); }}
.dw-wordmark {{
  font-family: "{DISPLAY_FONT}", Georgia, serif; font-weight: 400; font-size: 40px;
  letter-spacing: 0.16em; line-height: 1; color: var(--dw-ink); margin: 0;
}}
.dw-rule {{ height: 1px; background: var(--dw-gold); margin: 10px 0 8px; width: 100%; }}
.dw-tagline {{
  font-family: "{DISPLAY_FONT}", Georgia, serif; font-size: 13px; letter-spacing: 0.16em;
  color: var(--dw-muted); margin: 0;
}}

.dw-intro a, .dw-answer a {{ color: var(--dw-gold); }}

.dw-answer {{
  border: 1px solid var(--dw-gold); border-left-width: 4px; border-radius: 4px;
  padding: 20px 24px !important; min-height: 240px; font-size: 17px; line-height: 1.6;
}}
.dw-answer p, .dw-answer li {{ font-size: 17px; }}
.dw-answer blockquote {{
  margin: 0 0 14px; padding: 0 0 10px; border: none; border-bottom: 1px solid var(--dw-gold);
  color: var(--dw-muted); font-style: italic;
}}
.dw-question textarea {{ min-height: 84px; }}
.dw-thread {{ color: var(--dw-muted); font-size: 14px; }}
.dw-thread p {{ margin: 4px 0; }}
.dw-trail code {{ font-size: 12px; white-space: pre-wrap; word-break: break-word; }}

.dw-section h2 {{
  font-family: "{DISPLAY_FONT}", Georgia, serif; font-weight: 500; font-size: 26px;
  letter-spacing: 0.04em; border-bottom: 1px solid var(--dw-gold); padding-bottom: 4px;
}}
.dw-guide pre {{ white-space: pre-wrap; word-break: break-word; }}

@media (max-width: 640px) {{
  .gradio-container {{
    padding-left: 10px !important; padding-right: 10px !important;
    --text-sm: 12px; --text-md: 14px; --text-lg: 15px;
    --block-padding: 10px; --layout-gap: 10px;
  }}
  .dw-header {{ gap: 12px; padding: 4px 0 0; }}
  .dw-header svg {{ width: 40px; height: 40px; }}
  .dw-wordmark {{ font-size: 24px; }}
  .dw-rule {{ margin: 6px 0 4px; }}
  .dw-tagline {{ font-size: 9px; }}
  .dw-intro p {{ font-size: 13px; line-height: 1.5; }}
  .dw-section h2 {{ font-size: 20px; margin: 10px 0 4px; }}
  .dw-question textarea {{ min-height: 52px; }}
  .dw-examples button {{ font-size: 12px !important; padding: 4px 8px !important; }}
  .dw-answer {{ padding: 12px 14px !important; min-height: 0; }}
  .dw-answer p, .dw-answer li {{ font-size: 15px; line-height: 1.5; }}
  .dw-thread {{ font-size: 13px; }}
  .dw-table {{ font-size: 12px; }}
  .dw-table [data-col="{ENERGY_COLUMN}"], .dw-table [data-col="{LAST_PLAYED_COLUMN}"] {{
    display: none !important;
  }}
  .dw-guide p, .dw-guide li {{ font-size: 13px; }}
  .dw-guide pre, .dw-guide code {{ font-size: 11px; }}
  .dw-term {{ font-size: 11px; min-height: 0; padding: 12px 14px; }}
}}
"""

HEADER = """
<div class="dw-header">
  <svg viewBox="0 0 220 220" role="img" aria-label="Deadwax">
    <circle cx="110" cy="110" r="100" fill="none" stroke="currentColor" stroke-width="7"/>
    <path d="M 10 110 L 78 110" stroke="currentColor" stroke-width="7"/>
    <path class="dw-gold" d="M 78 110 L 92 110" stroke-width="14"/>
    <circle cx="110" cy="110" r="4" fill="currentColor"/>
  </svg>
  <div>
    <p class="dw-wordmark">DEADWAX</p>
    <div class="dw-rule"></div>
    <p class="dw-tagline">AI MUSIC LIBRARIAN</p>
  </div>
</div>
"""
