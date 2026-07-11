"""Landing page for the AI Personal Finance Agent."""

from __future__ import annotations

from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components


def _compact_html(html: str) -> str:
    """Remove Markdown-sensitive indentation from raw HTML."""
    return "".join(line.strip() for line in html.splitlines())


def _home_style() -> str:
    return _compact_html(
        dedent(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            html, body, [class*="css"] {
                font-family: -apple-system, BlinkMacSystemFont, "Inter", "SF Pro Display",
                    "SF Pro Text", "Segoe UI", sans-serif;
            }

            .stApp {
                background: #f8fbff;
                color: #0b1020;
            }

            #MainMenu,
            header[data-testid="stHeader"],
            footer {
                display: none !important;
            }

            [data-testid="stAppViewContainer"] > .main {
                background: transparent;
            }

            .block-container {
                max-width: 100% !important;
                padding: 0 !important;
            }

            .element-container:has(.home-page) {
                margin: 0 !important;
            }

            a,
            a:visited {
                color: inherit;
                text-decoration: none;
            }

            .home-page {
                min-height: 100vh;
                overflow: hidden;
                background:
                    radial-gradient(circle at 8% 58%, rgba(50, 113, 255, 0.12) 0, rgba(50, 113, 255, 0.08) 9rem, transparent 18rem),
                    radial-gradient(circle at 99% 35%, rgba(122, 62, 245, 0.13) 0, rgba(122, 62, 245, 0.08) 10rem, transparent 20rem),
                    linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
            }

            .top-nav {
                height: 82px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 47px;
                background: rgba(255, 255, 255, 0.90);
                border-bottom: 1px solid #e8ebf3;
                backdrop-filter: blur(18px);
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 16px;
            }

            .brand-icon {
                width: 40px;
                height: 40px;
                display: grid;
                place-items: center;
                border-radius: 10px;
                color: #ffffff;
                background: linear-gradient(135deg, #2658ff 0%, #7d36f6 100%);
                box-shadow: 0 14px 26px rgba(91, 75, 245, 0.22);
            }

            .brand-icon::before {
                content: "✦";
                display: block;
                font-size: 25px;
                line-height: 1;
                color: #ffffff;
            }

            .brand-text {
                font-size: 24px;
                font-weight: 800;
                letter-spacing: 0;
                color: #0d1220;
            }

            .nav-right {
                display: flex;
                align-items: center;
                gap: 28px;
            }

            .nav-links {
                display: flex;
                align-items: center;
                gap: 20px;
            }

            .nav-link {
                padding: 12px 17px;
                border-radius: 15px;
                color: #273044;
                font-size: 16px;
                font-weight: 500;
                line-height: 1;
                transition: background 180ms ease, color 180ms ease, transform 180ms ease;
            }

            .nav-link:hover {
                color: #5d35f2;
                background: rgba(116, 66, 246, 0.08);
                transform: translateY(-1px);
            }

            .nav-link.active {
                color: #5731ed;
                background: linear-gradient(135deg, rgba(33, 101, 255, 0.09), rgba(126, 55, 246, 0.13));
            }

            .avatar {
                width: 44px;
                height: 44px;
                display: grid;
                place-items: center;
                border-radius: 999px;
                background: linear-gradient(135deg, #eee9ff 0%, #e3d4ff 100%);
                color: #5d34ee;
                font-size: 18px;
                font-weight: 800;
            }

            .hero {
                position: relative;
                min-height: calc(100vh - 82px);
                padding: 42px 7vw 68px;
                text-align: center;
            }

            .spark-card {
                width: 58px;
                height: 58px;
                display: grid;
                place-items: center;
                margin: 0 auto 26px;
                border-radius: 15px;
                color: #6338f5;
                background: rgba(255, 255, 255, 0.96);
                border: 1px solid rgba(232, 235, 243, 0.95);
                box-shadow: 0 16px 34px rgba(17, 24, 39, 0.10);
            }

            .spark-card::before {
                content: "✦";
                display: block;
                font-size: 39px;
                line-height: 1;
                color: #6338f5;
            }

            .hero-title {
                margin: 0;
                font-size: clamp(44px, 5vw, 62px);
                line-height: 1.08;
                font-weight: 800;
                letter-spacing: 0;
                background: linear-gradient(90deg, #125cff 0%, #7b35f5 82%);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
            }

            .hero-subtitle {
                max-width: 850px;
                margin: 19px auto 0;
                color: #4b5568;
                font-size: 20px;
                line-height: 1.45;
                font-weight: 400;
            }

            .hero-cta {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 18px;
                min-width: 238px;
                height: 56px;
                margin-top: 30px;
                border-radius: 12px;
                color: #ffffff !important;
                font-size: 20px;
                font-weight: 700;
                background: linear-gradient(135deg, #1f67ff 0%, #7834f2 100%);
                box-shadow: 0 16px 34px rgba(58, 84, 245, 0.30);
                transition: transform 180ms ease, box-shadow 180ms ease;
            }

            .hero-cta:hover {
                transform: translateY(-3px);
                box-shadow: 0 22px 46px rgba(58, 84, 245, 0.36);
            }

            .hero-cta span {
                font-size: 28px;
                line-height: 1;
            }

            .module-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(260px, 327px));
                justify-content: center;
                gap: 28px;
                max-width: 1120px;
                margin: 40px auto 0;
            }

            .module-card {
                position: relative;
                display: block;
                min-height: 294px;
                padding: 30px 31px;
                border-radius: 22px;
                text-align: left;
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(232, 235, 243, 0.92);
                box-shadow: 0 24px 65px rgba(22, 30, 50, 0.10);
                cursor: pointer;
                transition: transform 190ms ease, box-shadow 190ms ease, border-color 190ms ease;
            }

            .module-card:hover {
                transform: translateY(-6px);
                border-color: rgba(95, 74, 245, 0.38);
                box-shadow: 0 32px 78px rgba(28, 42, 90, 0.16);
            }

            .icon-bubble {
                width: 78px;
                height: 78px;
                display: grid;
                place-items: center;
                margin-bottom: 34px;
                border-radius: 999px;
                background: linear-gradient(135deg, #ebe5ff 0%, #f3edff 100%);
                color: #6d39f1;
            }

            .icon-bubble.blue {
                background: linear-gradient(135deg, #dce8ff 0%, #eef3ff 100%);
                color: #1768ff;
            }

            .module-icon {
                width: 43px;
                height: 43px;
                display: block;
                overflow: visible;
            }

            .module-icon path,
            .module-icon rect,
            .module-icon line {
                vector-effect: non-scaling-stroke;
            }

            .module-title {
                margin: 0;
                color: #070b13;
                font-size: 21px;
                line-height: 1.2;
                font-weight: 800;
                letter-spacing: 0;
            }

            .module-index {
                margin-right: 7px;
                font-weight: 800;
                background: linear-gradient(120deg, #1262ff 0%, #7c35f6 88%);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
            }

            .module-dot {
                margin-right: 7px;
                color: #6d39f1;
            }

            .module-copy {
                max-width: 245px;
                margin: 17px 0 0;
                color: #4b5568;
                font-size: 17px;
                line-height: 1.65;
                font-weight: 400;
            }

            .arrow-button {
                position: absolute;
                right: 26px;
                bottom: 27px;
                width: 49px;
                height: 49px;
                display: grid;
                place-items: center;
                border-radius: 999px;
                color: #6238f5;
                font-size: 32px;
                line-height: 1;
                background: rgba(255, 255, 255, 0.96);
                border: 1px solid rgba(225, 229, 238, 0.94);
                box-shadow: 0 10px 22px rgba(17, 24, 39, 0.15);
                transition: transform 180ms ease, color 180ms ease;
            }

            .module-card:hover .arrow-button {
                transform: translateX(4px);
                color: #1768ff;
            }

            @media (max-width: 900px) {
                .top-nav {
                    height: auto;
                    padding: 22px;
                    align-items: flex-start;
                    gap: 18px;
                    flex-direction: column;
                }

                .nav-right,
                .nav-links {
                    width: 100%;
                    flex-wrap: wrap;
                    gap: 8px;
                }

                .nav-link {
                    font-size: 14px;
                    padding: 10px 12px;
                }

                .hero {
                    min-height: auto;
                    padding: 36px 20px 52px;
                }

                .hero-subtitle {
                    font-size: 18px;
                }

                .module-grid {
                    grid-template-columns: minmax(0, 1fr);
                }
            }
            </style>
            """
        )
    )


def render_global_style() -> None:
    st.html(_home_style())


def render_home() -> None:
    template = dedent(
        """
        <div class="home-page">
            <nav class="top-nav">
                <a class="brand" href="?page=home">
                    <span class="brand-icon" aria-hidden="true"></span>
                    <span class="brand-text">AI Finance Agent</span>
                </a>

                <div class="nav-right">
                    <div class="nav-links">
                        <a class="nav-link active" href="?page=home">Home</a>
                        <a class="nav-link" href="?page=questionnaire">Questionnaire</a>
                        <a class="nav-link" href="?page=report">Report</a>
                        <a class="nav-link" href="?page=chat">Chat</a>
                        <a class="nav-link" href="?page=scenarios">Scenarios</a>
                    </div>
                    <span class="avatar">KM</span>
                </div>
            </nav>

            <main class="hero">
                <div class="spark-card" aria-hidden="true"></div>
                <h1 class="hero-title">AI Personal Finance Agent</h1>
                <p class="hero-subtitle">
                    Your intelligent financial advisor — personalized to every dimension of your life.
                </p>
                <a class="hero-cta" href="?page=questionnaire">Get started <span>→</span></a>

                <section class="module-grid" aria-label="Finance agent modules">
                    <a class="module-card" href="?page=questionnaire">
                        <div class="icon-bubble" aria-hidden="true">
                            <svg class="module-icon" viewBox="0 0 48 48" fill="none">
                                <rect x="12" y="13" width="24" height="29" rx="4" stroke="currentColor" stroke-width="4"/>
                                <path d="M19 12h10l2 6H17l2-6z" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
                                <line x1="18" y1="27" x2="30" y2="27" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
                                <line x1="18" y1="35" x2="28" y2="35" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
                            </svg>
                        </div>
                        <h2 class="module-title"><span class="module-index">01</span><span class="module-dot">·</span>Questionnaire</h2>
                        <p class="module-copy">Fill in your full financial profile across 5 steps.</p>
                        <span class="arrow-button">→</span>
                    </a>

                    <a class="module-card" href="?page=report">
                        <div class="icon-bubble blue" aria-hidden="true">
                            <svg class="module-icon" viewBox="0 0 48 48" fill="none">
                                <rect x="9" y="27" width="8" height="13" rx="3" fill="currentColor"/>
                                <rect x="20" y="19" width="8" height="21" rx="3" fill="currentColor"/>
                                <rect x="31" y="10" width="8" height="30" rx="3" fill="currentColor"/>
                            </svg>
                        </div>
                        <h2 class="module-title"><span class="module-index">02</span><span class="module-dot">·</span>Analyze</h2>
                        <p class="module-copy">Get a personalized financial health score and plan.</p>
                        <span class="arrow-button">→</span>
                    </a>

                    <a class="module-card" href="?page=chat">
                        <div class="icon-bubble" aria-hidden="true">
                            <svg class="module-icon" viewBox="0 0 48 48" fill="none">
                                <path d="M24 10c-9.4 0-17 6.1-17 13.6 0 4.5 2.8 8.5 7.1 10.9l-1.5 6.1 7-3.8c1.4.3 2.9.4 4.4.4 9.4 0 17-6.1 17-13.6S33.4 10 24 10z" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <h2 class="module-title"><span class="module-index">03</span><span class="module-dot">·</span>Chat Advisor</h2>
                        <p class="module-copy">Ask “Should I buy this?” and get context-aware advice.</p>
                        <span class="arrow-button">→</span>
                    </a>
                </section>
            </main>
        </div>
        """
    )
    components.html(
        _compact_html(_home_style() + template),
        height=900,
        scrolling=False,
    )
