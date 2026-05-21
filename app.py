"""
ChiLife Agent — Streamlit UI
Run: streamlit run app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from db.database import init_db
from src.agents.lifestyle_agent import LifestyleAgent
from src.models.schemas import Feedback, UserRequest

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChiLife Agent",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Tighten sidebar padding */
  section[data-testid="stSidebar"] > div { padding-top: 1rem; }

  /* Plan card shell */
  .plan-card {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.4rem 1.6rem 1rem;
    margin-bottom: 1.2rem;
    background: #fafafa;
  }
  .plan-card-dark {
    border: 1px solid #333;
    border-radius: 12px;
    padding: 1.4rem 1.6rem 1rem;
    margin-bottom: 1.2rem;
    background: #1e1e1e;
  }

  /* Vibe badge */
  .vibe-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: white;
  }

  /* Confidence bar */
  .conf-bar-bg {
    background: #e8e8e8;
    border-radius: 4px;
    height: 6px;
    width: 100%;
    margin-top: 4px;
  }
  .conf-bar-fill {
    height: 6px;
    border-radius: 4px;
  }

  /* Itinerary step */
  .itinerary-step {
    padding: 6px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.9rem;
  }
  .itinerary-step:last-child { border-bottom: none; }

  /* Venue chip */
  .venue-chip {
    display: inline-block;
    background: #f0f0f0;
    border-radius: 8px;
    padding: 4px 10px;
    margin: 3px 3px 3px 0;
    font-size: 0.82rem;
    color: #333;
  }

  /* Plan number circle */
  .plan-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #1a1a2e;
    color: white;
    font-size: 13px;
    font-weight: 700;
    margin-right: 8px;
    flex-shrink: 0;
  }

  /* Section label */
  .section-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 4px;
  }

  /* Landing feature box */
  .feature-box {
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    height: 100%;
  }
</style>
""", unsafe_allow_html=True)

# ── Init ───────────────────────────────────────────────────────────────────────
init_db()

if "agent" not in st.session_state:
    st.session_state.agent = LifestyleAgent()
if "plan_set" not in st.session_state:
    st.session_state.plan_set = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = set()

AGENT: LifestyleAgent = st.session_state.agent

# ── Constants ─────────────────────────────────────────────────────────────────
NEIGHBORHOODS = [
    "Any", "Logan Square", "Wicker Park", "Lakeview", "Lincoln Park",
    "Pilsen", "West Loop", "River North", "Uptown",
]
VIBES = ["anything", "chill", "energetic", "romantic", "adventurous", "fun", "sophisticated"]
INTERESTS = ["live_music", "comedy", "sports", "coffee", "bars", "restaurants", "museums"]
INTEREST_LABELS = {
    "live_music": "🎵 Live Music", "comedy": "😂 Comedy", "sports": "🏟 Sports",
    "coffee": "☕ Coffee", "bars": "🍸 Bars", "restaurants": "🍽 Restaurants", "museums": "🏛 Museums",
}
FOOD_OPTIONS = ["anything", "mexican", "japanese", "italian", "vegetarian", "burgers", "seafood"]

VIBE_COLORS = {
    "chill": "#4A90D9", "energetic": "#E8453C", "romantic": "#C0546A",
    "adventurous": "#E67E22", "fun": "#27AE60", "sophisticated": "#8E44AD",
    "social": "#16A085", "casual": "#7F8C8D", "anything": "#2C3E50",
}


def _vibe_color(vibe: str) -> str:
    return VIBE_COLORS.get(vibe.lower(), "#2C3E50")


def _confidence_html(score: float) -> str:
    pct = int(score * 100)
    color = "#27AE60" if pct >= 80 else "#E67E22" if pct >= 60 else "#E74C3C"
    return f"""
    <div class="section-label">Match score</div>
    <div class="conf-bar-bg">
      <div class="conf-bar-fill" style="width:{pct}%;background:{color}"></div>
    </div>
    <div style="font-size:0.78rem;color:#888;margin-top:3px">{pct}%</div>
    """


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ ChiLife Agent")
    st.caption("Personal AI lifestyle concierge for Chicago")
    st.divider()

    neighborhood = st.selectbox("Neighborhood", NEIGHBORHOODS)
    date_context = st.selectbox("When?", ["tonight", "this weekend", "saturday", "sunday"])
    vibe = st.selectbox("Vibe", VIBES)

    col_a, col_b = st.columns(2)
    with col_a:
        budget = st.number_input("Budget ($/person)", min_value=10, max_value=300, value=60, step=5)
    with col_b:
        max_travel = st.number_input("Miles", min_value=1, max_value=20, value=5, step=1)

    group_context = st.radio("Going as?", ["solo", "date", "friends"], horizontal=True)
    food_preference = st.selectbox("Food preference", FOOD_OPTIONS)
    energy_level = st.select_slider("Energy", options=["low", "medium", "high"], value="medium")

    st.markdown("**Interests**")
    selected_interests = []
    cols = st.columns(2)
    for i, key in enumerate(INTERESTS):
        with cols[i % 2]:
            if st.checkbox(INTEREST_LABELS[key], value=key in ["restaurants", "bars"], key=f"int_{key}"):
                selected_interests.append(key)

    st.divider()
    generate_btn = st.button("✦ Find My Night", type="primary", use_container_width=True)


