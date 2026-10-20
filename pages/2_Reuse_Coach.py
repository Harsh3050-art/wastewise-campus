import streamlit as st

from services import ai_client, coach
from services.auth import require_login, sidebar_user, current_user
from services.bins import get_all_bins
from services.facts import fact_for
from services.mapview import TYPE_LABEL

st.set_page_config(page_title="Reuse Coach", layout="wide")
require_login()
sidebar_user()
user = current_user()
if user["role"] == "admin":
    st.info("This page is for students.")
    st.stop()
    
AI_ON = ai_client.ai_configured()
EXAMPLES = ["plastic bottle", "newspaper", "glass jar", "tin can", "old t-shirt", "paper cup"]
LEVEL_LABEL = {"easy": "Easy", "medium": "Medium", "creative": "Creative"}
SOURCE_LABEL = {
    "ai": "Answered by AI",
    "cache": "Saved answer from an earlier AI reply",
    "offline": "Saved examples (no AI used)",
}


def pick_example(example):
    st.session_state["coach_item"] = example


st.title("Reuse Coach")
st.caption("Tell me what you are about to throw away and I will suggest what to make from it. "
           "Always read the safety notes.")
if AI_ON:
    st.caption("AI mode is on: type any item or add a photo. AI answers can be wrong.")
else:
    with st.expander("Offline mode: saved ideas are used (no AI key set up)"):
        st.write("I have saved ideas for: " + ", ".join(coach.offline_items()) + ".")
        st.write("I also give bin-it-right advice for batteries, medicines, bulbs and electronics.")

flash = st.session_state.pop("coach_flash", None)
if flash:
    st.success(flash)

cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    c.button(ex, key=f"ex_{ex}", on_click=pick_example, args=(ex,))

item = st.text_input("What do you want to throw away?", key="coach_item",
                     max_chars=coach.MAX_ITEM_CHARS, placeholder="for example: plastic bottle")
photo = None
if AI_ON:
    photo = st.file_uploader("Or add a photo of the item (optional; the photo is used if you add both)",
                             type=["jpg", "jpeg", "png"])
go = st.button("Get reuse ideas", type="primary")

if go:
    img, mime = None, "image/jpeg"
    if photo is not None:
        try:
            img, mime = coach.prepare_photo(photo)
        except ValueError as e:
            st.error(str(e))
            st.stop()
    with st.spinner("Thinking of ideas..."):
        result, source, msg = coach.get_ideas(item, user["id"], img, mime)
    st.session_state["coach_state"] = {"result": result, "source": source, "msg": msg}

state = st.session_state.get("coach_state")
if state:
    res = state["result"]
    if state["msg"]:
        st.info(state["msg"])
    if res:
        st.subheader(res["item"].title())
        m1, m2, m3 = st.columns(3)
        m1.metric("Material", res["material"] or "unknown")
        m2.metric("Recyclable", "Yes" if res["recyclable"] else "No")
        m3.metric("Right bin", TYPE_LABEL[res["correct_bin"]])
        if res["disposal_note"]:
            st.write(res["disposal_note"])
        if not res["reuse_safe"]:
            st.warning("This item is not suitable to reuse. Please put it in the right bin.")

        for i, idea in enumerate(res["ideas"]):
            with st.container(border=True):
                st.markdown(f"**{LEVEL_LABEL[idea['level']]}: {idea['title']}** "
                            f"(about {idea['time_minutes']} min)")
                if idea["materials_needed"]:
                    st.write("You need: " + ", ".join(idea["materials_needed"]))
                for n, step in enumerate(idea["steps"], 1):
                    st.write(f"{n}. {step}")
                if idea["safety_note"]:
                    st.warning("Safety: " + idea["safety_note"])
                if st.button("I will try this", key=f"adopt_{i}"):
                    ok, m = coach.adopt_idea(user["id"], res["item"], idea["title"])
                    st.session_state["coach_flash"] = m
                    st.rerun()
                if res["ideas"]:
                   st.page_link("pages/7_Share_Creation.py", label="Made it? Share it to earn points", icon="📸")



        st.subheader(f"Or bin it right: emptiest {TYPE_LABEL[res['correct_bin']].lower()} bins now")
        bins = get_all_bins()
        options = bins[bins["type"] == res["correct_bin"]].sort_values("fill_pct").head(3)
        if options.empty:
            st.caption("No bins of this type yet.")
        for _, r in options.iterrows():
            a, b = st.columns([3, 1])
            a.write(f"**{r['name']}**: {r['fill_pct']:.0f}% full")
            if b.button("Show on map", key=f"map_{r['bin_id']}"):
                st.session_state["focus_bin"] = r["bin_id"]
                st.switch_page("pages/1_Campus_Map.py")

        fact = fact_for(res["item"])
        if fact:
            st.info("Did you know? " + fact["text"])
            st.caption("Source: " + fact["source"])
        st.caption(SOURCE_LABEL.get(state["source"], ""))