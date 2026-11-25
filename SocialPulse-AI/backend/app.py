import os
import json
import random
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Serve frontend from ../frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

@app.route('/')
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ── IBM Watsonx config ──────────────────────────────────────────────────────
WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL_ID   = os.getenv("WATSONX_MODEL_ID", "ibm/granite-13b-instruct-v2")

DEMO_MODE = not (WATSONX_API_KEY and WATSONX_PROJECT_ID)

_iam_token_cache = {"token": None, "expires_at": 0}

def get_iam_token():
    """Fetch / cache an IAM bearer token."""
    if _iam_token_cache["token"] and time.time() < _iam_token_cache["expires_at"] - 60:
        return _iam_token_cache["token"]
    import urllib.request, urllib.parse
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": WATSONX_API_KEY
    }).encode()
    req = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read())
    _iam_token_cache["token"]      = result["access_token"]
    _iam_token_cache["expires_at"] = time.time() + int(result.get("expires_in", 3600))
    return _iam_token_cache["token"]


def call_granite(prompt: str, max_tokens: int = 800) -> str:
    """Call IBM Granite via watsonx.ai. Falls back to demo string on any error."""
    if DEMO_MODE:
        return None  # caller will use demo fallback

    try:
        import urllib.request
        token = get_iam_token()
        url   = f"{WATSONX_URL}/ml/v1/text/generation?version=2023-05-29"
        body  = json.dumps({
            "model_id": WATSONX_MODEL_ID,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": max_tokens,
                "stop_sequences": ["###"]
            },
            "project_id": WATSONX_PROJECT_ID
        }).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        return result["results"][0]["generated_text"].strip()
    except Exception as e:
        app.logger.error(f"Granite error: {e}")
        return None


# ── Sample Data ─────────────────────────────────────────────────────────────
SAMPLE_WEEKLY = [
    {"day": "Mon", "instagram": 4200, "youtube": 8100, "linkedin": 1800, "facebook": 3100, "twitter": 2900},
    {"day": "Tue", "instagram": 5100, "youtube": 7600, "linkedin": 2200, "facebook": 2800, "twitter": 3400},
    {"day": "Wed", "instagram": 4800, "youtube": 9200, "linkedin": 2600, "facebook": 3300, "twitter": 4100},
    {"day": "Thu", "instagram": 6300, "youtube": 8800, "linkedin": 3100, "facebook": 3700, "twitter": 3800},
    {"day": "Fri", "instagram": 7200, "youtube": 11200, "linkedin": 2900, "facebook": 4100, "twitter": 5200},
    {"day": "Sat", "instagram": 8900, "youtube": 14100, "linkedin": 1900, "facebook": 5200, "twitter": 6100},
    {"day": "Sun", "instagram": 7600, "youtube": 12300, "linkedin": 1500, "facebook": 4800, "twitter": 5500},
]

PLATFORM_PERF = [
    {"platform": "Instagram", "reach": 48200, "engagement": 6.8, "followers": 24300, "posts": 14},
    {"platform": "YouTube",   "reach": 92400, "engagement": 4.2, "followers": 51200, "posts": 6},
    {"platform": "LinkedIn",  "reach": 18700, "engagement": 5.1, "followers": 9800,  "posts": 10},
    {"platform": "Facebook",  "reach": 31500, "engagement": 3.4, "followers": 18400, "posts": 12},
    {"platform": "X (Twitter)","reach": 29100, "engagement": 2.9, "followers": 15700, "posts": 28},
]

RECENT_POSTS = [
    {"post": "10 AI tools that will replace your team 🤖", "platform": "LinkedIn",  "reach": 12400, "likes": 847,  "comments": 213, "shares": 391, "sentiment": "Positive"},
    {"post": "POV: You discovered the morning routine that changed everything",     "platform": "Instagram", "reach": 8900,  "likes": 1203, "comments": 89,  "shares": 42,  "sentiment": "Positive"},
    {"post": "Why your startup will fail (and how to fix it)", "platform": "YouTube",   "reach": 34200, "likes": 2814, "comments": 476, "shares": 821, "sentiment": "Mixed"},
    {"post": "Thread: The brutal truth about passive income 🧵","platform": "X",         "reach": 7200,  "likes": 492,  "comments": 128, "shares": 267, "sentiment": "Neutral"},
    {"post": "Behind the scenes of building a 6-figure newsletter","platform": "Facebook",  "reach": 5600,  "likes": 318,  "comments": 54,  "shares": 89,  "sentiment": "Positive"},
]

