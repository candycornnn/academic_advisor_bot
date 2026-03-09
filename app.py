import streamlit as st
from groq import Groq
import pdfplumber
import io

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="GradGPT", page_icon="🎓", layout="wide")

if "audit_data" not in st.session_state:
    st.session_state.audit_data = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

def extract_pdf_text(uploaded_file):
    text = ""
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def parse_audit(text):
    import re
    data = {
        "raw_text": text,
        "name": "", "student_id": "", "gpa": "",
        "credits_completed": "", "credits_needed": "124", "credits_remaining": "",
        "program": "",
        "completed_courses": [], "in_progress_courses": [], "not_satisfied": [],
    }
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("Name") and ":" in line:
            data["name"] = line.split(":",1)[-1].strip()
        if "GPA:" in line and "completed" in line:
            m = re.search(r'([\d.]+)\s+completed', line)
            if m and data["gpa"] == "":
                data["gpa"] = m.group(1)
        if "Units:" in line and "required" in line and "used" in line and "needed" in line:
            m1 = re.search(r'([\d.]+)\s+required', line)
            m2 = re.search(r'([\d.]+)\s+used', line)
            m3 = re.search(r'([\d.]+)\s+needed', line)
            if m1 and data["credits_needed"] == "124":
                data["credits_needed"] = m1.group(1)
            if m2 and data["credits_completed"] == "":
                data["credits_completed"] = m2.group(1)
            if m3 and data["credits_remaining"] == "":
                data["credits_remaining"] = m3.group(1)

    course_pattern = re.compile(r'((?:Fall|Spr|Sum)\s+\d{4})\s+([A-Z]{2,5})\s+(\w+)\s+(.+?)\s+([A-F][+-]?)\s+([\d.]+)\s+EN')
    ip_pattern = re.compile(r'((?:Fall|Spr|Sum)\s+\d{4})\s+([A-Z]{2,5})\s+(\w+)\s+(.+?)\s+([\d.]+)\s+IP')
    for line in lines:
        m = course_pattern.search(line)
        if m:
            data["completed_courses"].append({
                "term": m.group(1), "subject": m.group(2), "number": m.group(3),
                "title": m.group(4).strip(), "grade": m.group(5), "credits": m.group(6),
            })
        m2 = ip_pattern.search(line)
        if m2:
            data["in_progress_courses"].append({
                "term": m2.group(1), "subject": m2.group(2), "number": m2.group(3),
                "title": m2.group(4).strip(), "credits": m2.group(5),
            })

    not_sat_pattern = re.compile(r'Not Satisfied:\s+(.+)')
    seen = set()
    for line in lines:
        m = not_sat_pattern.search(line)
        if m:
            item = m.group(1).strip()
            if item not in seen and len(item) > 10 and "student" not in item.lower():
                seen.add(item)
                data["not_satisfied"].append(item)

    for line in lines:
        if any(x in line for x in ["BS", "BA", "BFA", "Minor"]) and data["program"] == "":
            if any(x in line for x in ["Computer", "Business", "Engineering", "Education", "Science", "Arts"]):
                data["program"] = line.strip()
    return data

# ─── UPLOAD SCREEN ───────────────────────────────────────────────────────────
if st.session_state.audit_data is None:
    st.title("🎓 GradGPT")
    st.markdown("#### Your AI-powered USM degree advisor")
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Upload Your Degree Audit PDF")
        st.markdown("""
**How to get your PDF from SOAR:**
1. Go to **soar.usm.edu** and log in
2. Navigate to **Student → Degree Works**
3. Click **Print** → Save as PDF
4. Upload below ⬇️
        """)
        uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            with st.spinner("📖 Reading your degree audit..."):
                try:
                    text = extract_pdf_text(uploaded)
                    data = parse_audit(text)
                    st.session_state.audit_data = data
                    st.session_state.pdf_text = text
                    st.session_state.messages = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not read PDF. Make sure it's not a scanned image. Error: {e}")

