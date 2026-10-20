import hmac
from datetime import date

import streamlit as st
from services.auth import signup, login, current_user, sidebar_user, hide_sidebar
from services.bins import get_all_bins
from services.bootstrap import ensure_ready
from services.facts import fact_of_the_day
from services.stats import user_stats, badge_info

WASTE_LABELS = {
    "wet": "Food / wet waste",
    "dry": "Dry waste (paper, wrappers)",
    "recyclable": "Recyclables (bottles, cans)",
    "ewaste": "E-waste (batteries, cables)",
    "hazardous": "Hazardous waste",
}

CHALLENGES = [
    "Carry your own bottle or mug today.",
    "Sort your waste into wet and dry for one full day.",
    "Turn one jar, box or bottle into something useful instead of binning it.",
    "Say no to a single-use plastic bag today.",
    "Use both sides of the paper today.",
    "Pick up one piece of litter and put it in the right bin.",
    "Read the label before you bin something and check if it can be recycled.",
]

st.set_page_config(
    page_title="WasteWise Campus",
    page_icon="♻️",
    layout="wide",
)


# First start: creates the database, loads the bins, builds the simulated
# history and trains the forecast model. It runs once per server start.
@st.cache_resource
def _boot():
    ensure_ready()
    return True


_boot()

st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #14342B, #1B7F4B);
    padding: 28px 32px;
    border-radius: 16px;
    color: white;
    margin-bottom: 18px;
}
.hero h1 {
    color: white;
    margin: 0;
    font-size: 2rem;
}
.hero p {
    color: #d6efe1;
    margin: 6px 0 0 0;
}
.hero ul {
    color: #d6efe1;
    margin-top: 12px;
}
</style>
""", unsafe_allow_html=True)


def get_admin_code():
    try:
        return st.secrets["ADMIN_INVITE_CODE"]
    except Exception:
        return None


user = current_user()

# --------------------------------------------------
# LOGGED-IN HOME PAGE
# --------------------------------------------------
if user:
    sidebar_user(poll=True)

    st.markdown(
        f'<div class="hero"><h1>Welcome, {user["name"]}</h1>'
        '<p>Smart and sustainable waste management for IIT Roorkee</p></div>',
        unsafe_allow_html=True,
    )

    # ADMIN HOME: direct the admin to the control room
    if user["role"] == "admin":
        st.subheader("Waste Management Control Room")
        st.write("Monitor campus bins, fill levels, and operational alerts.")

        st.page_link(
            "pages/6_Admin_Dashboard.py",
            label="Open the Admin Dashboard",
            icon="🛠️",
        )
        st.page_link(
            "pages/1_Campus_Map.py",
            label="Open the Campus Map",
            icon="🗺️",
        )
        st.stop()

    # STUDENT HOME
    s = user_stats(user["id"])
    df = get_all_bins()

    badge, nxt_name, to_go, ratio = badge_info(s["points"])

    clean_pct = (
        (df["fill_pct"] < 80).mean() * 100
        if not df.empty
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1.container(border=True):
        st.metric("Your points", s["points"])

    with c2.container(border=True):
        st.metric("Your rank", f"#{s['rank']}")

    with c3.container(border=True):
        st.metric("Your badge", badge)

    with c4.container(border=True):
        st.metric("Campus cleanliness", f"{clean_pct:.0f}%")

    if nxt_name:
        st.progress(
            ratio,
            text=f"{to_go} points to reach {nxt_name}",
        )
    else:
        st.success("You reached the top badge!")

    left, right = st.columns([1.3, 1], gap="large")

    # WHERE CAN I THROW IT?
    with left:
        with st.container(border=True):
            st.subheader("Where can I throw it?")

            kind = st.selectbox(
                "What kind of waste do you have?",
                list(WASTE_LABELS),
                format_func=WASTE_LABELS.get,
            )

            options = (
                df[df["type"] == kind]
                .sort_values("fill_pct")
                .head(3)
            )

            if options.empty:
                st.info("No bins of this type yet.")

            for _, r in options.iterrows():
                a, b = st.columns([3, 1])

                with a:
                    st.write(
                        f"**{r['name']}**: {r['fill_pct']:.0f}% full"
                    )
                    st.progress(
                        min(max(r["fill_pct"], 0), 100) / 100
                    )

                with b:
                    if st.button(
                        "Show on map",
                        key=f"show_{r['bin_id']}",
                    ):
                        st.session_state["focus_bin"] = r["bin_id"]
                        st.switch_page("pages/1_Campus_Map.py")

            st.caption(
                "These are the emptiest bins of this type. "
                "Find them on the Campus Map."
            )

    # ECO CHALLENGE AND STUDENT ACTIVITY
    with right:
        with st.container(border=True):
            st.subheader("Today's eco challenge")
            st.info(
                CHALLENGES[
                    date.today().toordinal() % len(CHALLENGES)
                ]
            )

        with st.container(border=True):
            st.subheader("Your activity")
            st.write(f"Bins reported: **{s['reports']}**")
            st.write(f"Reuse ideas tried: **{s['ideas']}**")
            st.write(f"Approved creations: **{s['makes']}**")

    # QUICK LINKS
    st.page_link("pages/2_Reuse_Coach.py", label="Ask the Reuse Coach", icon="♻️")
    st.page_link("pages/7_Share_Creation.py", label="Share something you made", icon="📸")
    st.page_link("pages/3_Leaderboard.py", label="Leaderboard", icon="🏆")
    st.page_link("pages/4_Profile.py", label="My profile", icon="👤")
    st.page_link("pages/1_Campus_Map.py", label="Open the campus map", icon="🗺️")

    st.caption("Demo note: bin fill levels are simulated. "
               "Real sensors would write the same readings.")

    st.stop()

# --------------------------------------------------
# LOGIN AND SIGNUP PAGE (no sidebar when logged out)
# --------------------------------------------------
hide_sidebar()

left, right = st.columns([1.1, 1], gap="large")

with left:
    st.markdown("""
    <div class="hero">
        <h1>WasteWise Campus</h1>
        <p>Smart and sustainable waste management for IIT Roorkee</p>
        <ul>
            <li>Campus map with bin fill levels and time to full</li>
            <li>Report bins and track cleaning activity</li>
            <li>Discover reuse ideas and earn eco points</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with right:
    fact = fact_of_the_day()
    if fact:
        with st.container(border=True):
            st.subheader("Did you know?")
            st.write(fact["text"])
            st.caption("Source: " + fact["source"])

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            ident = st.text_input("Email or enrollment ID")
            pw = st.text_input("Password", type="password")

            go = st.form_submit_button(
                "Log in",
                type="primary",
            )

        if go:
            u = login(ident, pw)

            if u:
                st.session_state["user"] = u
                st.rerun()
            else:
                st.error("Wrong ID or password.")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            ident2 = st.text_input(
                "Email or enrollment ID",
                key="signup_ident",
            )
            hostel = st.text_input(
                "Hostel or department (optional)"
            )
            pw1 = st.text_input(
                "Password (min 8 characters)",
                type="password",
                key="pw1",
            )
            pw2 = st.text_input(
                "Confirm password",
                type="password",
                key="pw2",
            )
            code = st.text_input(
                "Admin invite code (waste team only)",
                type="password",
            )

            go2 = st.form_submit_button(
                "Create account",
                type="primary",
            )

        if go2:
            role = "student"

            if code.strip():
                expected = get_admin_code()

                if expected and hmac.compare_digest(
                    code.strip(), expected
                ):
                    role = "admin"
                else:
                    st.error("Invalid admin invite code.")
                    st.stop()

            ok, msg = signup(
                name, ident2, pw1, pw2, hostel, role
            )

            if ok:
                st.success(msg)
            else:
                st.error(msg)