TRENDING_HASHTAGS = [
    {"tag": "#AITools",        "volume": 2400000, "growth": "+142%", "relevance": 97},
    {"tag": "#CreatorEconomy", "volume": 890000,  "growth": "+89%",  "relevance": 91},
    {"tag": "#PassiveIncome",  "volume": 1200000, "growth": "+67%",  "relevance": 84},
    {"tag": "#StartupLife",    "volume": 760000,  "growth": "+55%",  "relevance": 78},
    {"tag": "#ContentStrategy","volume": 420000,  "growth": "+48%",  "relevance": 88},
    {"tag": "#LinkedInGrowth", "volume": 310000,  "growth": "+41%",  "relevance": 82},
    {"tag": "#DigitalNomad",   "volume": 980000,  "growth": "+37%",  "relevance": 73},
    {"tag": "#SideHustle",     "volume": 1500000, "growth": "+29%",  "relevance": 76},
]

TRENDS = [
    {"name": "AI-Generated Short-Form Video",  "hashtags": ["#AIVideo","#ShortForm","#Reels"],       "momentum": 94, "niche": "Tech / Creator",     "growth": "+218%", "angle": "Show AI tools creating content in real-time"},
    {"name": "Authenticity Over Perfection",   "hashtags": ["#RealTalk","#Authentic","#BehindScenes"],"momentum": 87, "niche": "Lifestyle / Brand",   "growth": "+156%", "angle": "Raw, unfiltered behind-the-scenes content"},
    {"name": "AI Productivity Stacks",         "hashtags": ["#AITools","#Productivity","#WorkSmart"], "momentum": 91, "niche": "Business / SaaS",     "growth": "+189%", "angle": "Compare tools in a 60-second speed test"},
    {"name": "Creator Business Transparency",  "hashtags": ["#IncomeReport","#Transparency"],         "momentum": 78, "niche": "Creator / Finance",   "growth": "+134%", "angle": "Monthly revenue breakdown with real numbers"},
    {"name": "Silent Walking Challenges",      "hashtags": ["#SilentWalk","#Mindfulness"],            "momentum": 72, "niche": "Health / Wellness",   "growth": "+98%",  "angle": "Personal reflection and mental clarity"},
    {"name": "B2B LinkedIn Storytelling",      "hashtags": ["#LinkedInStory","#B2BMarketing"],        "momentum": 83, "niche": "B2B / Professional",  "growth": "+145%", "angle": "Turn client wins into narrative-style posts"},
    {"name": "Micro-SaaS Launch Stories",      "hashtags": ["#MicroSaaS","#Buildinpublic"],           "momentum": 86, "niche": "Tech / Startup",      "growth": "+167%", "angle": "Document launch day with metrics"},
    {"name": "Personal Finance Reframes",      "hashtags": ["#MoneyMindset","#FinanceTips"],          "momentum": 79, "niche": "Finance / Self-help",  "growth": "+112%", "angle": "Counter-intuitive money advice with data"},
]

COMPETITORS = [
    {"name": "GrowthHQ",      "niche": "Creator Tools",      "followers": 128000, "eng_rate": 7.2, "top_formats": ["Carousels","Short Video","Threads"], "growth": "+34%", "platform": "Instagram"},
    {"name": "ContentOS",     "niche": "Content Strategy",   "followers": 94500,  "eng_rate": 5.8, "top_formats": ["Long-form","Newsletters","LinkedIn"], "growth": "+28%", "platform": "LinkedIn"},
    {"name": "ViralVault",    "niche": "Viral Content",       "followers": 215000, "eng_rate": 9.1, "top_formats": ["Memes","Reels","TikTok Duets"],      "growth": "+61%", "platform": "TikTok"},
    {"name": "BrandAI Studio","niche": "AI for Brands",       "followers": 67200,  "eng_rate": 6.4, "top_formats": ["AI Demos","Case Studies","Webinars"], "growth": "+47%", "platform": "YouTube"},
    {"name": "PulseCreative", "niche": "Social Analytics",    "followers": 41800,  "eng_rate": 4.9, "top_formats": ["Data Stories","Reports","Twitter"],   "growth": "+19%", "platform": "X"},
]


