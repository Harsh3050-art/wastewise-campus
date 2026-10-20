import streamlit as st

from services import submissions as sb
from services.auth import require_login, sidebar_user, current_user
from services.reports import photo_abs

st.set_page_config(page_title="Share Creation", layout="wide")
require_login()
sidebar_user()
user = current_user()

STATUS_LABEL = {"pending": "Waiting for review", "approved": "Approved", "rejected": "Not approved"}


def allow_upload():
    try:
        return str(st.secrets.get("ALLOW_UPLOAD", "false")).lower() == "true"
    except Exception:
        return False


st.title("Share what you made")
if user["role"] != "student":
    st.info("Only students can share creations. Admins review them in the Admin Dashboard.")
    st.stop()

n = st.session_state.setdefault("creation_form_n", 0)
flash = st.session_state.pop("creation_flash", None)
if flash:
    st.success(flash)

st.caption("Made something from waste? Share it to earn bigger points. An admin checks every "
           "creation, and points are given only after approval.")
with st.container(border=True):
    st.subheader(f"Today's code: {sb.daily_code()}")
    st.write("Write this number on a piece of paper and keep it visible in photo 2. "
             "It shows the photo was taken today.")
st.caption(f"Rules: photos must be taken now with the camera. You can share up to "
           f"{sb.MAX_PER_DAY} creations in 24 hours and {sb.MAX_PER_WEEK} per week, and each idea "
           f"only once a week. Please keep faces and ID cards out of the photos.")

title = st.text_input("What did you make?", key=f"c_title_{n}", max_chars=80,
                      placeholder="for example: pen stand from a plastic bottle")
materials = st.text_input("Which waste items did you use?", key=f"c_mat_{n}", max_chars=120,
                          placeholder="for example: plastic bottle, tape")
desc = st.text_area("How did you make it? (optional)", key=f"c_desc_{n}", max_chars=300)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Photo 1: the waste item or work in progress**")
    p1 = st.camera_input("Photo 1", key=f"c_p1_{n}", label_visibility="collapsed")
    u1 = (st.file_uploader("Test mode: upload photo 1", type=["jpg", "jpeg", "png"], key=f"c_u1_{n}")
          if allow_upload() else None)
with c2:
    st.markdown("**Photo 2: the finished product (with today's code on paper)**")
    p2 = st.camera_input("Photo 2", key=f"c_p2_{n}", label_visibility="collapsed")
    u2 = (st.file_uploader("Test mode: upload photo 2", type=["jpg", "jpeg", "png"], key=f"c_u2_{n}")
          if allow_upload() else None)

if st.button("Submit for review", type="primary"):
    b1 = p1.getvalue() if p1 else (u1.getvalue() if u1 else None)
    b2 = p2.getvalue() if p2 else (u2.getvalue() if u2 else None)
    ok, msg = sb.create_submission(user["id"], title, materials, desc, b1, b2)
    if ok:
        st.session_state["creation_flash"] = msg
        st.session_state["creation_form_n"] = n + 1  # new widget keys clear the form
        st.rerun()
    else:
        st.error(msg)

st.divider()
st.subheader("My shared creations")
mine = sb.my_submissions(user["id"])
if not mine:
    st.caption("Nothing shared yet.")
for s in mine:
    with st.container(border=True):
        a, b = st.columns([1, 4])
        if s["photo_path"]:
            a.image(photo_abs(s["photo_path"]), width=110)
        b.markdown(f"**{s['idea_title']}**: {STATUS_LABEL.get(s['status'], s['status'])}")
        if s["status"] == "approved":
            b.caption(f"+{s['points_awarded']} points")
        if s["review_note"] and s["status"] == "rejected":
            b.caption(f"Reason: {s['review_note']}")