# ─── MAIN DASHBOARD ──────────────────────────────────────────────────────────
else:
    data = st.session_state.audit_data
    name = data["name"] if data["name"] else "Student"
    program = data["program"] if data["program"] else "USM Degree"

    # Header
    col1, col2 = st.columns([5,1])
    with col1:
        st.title(f"🎓 GradGPT")
        st.markdown(f"**{name}** · {program}")
    with col2:
        st.write("")
        st.write("")
        if st.button("↩️ New Audit"):
            st.session_state.audit_data = None
            st.session_state.messages = []
            st.session_state.pdf_text = ""
            st.rerun()

    # Metrics
    completed = data["credits_completed"] or "—"
    needed = data["credits_needed"] or "124"
    remaining = data["credits_remaining"] or "—"
    gpa = data["gpa"] or "—"
    ip_count = len(data["in_progress_courses"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Credits Completed", completed)
    c2.metric("🔄 In Progress", f"{ip_count} courses")
    c3.metric("📋 Credits Remaining", remaining)
    c4.metric("🎯 GPA", gpa)

    try:
        prog = float(completed) / float(needed)
        st.progress(min(prog, 1.0), text=f"{completed}/{needed} credits ({int(min(prog,1.0)*100)}%)")
    except:
        pass

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "✅ Completed", "🔄 In Progress", "📋 Remaining", "🤖 GradGPT Chat"
    ])

    # ── COMPLETED ────────────────────────────────────────────────────────────
    with tab1:
        courses = data["completed_courses"]
        st.subheader(f"Completed Courses — {len(courses)} total")
        if not courses:
            st.info("No completed courses detected. Try the GradGPT Chat tab to ask about your progress.")
        else:
            search = st.text_input("🔍 Search courses", placeholder="e.g. CSC, Calculus, Fall 2024...")
            terms = {}
            for c in courses:
                t = c["term"]
                if t not in terms:
                    terms[t] = []
                terms[t].append(c)

            for term, tcourses in sorted(terms.items()):
                if search:
                    tcourses = [c for c in tcourses if
                        search.lower() in c["subject"].lower() or
                        search.lower() in c["title"].lower() or
                        search.lower() in c["number"].lower() or
                        search.lower() in term.lower()]
                if not tcourses:
                    continue
                tc = sum(float(c["credits"]) for c in tcourses)
                with st.expander(f"📅 {term} — {len(tcourses)} courses · {tc:.0f} credits"):
                    header = st.columns([2,5,1,1])
                    header[0].markdown("**Code**")
                    header[1].markdown("**Title**")
                    header[2].markdown("**Cr**")
                    header[3].markdown("**Grade**")
                    for c in tcourses:
                        row = st.columns([2,5,1,1])
                        row[0].write(f"{c['subject']} {c['number']}")
                        row[1].write(c["title"])
                        row[2].write(c["credits"])
                        row[3].markdown(f"**{c['grade']}**")

    # ── IN PROGRESS ──────────────────────────────────────────────────────────
    with tab2:
        ip = data["in_progress_courses"]
        st.subheader(f"Currently In Progress — {len(ip)} courses")
        if not ip:
            st.info("No in-progress courses detected in your audit.")
        else:
            header = st.columns([2,5,1])
            header[0].markdown("**Code**")
            header[1].markdown("**Title**")
            header[2].markdown("**Cr**")
            for c in ip:
                row = st.columns([2,5,1])
                row[0].write(f"{c['subject']} {c['number']}")
                row[1].write(c["title"])
                row[2].write(c["credits"])

    # ── REMAINING ────────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Remaining Requirements")
        not_sat = data["not_satisfied"]
        if not not_sat:
            st.success("🎉 No unsatisfied requirements detected!")
        else:
            unique = list(dict.fromkeys([r for r in not_sat if len(r) > 10]))
            st.info(f"**{len(unique)} unsatisfied requirements** found in your audit.")
            for i, req in enumerate(unique[:50], 1):
                st.markdown(f"**{i}.** {req}")
            st.caption("For full details on each requirement, refer to your SOAR Degree Works audit.")

    # ── GRADGPT CHAT ─────────────────────────────────────────────────────────
    with tab4:
        st.subheader("🤖 GradGPT Chat")
        st.caption("I only answer based on your uploaded degree audit. If I don't have the data, I'll tell you.")

        system_prompt = f"""You are GradGPT, a helpful academic advisor chatbot for the University of Southern Mississippi.

IMPORTANT RULES:
1. You ONLY answer based on the degree audit data provided below.
2. If the information is NOT in the audit, respond with: "I don't have that information in your degree audit. Please check SOAR or contact your academic advisor directly."
3. Never make up course schedules, semester availability, building locations, or professor names.
4. Be friendly, concise, and reference specific course codes from the audit.
5. When summarizing progress, use the actual numbers from the audit.

--- STUDENT DEGREE AUDIT (use ONLY this data) ---
{st.session_state.pdf_text[:9000]}
-------------------------------------------------
"""

        # Quick prompts
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if st.button("📊 Summarize my progress", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Give me a clear summary of my degree progress — how many credits done, GPA, what's remaining."})
                st.rerun()
        with qc2:
            if st.button("📋 What do I still need?", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "What requirements do I still need to complete to graduate? List them clearly."})
                st.rerun()
        with qc3:
            if st.button("🔄 What am I taking now?", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "What courses am I currently taking this semester?"})
                st.rerun()

        st.divider()

        # Render all messages cleanly top to bottom
        for msg in st.session_state.messages:
            with st.chat_message("user" if msg["role"] == "user" else "assistant", avatar=("🎓" if msg["role"] == "assistant" else None)):
                st.write(msg["content"])

        # Chat input — always at bottom
        if prompt := st.chat_input("Ask GradGPT about your degree..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant", avatar="🎓"):
                with st.spinner(""):
                    try:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages,
                            max_tokens=800,
                        )
                        reply = response.choices[0].message.content
                    except Exception as e:
                        reply = f"Error: {e}"
                    st.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

        if st.session_state.messages:
            if st.button("🗑️ Clear chat", use_container_width=False):
                st.session_state.messages = []
                st.rerun()