# ── Demo AI Responses ────────────────────────────────────────────────────────
def demo_strategy(niche, audience, goal, platform, tone):
    return {
        "demo_mode": True,
        "strategy": f"[DEMO MODE — not generated by IBM Granite]\n\nFor a {tone} {niche} creator targeting {audience} on {platform}, focus on educational value-first content that positions you as the go-to authority. Lead with data-backed insights to earn trust quickly.",
        "trending_topics": [
            f"Behind-the-scenes of building a {niche} brand",
            f"Top 5 mistakes {audience} make with {niche}",
            f"How AI is changing {niche} in 2025",
            f"My honest {niche} income report",
            f"The {niche} framework nobody talks about"
        ],
        "hashtags": [f"#{niche.replace(' ','')}Tips", "#ContentStrategy", "#CreatorEconomy", f"#{platform}Growth", "#AIContent"],
        "formats": ["Short-form video (60s)", "Educational carousels", "Data-driven threads", "Behind-the-scenes vlogs", "Weekly newsletter"],
        "schedule": {"Mon": "Educational carousel", "Wed": "Short-form video", "Fri": "Engagement thread", "Sun": "Long-form story"},
        "opportunities": [f"Gap in {niche} content for {audience}", "AI tool integration demos trending", "Long-form explainers underserved on {platform}"],
        "recommendations": [
            "Post within the first hour of peak audience activity",
            "Repurpose top-performing content across platforms",
            "Use pattern-interrupt hooks in the first 3 seconds",
            "Collaborate with micro-creators in adjacent niches",
            "Build a weekly series to train the algorithm"
        ]
    }


def demo_content(platform, topic, tone, content_type):
    hooks = [
        f"Nobody told you this about {topic} — until now.",
        f"Stop doing {topic} wrong. Here's what actually works:",
        f"I spent 90 days testing {topic} so you don't have to.",
    ]
    return {
        "demo_mode": True,
        "hook": random.choice(hooks),
        "caption": f"[DEMO MODE — not generated by IBM Granite]\n\nMost people approach {topic} the wrong way.\n\nAfter months of testing, here's the {tone} take that actually moved the needle for me:\n\n✅ Focus on value first\n✅ Use data to back your claims\n✅ End with a clear CTA\n\nThe creators winning on {platform} right now all share one thing in common — they're consistent, genuine, and strategic. This {content_type} is your starting point.\n\nSave this. You'll need it.",
        "hashtags": [f"#{topic.replace(' ','')}","#ContentCreation",f"#{platform}Tips","#CreatorEconomy","#GrowthHacks"],
        "cta": f"Which of these {topic} tips surprised you most? Drop a comment 👇",
        "alternate": f"[DEMO MODE — not generated by IBM Granite]\n\nHot take: Everything you've heard about {topic} is outdated.\n\nHere's the {tone} 2025 playbook for {platform} that's actually working right now 🧵"
    }


