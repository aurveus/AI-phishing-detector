# Streamlit front end. Run:  streamlit run app.py
# (comments, not a docstring: Streamlit would print a top-of-file docstring on the page)
import streamlit as st

from phishing_detector import config
from phishing_detector.classifier import PhishingClassifier
from phishing_detector.examples import EXAMPLES
from phishing_detector.model_store import ensure_model
from phishing_detector.signals import defanged_links, find_signals

st.set_page_config(page_title="Phishing Email Detector", page_icon="🎣", layout="centered")

# Everything injected below is fixed text or numbers we format ourselves, never the pasted email.
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; max-width: 820px; }
      .hero h1 { margin: 0; font-size: 2.1rem; }
      .hero p { margin: .3rem 0 1.2rem; color: #9aa3b2; }
      .verdict { border-radius: 14px; padding: 1.1rem 1.3rem; margin: .8rem 0 .4rem; border: 1px solid; }
      .verdict.bad  { background: #3a1417; border-color: #e5484d; }
      .verdict.good { background: #12301f; border-color: #30a46c; }
      .verdict .t { font-size: 1.5rem; font-weight: 700; }
      .verdict .s { color: #c4cad6; margin-top: .15rem; }
      .bar { height: 10px; border-radius: 6px; background: #2a3140; overflow: hidden; margin-top: .8rem; }
      .bar > div { height: 100%; border-radius: 6px; }
      .barlabel { display: flex; justify-content: space-between; color: #9aa3b2; font-size: .8rem; margin-top: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Loading the model. The first start downloads and verifies it (about 257 MB)...")
def load_classifier() -> PhishingClassifier:
    return PhishingClassifier(ensure_model())


def set_example(name: str) -> None:
    st.session_state.email_text = EXAMPLES[name]
    st.session_state.run = True


def clear() -> None:
    st.session_state.email_text = ""
    st.session_state.run = False


# ----- sidebar -------------------------------------------------------------------------------------------
with st.sidebar:
    st.header("About")
    st.write("A DistilBERT language model fine-tuned on about 18,600 labeled emails reads the text and scores how "
             "likely it is to be phishing.")
    st.metric("Accuracy on held-out test emails", "97.5%")
    st.metric("Phishing emails caught", "98.1%")
    st.divider()
    st.subheader("Good to know")
    st.markdown(
        "- Reads **text only**: not headers, attachments or where a link really goes.\n"
        "- Trained on one English dataset; a cleverly reworded scam can slip past.\n"
        "- Your text is processed in memory and **not stored**.\n"
        "- A screening aid, not a guarantee."
    )
    st.caption("[Source code and security review](https://github.com/aurveus/AI-phishing-detector)")

# ----- header --------------------------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>🎣 Phishing Email Detector</h1>'
    "<p>Paste an email and see whether it looks like phishing, and why.</p></div>",
    unsafe_allow_html=True,
)

try:
    classifier = load_classifier()
except Exception:  # offline, blocked download or checksum failure: say so instead of showing a traceback
    st.error("The model could not be loaded. If this is the first start, check your internet connection and try again. "
             "If it keeps failing, the downloaded file did not match its checksum and was refused.")
    st.stop()

# A shareable demo link: ?example=phishing or ?example=safe
demo = st.query_params.get("example")
if demo in EXAMPLES and "email_text" not in st.session_state:
    set_example(demo)

st.session_state.setdefault("email_text", "")
st.session_state.setdefault("run", False)

c1, c2, c3 = st.columns([1.4, 1.4, 1])
c1.button("Try a phishing example", key="ex_phish", on_click=set_example, args=("phishing",), use_container_width=True)
c2.button("Try a safe example", key="ex_safe", on_click=set_example, args=("safe",), use_container_width=True)
c3.button("Clear", key="clear", on_click=clear, use_container_width=True)

text = st.text_area("Email text", key="email_text", height=230, max_chars=config.MAX_INPUT_CHARS,
                    placeholder="Paste the full text of the email here...")

if st.button("Check this email", key="detect", type="primary", use_container_width=True):
    st.session_state.run = True

if st.session_state.run:
    if not text.strip():
        st.warning("Paste some email text first, or try one of the examples above.")
    else:
        try:
            result = classifier.predict(text)
        except ValueError as e:
            st.error(f"Could not check this text: {e}.")
            st.stop()
        score = result["phishing_probability"]
        bad = result["label"] == "Phishing Email"
        confidence = score if bad else 1 - score
        title = "Likely phishing" if bad else "Looks safe"
        sub = (f"The model is {confidence:.0%} sure. Do not click links or reply." if bad
               else f"The model is {confidence:.0%} sure. Stay careful with links and attachments.")
        color = "#e5484d" if bad else "#30a46c"
        st.markdown(
            f'<div class="verdict {"bad" if bad else "good"}"><div class="t">{"⚠️" if bad else "✅"} {title}</div>'
            f'<div class="s">{sub}</div>'
            f'<div class="bar"><div style="width:{score * 100:.1f}%;background:{color}"></div></div>'
            f'<div class="barlabel"><span>Safe</span><span>Phishing score {score:.0%}</span><span>Phishing</span></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        signals = find_signals(text)
        with st.expander("Why? Warning signs found in the text", expanded=bool(signals)):
            if signals:
                for line in signals:
                    st.markdown(f"- {line}")
                links = defanged_links(text)
                if links:
                    st.caption("Links found, made harmless so they cannot be clicked:")
                    st.code("\n".join(links), language=None)
            else:
                st.write("No obvious warning signs such as links, urgency or requests for passwords. "
                         "The verdict above comes from the model.")
            st.caption("These checks are simple hints for your benefit. They are not part of the model's score.")
