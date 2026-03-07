"""Shared UI styling, branding, and helper functions for the ABA Auth Agent.

Import and call inject_custom_css() at the top of every page to apply branding.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
BRAND_NAME = "Lumen ABA"
BRAND_TAGLINE = "Reauthorization Intelligence for ABA Providers"
BRAND_PRIMARY = "#0B7285"       # teal-700
BRAND_PRIMARY_LIGHT = "#E6F4F7" # teal-50
BRAND_SECONDARY = "#2D6A4F"     # green-800
BRAND_ACCENT = "#F59E0B"        # amber-500
BRAND_DARK = "#1A2B3C"          # slate-900
BRAND_MUTED = "#6B7280"         # gray-500
BRAND_BG = "#F0F7F9"            # light teal bg
BRAND_WHITE = "#FFFFFF"

# Urgency / status colors
COLOR_CRITICAL = "#DC2626"      # red-600
COLOR_WARNING = "#F59E0B"       # amber-500
COLOR_SUCCESS = "#059669"       # emerald-600
COLOR_INFO = "#0B7285"          # teal-700
COLOR_NEUTRAL = "#9CA3AF"       # gray-400


def inject_custom_css():
    """Inject global custom CSS. Call once per page, right after set_page_config."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def branded_header(title: str, subtitle: str = ""):
    """Render a branded page header with optional subtitle."""
    sub_html = f'<p class="branded-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="branded-header">'
        f'<h1 class="branded-title">{title}</h1>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def sidebar_branding():
    """Render branded sidebar with logo area, trust badges, and payor list."""
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-logo">
                <span class="logo-icon">&#9672;</span>
                <span class="logo-text">{BRAND_NAME}</span>
            </div>
            <p class="sidebar-tagline">{BRAND_TAGLINE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")


def sidebar_trust_badges():
    """Render HIPAA and compliance badges in sidebar."""
    st.sidebar.markdown(
        """
        <div class="trust-badges">
            <div class="trust-badge">
                <span class="badge-icon">&#128274;</span>
                <div>
                    <span class="badge-label">HIPAA Compliant</span>
                    <span class="badge-sub">De-identified data only</span>
                </div>
            </div>
            <div class="trust-badge">
                <span class="badge-icon">&#9989;</span>
                <div>
                    <span class="badge-label">BCBA-Reviewed</span>
                    <span class="badge-sub">Clinical oversight required</span>
                </div>
            </div>
            <div class="trust-badge">
                <span class="badge-icon">&#128196;</span>
                <div>
                    <span class="badge-label">Multi-Payor</span>
                    <span class="badge-sub">5 templates supported</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, color: str = BRAND_PRIMARY, icon: str = ""):
    """Render a styled metric card. Returns HTML string."""
    icon_html = f'<span class="card-icon">{icon}</span>' if icon else ""
    return (
        f'<div class="metric-card" style="border-left: 4px solid {color};">'
        f'{icon_html}'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-label">{label}</div>'
        f'</div>'
    )


def status_badge(text: str, color: str = COLOR_INFO):
    """Return an HTML status badge."""
    return (
        f'<span class="status-badge" '
        f'style="background:{color}15; color:{color}; border: 1px solid {color}40;">'
        f'{text}</span>'
    )


def urgency_badge(urgency: str) -> str:
    """Return an HTML urgency badge based on urgency level."""
    config = {
        "expired": ("Expired", COLOR_CRITICAL),
        "critical": ("Due Soon", COLOR_CRITICAL),
        "soon": ("Upcoming", COLOR_WARNING),
        "ok": ("On Track", COLOR_SUCCESS),
        "no_period": ("No Auth", COLOR_NEUTRAL),
    }
    text, color = config.get(urgency, ("Unknown", COLOR_NEUTRAL))
    return status_badge(text, color)


def section_header(number: int, title: str, count: str = ""):
    """Render a styled section header with number badge."""
    count_html = f'<span class="section-count">{count}</span>' if count else ""
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-number">{number}</span>'
        f'<span class="section-title">{title}</span>'
        f'{count_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def progress_bar_html(value: float, max_val: float = 100, color: str = BRAND_PRIMARY) -> str:
    """Return an HTML progress bar string."""
    pct = min((value / max_val * 100) if max_val > 0 else 0, 100)
    return (
        f'<div class="progress-track">'
        f'<div class="progress-fill" style="width:{pct:.0f}%; background:{color};"></div>'
        f'</div>'
        f'<span class="progress-label">{pct:.0f}%</span>'
    )


def login_hero():
    """Render the branded login hero section."""
    st.markdown(
        f"""
        <div class="login-hero">
            <div class="login-logo">
                <span class="logo-icon-lg">&#9672;</span>
                <h1 class="login-brand">{BRAND_NAME}</h1>
            </div>
            <p class="login-tagline">{BRAND_TAGLINE}</p>
            <div class="login-features">
                <div class="login-feature">
                    <span class="feature-icon">&#128196;</span>
                    <div>
                        <strong>AI-Powered Extraction</strong>
                        <p>Upload progress reports. Get structured clinical data in seconds.</p>
                    </div>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#9998;</span>
                    <div>
                        <strong>BCBA-Controlled Narratives</strong>
                        <p>AI drafts. You review and edit every section side-by-side.</p>
                    </div>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#128203;</span>
                    <div>
                        <strong>Multi-Payor Export</strong>
                        <p>Anthem, Aetna, Optum, Blue Shield CA, Medi-Cal templates.</p>
                    </div>
                </div>
                <div class="login-feature">
                    <span class="feature-icon">&#128274;</span>
                    <div>
                        <strong>HIPAA-Conscious Design</strong>
                        <p>Built for de-identified data. Production-ready with AWS Bedrock BAA.</p>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, message: str, button_label: str = ""):
    """Render a friendly empty state with illustration."""
    btn = (
        f'<div style="margin-top:12px;">'
        f'<span class="empty-btn">{button_label}</span>'
        f'</div>'
        if button_label else ""
    )
    st.markdown(
        f'<div class="empty-state">'
        f'<span class="empty-icon">{icon}</span>'
        f'<h3 class="empty-title">{title}</h3>'
        f'<p class="empty-message">{message}</p>'
        f'{btn}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
_GLOBAL_CSS = """
<style>
/* ===== Typography & Base ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #1A2B3C;
}

/* ===== Sidebar Branding ===== */
.sidebar-brand {
    text-align: center;
    padding: 8px 0 4px 0;
}

.sidebar-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.logo-icon {
    font-size: 28px;
    color: #0B7285;
}

.logo-text {
    font-size: 22px;
    font-weight: 700;
    color: #1A2B3C;
    letter-spacing: -0.5px;
}

.sidebar-tagline {
    font-size: 11px;
    color: #6B7280;
    margin-top: 2px;
    letter-spacing: 0.3px;
}

/* ===== Trust Badges ===== */
.trust-badges {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 4px 0;
}

.trust-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: #F0F7F9;
    border-radius: 8px;
    font-size: 12px;
}

.badge-icon {
    font-size: 16px;
    flex-shrink: 0;
}

.badge-label {
    font-weight: 600;
    color: #1A2B3C;
    display: block;
    font-size: 12px;
}

.badge-sub {
    color: #6B7280;
    font-size: 10px;
    display: block;
}

/* ===== Branded Header ===== */
.branded-header {
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid #E6F4F7;
}

.branded-title {
    font-size: 28px;
    font-weight: 700;
    color: #1A2B3C;
    margin: 0;
    line-height: 1.2;
}

.branded-subtitle {
    font-size: 14px;
    color: #6B7280;
    margin: 4px 0 0 0;
}

/* ===== Metric Cards ===== */
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}

.metric-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.card-icon {
    font-size: 20px;
    display: block;
    margin-bottom: 4px;
}

.card-value {
    font-size: 28px;
    font-weight: 700;
    color: #1A2B3C;
    line-height: 1.1;
}

.card-label {
    font-size: 12px;
    color: #6B7280;
    margin-top: 4px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ===== Status Badges ===== */
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.2px;
    white-space: nowrap;
}

/* ===== Section Headers ===== */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #E5E7EB;
}

.section-number {
    background: #0B7285;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1A2B3C;
}

.section-count {
    font-size: 12px;
    color: #6B7280;
    background: #F0F7F9;
    padding: 2px 8px;
    border-radius: 8px;
    margin-left: auto;
}

/* ===== Progress Bars ===== */
.progress-track {
    background: #E5E7EB;
    border-radius: 6px;
    height: 8px;
    overflow: hidden;
    display: inline-block;
    width: 80%;
    vertical-align: middle;
}

.progress-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.3s ease;
}

.progress-label {
    font-size: 12px;
    font-weight: 600;
    color: #1A2B3C;
    margin-left: 6px;
}

/* ===== Client Table ===== */
.client-table-wrap {
    background: white;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    overflow: hidden;
    margin-top: 4px;
}

.client-table-header {
    display: grid;
    grid-template-columns: 2fr 1.2fr 1.2fr 1.5fr;
    padding: 12px 20px;
    background: #F8FAFB;
    border-bottom: 2px solid #E5E7EB;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #6B7280;
}

.client-table-row {
    display: grid;
    grid-template-columns: 2fr 1.2fr 1.2fr 1.5fr;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #F0F1F3;
    transition: background 0.15s;
}

.client-table-row:last-child {
    border-bottom: none;
}

.client-table-row:hover {
    background: #F0F7F9;
}

.client-name {
    font-weight: 600;
    font-size: 15px;
    color: #1A2B3C;
}

.client-name .client-id-sub {
    font-weight: 400;
    font-size: 12px;
    color: #9CA3AF;
    display: block;
    margin-top: 2px;
}

.client-cell {
    font-size: 14px;
    color: #374151;
}

.client-cell-muted {
    font-size: 14px;
    color: #9CA3AF;
}

.client-payor-badge {
    display: inline-block;
    padding: 4px 10px;
    background: #E6F4F7;
    color: #0B7285;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Search bar styling */
.client-search-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}

.client-count {
    font-size: 13px;
    color: #6B7280;
    display: flex;
    align-items: center;
    gap: 6px;
}

.client-count .count-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #0B7285;
    color: white;
    font-size: 12px;
    font-weight: 600;
    width: 22px;
    height: 22px;
    border-radius: 6px;
}

/* ===== Client Row Cards (legacy compat) ===== */
.client-row {
    background: white;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    border: 1px solid #E5E7EB;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.client-row:hover {
    border-color: #0B7285;
    box-shadow: 0 2px 8px rgba(11,114,133,0.08);
}

/* ===== Login Hero ===== */
.login-hero {
    text-align: center;
    padding: 30px 20px 20px 20px;
    max-width: 560px;
    margin: 0 auto;
}

.login-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 4px;
}

.logo-icon-lg {
    font-size: 40px;
    color: #0B7285;
}

.login-brand {
    font-size: 36px;
    font-weight: 700;
    color: #1A2B3C;
    margin: 0;
}

.login-tagline {
    font-size: 16px;
    color: #6B7280;
    margin: 0 0 28px 0;
}

.login-features {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    text-align: left;
    margin: 0 auto;
    max-width: 520px;
}

.login-feature {
    display: flex;
    gap: 10px;
    padding: 12px 14px;
    background: #F0F7F9;
    border-radius: 10px;
    border: 1px solid #E6F4F7;
}

.login-feature .feature-icon {
    font-size: 22px;
    flex-shrink: 0;
    margin-top: 2px;
}

.login-feature strong {
    font-size: 13px;
    color: #1A2B3C;
    display: block;
    margin-bottom: 2px;
}

.login-feature p {
    font-size: 11px;
    color: #6B7280;
    margin: 0;
    line-height: 1.4;
}

/* ===== Empty States ===== */
.empty-state {
    text-align: center;
    padding: 48px 20px;
    background: #F9FAFB;
    border-radius: 12px;
    border: 2px dashed #D1D5DB;
    margin: 20px 0;
}

.empty-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 12px;
}

.empty-title {
    font-size: 18px;
    font-weight: 600;
    color: #1A2B3C;
    margin: 0 0 6px 0;
}

.empty-message {
    font-size: 14px;
    color: #6B7280;
    margin: 0;
}

.empty-btn {
    display: inline-block;
    padding: 8px 20px;
    background: #0B7285;
    color: white;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}

/* ===== Streamlit Overrides ===== */

/* Make primary buttons match brand */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background-color: #0B7285;
    border-color: #0B7285;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 20px;
    letter-spacing: 0.2px;
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background-color: #096B7C;
    border-color: #096B7C;
}

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    border-radius: 8px;
    font-weight: 500;
    border-color: #D1D5DB;
}

.stButton > button[kind="secondary"]:hover {
    border-color: #0B7285;
    color: #0B7285;
}

/* Expanders - cleaner borders */
.streamlit-expanderHeader {
    font-weight: 600;
    font-size: 14px;
    border-radius: 8px;
}

/* Metric styling tweaks */
[data-testid="stMetric"] {
    background: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #E5E7EB;
}

[data-testid="stMetricLabel"] {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6B7280;
}

[data-testid="stMetricValue"] {
    font-size: 24px;
    font-weight: 700;
    color: #1A2B3C;
}

/* File uploader styling */
[data-testid="stFileUploader"] {
    border-radius: 10px;
}

/* Dividers */
hr {
    border-color: #E6F4F7;
}

/* Page links */
.stPageLink > a {
    border-radius: 8px;
    font-weight: 600;
}

/* Toast refinement */
.stToast {
    border-radius: 10px;
}

/* Form inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border-radius: 8px;
}

/* Tabs styling */
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 14px;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: #0B7285;
}

/* Info/Warning/Success/Error boxes */
.stAlert {
    border-radius: 10px;
}
</style>
"""