def demo_sentiment(text):
    words = text.lower().split()
    pos_words = {"love","great","amazing","awesome","fantastic","excellent","good","best","wonderful","helpful","brilliant"}
    neg_words = {"hate","terrible","awful","bad","worst","horrible","poor","useless","disappointing","broken","slow"}
    pos = sum(1 for w in words if w.strip(".,!?") in pos_words)
    neg = sum(1 for w in words if w.strip(".,!?") in neg_words)
    total = max(pos + neg, 1)
    pos_pct = round(pos / total * 100)
    neg_pct = round(neg / total * 100)
    neu_pct = 100 - pos_pct - neg_pct
    return {
        "demo_mode": True,
        "positive": pos_pct, "negative": neg_pct, "neutral": neu_pct,
        "themes": ["Product quality", "Customer experience", "Pricing value", "Support response time"],
        "concerns": ["Delivery speed mentioned", "Onboarding complexity flagged", "Feature requests noted"],
        "recommendations": [
            "Acknowledge positive feedback publicly to amplify social proof",
            "Address delivery concerns within 24 hours in comments",
            "Create FAQ content around the most repeated questions",
            "Pin top positive testimonials as social proof"
        ]
    }


def demo_competitor_analysis():
    return {
        "demo_mode": True,
        "opportunities": [
            "Long-form educational content is underserved across all tracked competitors",
            "AI transparency and 'how-it-works' explainers are a clear gap",
            "Competitor newsletters lag behind — an email audience represents untapped owned media",
            "Live Q&A and community building is absent from all competitor strategies"
        ],
        "weaknesses": [
            "ViralVault's engagement spikes around memes but drops sharply for product posts — low purchase intent",
            "GrowthHQ relies heavily on Instagram carousels with minimal video — vulnerable to Reels algorithm shift",
            "ContentOS publishes infrequently (< 2x/week), creating consistency gaps you can exploit",
            "BrandAI Studio's YouTube watch time is good but their short-form repurposing is minimal"
        ],
        "content_gaps": [
            "No competitor publishes case studies with real creator income data",
            "AI tool comparison videos are missing from all competitors",
            "Behind-the-scenes of content strategy development is completely absent",
            "Data journalism — turning analytics into stories — is an entirely open lane"
        ],
        "recommendations": [
            "Publish a weekly data-driven industry report (competitors ignore this format)",
            "Build a cross-platform presence — competitors are largely single-platform dependent",
            "Launch a creator community hub to convert followers into engaged members",
            "Target ViralVault's audience with higher-value educational content to convert intent"
        ]
    }


# ── API Routes ───────────────────────────────────────────────────────────────
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    return jsonify({
        "demo_mode": True,
        "kpis": {
            "total_reach":     {"value": "224,900", "change": "+18.4%", "trend": "up"},
            "engagement_rate": {"value": "5.68%",   "change": "+0.9%",  "trend": "up"},
            "followers_growth":{"value": "+3,842",  "change": "+12.1%", "trend": "up"},
            "sentiment_score": {"value": "84/100",  "change": "+6pts",  "trend": "up"},
        },
        "weekly_engagement": SAMPLE_WEEKLY,
        "platform_performance": PLATFORM_PERF,
        "recent_posts": RECENT_POSTS,
        "trending_hashtags": TRENDING_HASHTAGS,
        "sentiment_distribution": {"positive": 61, "neutral": 24, "negative": 15}
    })


@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"demo_mode": True, "trends": TRENDS})


@app.route("/api/competitors", methods=["GET"])
def get_competitors():
    return jsonify({"demo_mode": True, "competitors": COMPETITORS})


@app.route("/api/generate-strategy", methods=["POST"])
def generate_strategy():
    data    = request.json or {}
    niche   = data.get("niche", "content creation")
    audience= data.get("audience", "millennials")
    goal    = data.get("goal", "grow followers")
    platform= data.get("platform", "Instagram")
    tone    = data.get("tone", "professional")

    if DEMO_MODE:
        return jsonify(demo_strategy(niche, audience, goal, platform, tone))

    prompt = f"""You are a world-class social media strategist. Create a detailed content strategy.

Creator niche: {niche}
Target audience: {audience}
Primary goal: {goal}
Main platform: {platform}
Brand tone: {tone}

Provide a JSON response with these exact keys:
- strategy: 2-3 paragraph strategic overview
- trending_topics: list of 5 specific trending topic ideas
- hashtags: list of 5 recommended hashtags (with # symbol)
- formats: list of 5 best content formats for this niche/platform
- schedule: object with days of week as keys and content type as value (Mon-Sun)
- opportunities: list of 3 specific growth opportunities
- recommendations: list of 5 actionable recommendations

Return ONLY valid JSON, no extra text.
###"""

    result = call_granite(prompt, max_tokens=1000)
    if result is None:
        return jsonify(demo_strategy(niche, audience, goal, platform, tone))

    try:
        # Extract JSON from response
        start = result.find("{")
        end   = result.rfind("}") + 1
        parsed = json.loads(result[start:end])
        parsed["demo_mode"] = False
        return jsonify(parsed)
    except Exception:
        fallback = demo_strategy(niche, audience, goal, platform, tone)
        fallback["raw"] = result
        return jsonify(fallback)