# ── Main ───────────────────────────────────────────────────────────────────────
# Header
header_col, badge_col = st.columns([5, 1])
with header_col:
    st.markdown("# Find Your Chicago Night")
    st.caption("3 personalized plans based on your vibe, budget, and the city's best spots.")
with badge_col:
    if st.session_state.plan_set:
        mode = "AI" if st.session_state.plan_set.llm_used else "Rule-Based"
        st.markdown(f"<div style='margin-top:1.2rem;text-align:right'><span style='background:#f0f0f0;padding:4px 10px;border-radius:8px;font-size:12px;color:#555'>{mode}</span></div>", unsafe_allow_html=True)


# ── Generate ───────────────────────────────────────────────────────────────────
if generate_btn:
    request = UserRequest(
        neighborhood=neighborhood,
        date_context=date_context,
        vibe=vibe,
        budget=budget,
        group_context=group_context,
        food_preference=food_preference,
        interests=selected_interests,
        max_travel_miles=float(max_travel),
        energy_level=energy_level,
        user_id="default",
    )
    with st.spinner("Scouting Chicago for you..."):
        st.session_state.plan_set = AGENT.generate_plans(request)
        st.session_state.feedback_given = set()


# ── Plan Cards ─────────────────────────────────────────────────────────────────
if st.session_state.plan_set:
    plans = st.session_state.plan_set.plans

    for idx, plan in enumerate(plans):
        color = _vibe_color(plan.vibe)
        already_rated = plan.plan_id in st.session_state.feedback_given

        # ── Card header ──────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:0.3rem;margin-top:{'0' if idx==0 else '0.8rem'}">
          <span class="plan-num">{idx + 1}</span>
          <span style="font-size:1.25rem;font-weight:700;flex:1">{plan.title}</span>
          <span class="vibe-badge" style="background:{color}">{plan.vibe}</span>
        </div>
        """, unsafe_allow_html=True)

        # ── 4-column meta strip ───────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown('<div class="section-label">Neighborhood</div>', unsafe_allow_html=True)
            st.markdown(f"**{plan.neighborhood}**")
        with m2:
            st.markdown('<div class="section-label">Budget est.</div>', unsafe_allow_html=True)
            st.markdown(f"**${plan.budget_estimate} / person**")
        with m3:
            st.markdown(_confidence_html(plan.confidence_score), unsafe_allow_html=True)
        with m4:
            if plan.weather_note:
                st.markdown('<div class="section-label">Weather</div>', unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:0.85rem'>{plan.weather_note}</span>", unsafe_allow_html=True)

        # ── Summary + why ─────────────────────────────────────────────────────
        st.markdown(f"<p style='margin:0.6rem 0 0.2rem'>{plan.summary}</p>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#f5f8ff;border-left:3px solid {color};padding:6px 12px;"
            f"border-radius:0 6px 6px 0;font-size:0.88rem;color:#444;margin-bottom:0.6rem'>"
            f"<strong>Why this fits:</strong> {plan.why_it_fits}</div>",
            unsafe_allow_html=True,
        )

        # ── Two-column body: itinerary | venues ───────────────────────────────
        left, right = st.columns([3, 2])

        with left:
            st.markdown('<div class="section-label">Itinerary</div>', unsafe_allow_html=True)
            steps_html = "".join(
                f'<div class="itinerary-step">{"→" if i > 0 else "●"} {step}</div>'
                for i, step in enumerate(plan.itinerary)
            )
            st.markdown(steps_html, unsafe_allow_html=True)

        with right:
            if plan.events:
                st.markdown('<div class="section-label">Events</div>', unsafe_allow_html=True)
                for ev in plan.events:
                    st.markdown(
                        f"<div class='venue-chip'>🎟 {ev.name}</div>"
                        f"<div style='font-size:0.78rem;color:#777;margin-bottom:4px'>"
                        f"{ev.venue} · {ev.time} · ${ev.price}</div>",
                        unsafe_allow_html=True,
                    )
            if plan.places:
                st.markdown('<div class="section-label">Venues</div>', unsafe_allow_html=True)
                for pl in plan.places:
                    st.markdown(
                        f"<div class='venue-chip'>📍 {pl.name}</div>"
                        f"<div style='font-size:0.78rem;color:#777;margin-bottom:4px'>"
                        f"{pl.subcategory} · {pl.price_range} · ~${pl.price_avg}/person</div>",
                        unsafe_allow_html=True,
                    )

        # ── Feedback row ──────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        fb1, fb2, fb3, fb4, fb5 = st.columns([1, 1, 2, 2, 2])

        with fb1:
            if st.button("👍", key=f"up_{plan.plan_id}", disabled=already_rated, help="Love it"):
                AGENT.save_feedback(Feedback(
                    plan_id=plan.plan_id, user_id="default", rating="thumbs_up",
                    saved_neighborhood=plan.neighborhood, saved_vibe=plan.vibe,
                ))
                st.session_state.feedback_given.add(plan.plan_id)
                st.rerun()

        with fb2:
            if st.button("👎", key=f"dn_{plan.plan_id}", disabled=already_rated, help="Not for me"):
                AGENT.save_feedback(Feedback(
                    plan_id=plan.plan_id, user_id="default", rating="thumbs_down",
                    disliked_option=plan.title,
                ))
                st.session_state.feedback_given.add(plan.plan_id)
                st.rerun()

        with fb3:
            if st.checkbox(f"Save {plan.neighborhood}", key=f"nb_{plan.plan_id}", disabled=already_rated):
                AGENT.save_feedback(Feedback(
                    plan_id=plan.plan_id, user_id="default", rating="saved",
                    saved_neighborhood=plan.neighborhood,
                ))

        with fb4:
            if st.checkbox(f"Save '{plan.vibe}' vibe", key=f"vb_{plan.plan_id}", disabled=already_rated):
                AGENT.save_feedback(Feedback(
                    plan_id=plan.plan_id, user_id="default", rating="saved",
                    saved_vibe=plan.vibe,
                ))

        with fb5:
            if already_rated:
                st.markdown("<span style='font-size:0.82rem;color:#27AE60'>✓ Feedback saved</span>", unsafe_allow_html=True)

        st.divider()


# ── Landing state ──────────────────────────────────────────────────────────────
else:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🎵", "Live Music", "Concord Music Hall, Empty Bottle, Green Mill, Thalia Hall"),
        ("🍜", "Food & Drink", "West Loop restaurants, Wicker Park cocktail bars, Logan Square breweries"),
        ("😂", "Comedy & Arts", "Second City, Laugh Factory, Pilsen art walks, Uptown poetry slam"),
        ("⚾", "Sports & Events", "Cubs at Wrigley, Blackhawks at the United Center, street markets"),
    ]
    for col, (icon, title, desc) in zip([f1, f2, f3, f4], features):
        with col:
            st.markdown(
                f"<div class='feature-box'>"
                f"<div style='font-size:1.8rem'>{icon}</div>"
                f"<div style='font-weight:700;margin:6px 0 4px'>{title}</div>"
                f"<div style='font-size:0.82rem;color:#666'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    **How it works**

    Set your preferences in the sidebar — neighborhood, vibe, budget, group context, food, and interests.
    Hit **✦ Find My Night** and the agent checks Chicago's weather, filters events and venues, and builds
    3 distinct itineraries tailored to your night. Give feedback to improve future picks.
    """)

    n1, n2, n3, n4 = st.columns(4)
    neighborhoods = [
        ("Logan Square", "Indie bars, breweries, tacos"),
        ("Wicker Park", "Cocktails, dive bars, brunch"),
        ("West Loop", "Restaurant row, Fulton Market"),
        ("Pilsen", "Art, murals, Korean-Polish fusion"),
    ]
    n5, n6, n7, n8 = st.columns(4)
    neighborhoods2 = [
        ("Lakeview", "Wrigley, comedy, rooftop bars"),
        ("Lincoln Park", "Second City, museums, wine"),
        ("River North", "Jazz, ramen, gallery district"),
        ("Uptown", "Green Mill, poetry, jazz history"),
    ]
    for col, (name, desc) in zip([n1, n2, n3, n4], neighborhoods):
        with col:
            st.markdown(f"**{name}**  \n<span style='font-size:0.8rem;color:#777'>{desc}</span>", unsafe_allow_html=True)
    for col, (name, desc) in zip([n5, n6, n7, n8], neighborhoods2):
        with col:
            st.markdown(f"**{name}**  \n<span style='font-size:0.8rem;color:#777'>{desc}</span>", unsafe_allow_html=True)