@app.route("/api/generate-content", methods=["POST"])
def generate_content():
    data         = request.json or {}
    platform     = data.get("platform", "Instagram")
    topic        = data.get("topic", "productivity")
    tone         = data.get("tone", "casual")
    content_type = data.get("content_type", "caption")
    image_desc   = data.get("image_description", "")

    if DEMO_MODE:
        return jsonify(demo_content(platform, topic, tone, content_type))

    image_context = f"\nImage context provided by user: {image_desc}" if image_desc else ""

    prompt = f"""You are an expert social media copywriter. Create viral {platform} content.

Platform: {platform}
Topic: {topic}
Tone: {tone}
Content type: {content_type}{image_context}

Provide a JSON response with these exact keys:
- hook: attention-grabbing opening line (1-2 sentences)
- caption: full caption with emojis, line breaks, and storytelling (150-300 words)
- hashtags: list of 8 optimized hashtags
- cta: compelling call-to-action
- alternate: a completely different alternate version of the caption (100-150 words)

Return ONLY valid JSON, no extra text.
###"""

    result = call_granite(prompt, max_tokens=900)
    if result is None:
        return jsonify(demo_content(platform, topic, tone, content_type))

    try:
        start  = result.find("{")
        end    = result.rfind("}") + 1
        parsed = json.loads(result[start:end])
        parsed["demo_mode"] = False
        return jsonify(parsed)
    except Exception:
        fallback = demo_content(platform, topic, tone, content_type)
        fallback["raw"] = result
        return jsonify(fallback)


@app.route("/api/analyze-sentiment", methods=["POST"])
def analyze_sentiment():
    data = request.json or {}
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    if DEMO_MODE:
        return jsonify(demo_sentiment(text))

    prompt = f"""You are a social media sentiment analysis expert. Analyze the following comments/text.

Text to analyze:
\"\"\"{text[:2000]}\"\"\"

Provide a JSON response with these exact keys:
- positive: integer percentage (0-100)
- negative: integer percentage (0-100)
- neutral: integer percentage (0-100, must sum to 100 with positive + negative)
- themes: list of 4 common themes found in the text
- concerns: list of 3 audience concerns or issues mentioned
- recommendations: list of 4 actionable recommendations for responding

Return ONLY valid JSON, no extra text.
###"""

    result = call_granite(prompt, max_tokens=600)
    if result is None:
        return jsonify(demo_sentiment(text))

    try:
        start  = result.find("{")
        end    = result.rfind("}") + 1
        parsed = json.loads(result[start:end])
        # Normalize percentages to sum to 100
        total = parsed.get("positive", 0) + parsed.get("negative", 0) + parsed.get("neutral", 0)
        if total != 100 and total > 0:
            parsed["neutral"] = 100 - parsed["positive"] - parsed["negative"]
        parsed["demo_mode"] = False
        return jsonify(parsed)
    except Exception:
        fallback = demo_sentiment(text)
        fallback["raw"] = result
        return jsonify(fallback)


@app.route("/api/analyze-competitors", methods=["POST"])
def analyze_competitors():
    if DEMO_MODE:
        return jsonify(demo_competitor_analysis())

    competitor_summary = json.dumps([
        {"name": c["name"], "followers": c["followers"], "engagement": c["eng_rate"],
         "formats": c["top_formats"], "growth": c["growth"]}
        for c in COMPETITORS
    ], indent=2)

    prompt = f"""You are a competitive intelligence analyst for social media. Analyze this competitor data.

Competitor Data:
{competitor_summary}

Provide a JSON response with these exact keys:
- opportunities: list of 4 specific market opportunities based on competitor gaps
- weaknesses: list of 4 specific competitor weaknesses you can exploit
- content_gaps: list of 4 content types or topics none of the competitors cover well
- recommendations: list of 4 strategic recommendations to outperform these competitors

Return ONLY valid JSON, no extra text.
###"""

    result = call_granite(prompt, max_tokens=800)
    if result is None:
        return jsonify(demo_competitor_analysis())

    try:
        start  = result.find("{")
        end    = result.rfind("}") + 1
        parsed = json.loads(result[start:end])
        parsed["demo_mode"] = False
        return jsonify(parsed)
    except Exception:
        fallback = demo_competitor_analysis()
        fallback["raw"] = result
        return jsonify(fallback)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "model": WATSONX_MODEL_ID if not DEMO_MODE else "demo",
        "timestamp": datetime.utcnow().isoformat()
    })


# ── YouTube Channel Analyzer ─────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YT_API = "https://www.googleapis.com/youtube/v3"


def yt_get(endpoint, params):
    """Make a YouTube Data API v3 request. Returns parsed JSON or raises."""
    import urllib.request, urllib.parse
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY not configured")
    params["key"] = YOUTUBE_API_KEY
    url = f"{YT_API}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def resolve_channel_id(input_str):
    """
    Accept any of:
      - Channel ID (UCxxxxxxxx)
      - @handle  / youtube.com/@handle
      - youtube.com/channel/UCxxxx
      - youtube.com/c/CustomName
      - youtube.com/user/LegacyName
    Returns channel_id string or raises.
    """
    import re, urllib.parse

    s = input_str.strip()

    # Bare channel ID
    if re.match(r'^UC[\w-]{22}$', s):
        return s

    # Extract path from full URL
    if "youtube.com" in s or "youtu.be" in s:
        parsed = urllib.parse.urlparse(s if s.startswith("http") else "https://" + s)
        path = parsed.path.rstrip("/")
        # /channel/UC...
        m = re.match(r'^/channel/(UC[\w-]{22})$', path)
        if m:
            return m.group(1)
        # /@handle
        m = re.match(r'^/@([\w.-]+)$', path)
        if m:
            s = "@" + m.group(1)
        # /c/name or /user/name
        m = re.match(r'^/(?:c|user)/([\w.-]+)$', path)
        if m:
            s = m.group(1)

    # @handle — use search forHandle
    if s.startswith("@"):
        handle = s.lstrip("@")
        data = yt_get("channels", {"part": "id", "forHandle": handle, "maxResults": 1})
        items = data.get("items", [])
        if items:
            return items[0]["id"]
        # Fallback: search
        data = yt_get("search", {"part": "snippet", "type": "channel", "q": s, "maxResults": 1})
        items = data.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
        raise ValueError(f"Channel not found for handle: {s}")

    # Legacy username
    data = yt_get("channels", {"part": "id", "forUsername": s, "maxResults": 1})
    items = data.get("items", [])
    if items:
        return items[0]["id"]

    # Last resort: search
    data = yt_get("search", {"part": "snippet", "type": "channel", "q": s, "maxResults": 1})
    items = data.get("items", [])
    if items:
        return items[0]["snippet"]["channelId"]

    raise ValueError(f"Could not resolve channel: {input_str}")


def classify_video(title, duration_iso):
    """Return 'short' or 'long'. Shorts: duration <= 60s OR #Shorts in title."""
    import re
    if "#shorts" in title.lower() or "#short" in title.lower():
        return "short"
    if duration_iso:
        m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if m:
            h = int(m.group(1) or 0)
            mi = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            total_sec = h * 3600 + mi * 60 + s
            if total_sec <= 62:
                return "short"
    return "long"


@app.route("/api/youtube/analyze", methods=["POST"])
def youtube_analyze():
    if not YOUTUBE_API_KEY:
        return jsonify({"error": "YOUTUBE_API_KEY not set in backend/.env", "quota_error": False}), 503

    data = request.json or {}
    raw_input = (data.get("channel_input") or "").strip()
    if not raw_input:
        return jsonify({"error": "No channel URL or handle provided"}), 400

    try:
        channel_id = resolve_channel_id(raw_input)
    except ValueError as e:
        return jsonify({"error": str(e), "quota_error": False}), 404
    except Exception as e:
        msg = str(e)
        if "quotaExceeded" in msg or "403" in msg:
            return jsonify({"error": "YouTube API quota exceeded. Try again tomorrow.", "quota_error": True}), 429
        return jsonify({"error": f"Failed to resolve channel: {msg}", "quota_error": False}), 400

    try:
        # Channel stats
        ch_data = yt_get("channels", {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id
        })
        if not ch_data.get("items"):
            return jsonify({"error": "Channel not found or is private"}), 404

        ch = ch_data["items"][0]
        snippet = ch.get("snippet", {})
        stats   = ch.get("statistics", {})
        uploads_playlist = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")

        channel_info = {
            "id":           channel_id,
            "name":         snippet.get("title", "Unknown"),
            "description":  snippet.get("description", ""),
            "avatar":       (snippet.get("thumbnails", {}).get("high") or
                             snippet.get("thumbnails", {}).get("default") or {}).get("url", ""),
            "country":      snippet.get("country", ""),
            "published_at": snippet.get("publishedAt", ""),
            "url":          f"https://www.youtube.com/channel/{channel_id}",
            "subscribers":  int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount") else None,
            "total_views":  int(stats.get("viewCount", 0)),
            "video_count":  int(stats.get("videoCount", 0)),
            "hidden_subs":  stats.get("hiddenSubscriberCount", False),
        }

        # Fetch up to 20 recent uploads via playlist
        videos = []
        if uploads_playlist:
            pl_data = yt_get("playlistItems", {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist,
                "maxResults": 20
            })
            video_ids = [
                item["contentDetails"]["videoId"]
                for item in pl_data.get("items", [])
                if item.get("contentDetails", {}).get("videoId")
            ]

            if video_ids:
                vd = yt_get("videos", {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids)
                })
                for v in vd.get("items", []):
                    vs = v.get("statistics", {})
                    vsnip = v.get("snippet", {})
                    duration = v.get("contentDetails", {}).get("duration", "")
                    title = vsnip.get("title", "")
                    thumb = (vsnip.get("thumbnails", {}).get("medium") or
                             vsnip.get("thumbnails", {}).get("default") or {}).get("url", "")
                    view_count = int(vs.get("viewCount", 0))
                    like_count = int(vs.get("likeCount", 0))
                    comment_count = int(vs.get("commentCount", 0))
                    eng_rate = round((like_count + comment_count) / max(view_count, 1) * 100, 2)
                    videos.append({
                        "id":            v["id"],
                        "title":         title,
                        "thumbnail":     thumb,
                        "published_at":  vsnip.get("publishedAt", ""),
                        "views":         view_count,
                        "likes":         like_count,
                        "comments":      comment_count,
                        "duration":      duration,
                        "engagement":    eng_rate,
                        "type":          classify_video(title, duration),
                        "url":           f"https://www.youtube.com/watch?v={v['id']}",
                    })

        return jsonify({"channel": channel_info, "videos": videos})

    except Exception as e:
        msg = str(e)
        if "quotaExceeded" in msg or "403" in msg:
            return jsonify({"error": "YouTube API quota exceeded. Try again tomorrow.", "quota_error": True}), 429
        return jsonify({"error": f"YouTube API error: {msg}", "quota_error": False}), 500


if __name__ == "__main__":
    mode_str = "DEMO MODE (no IBM credentials)" if DEMO_MODE else f"AI MODE ({WATSONX_MODEL_ID})"
    print(f"\nSocialPulse AI Backend starting - {mode_str}")
    print(f"   API available at http://localhost:5000\n")
    app.run(debug=True, port=5000)
