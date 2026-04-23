"""
colosseum.py – Main Streamlit application for Synapse AI Arena.
Integrates models, personas, metrics, judge, history, and export.
"""

import streamlit as st
import pandas as pd

from utils import cfg, export_battle_markdown, export_battle_pdf_bytes
from models import list_available_models, check_ollama_health, run_battle, stream_response
from personas import get_persona_names, resolve_persona, CUSTOM_PERSONA_KEY, BUILTIN_PERSONAS
from metrics import compute_metrics
from judge import get_judge_verdict
from history import save_battle, get_leaderboard, get_all_battles, clear_history


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=cfg("app.page_title", "⚔️ Synapse-AI-Arena"),
    layout=cfg("app.layout", "wide"),
)
st.title(cfg("app.title", "⚔️ Synapse AI Arena"))


# ── Session state defaults ────────────────────────────────────────────────────

_DEFAULTS = {
    "response_a": "",
    "response_b": "",
    "time_a": 0.0,
    "time_b": 0.0,
    "original_prompt": "",
    "original_persona": "",
    "battle_winner": "",
    "judge_verdict": "",
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Ollama health check ──────────────────────────────────────────────────────

healthy, health_msg = check_ollama_health()
if not healthy:
    st.error(
        f"🚨 **Ollama is not reachable.** Make sure the Ollama service is running.\n\n"
        f"Details: {health_msg}"
    )
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Battle Config")

# Dynamic model listing
fallback = cfg("ollama.fallback_models", ["llama3", "mistral", "gemma:2b"])
judge_model_name = cfg("judge.model", "qwen2.5")
available_models = list_available_models(fallback=fallback)

# Filter out the dedicated judge model so it cannot be selected as a competitor
# Compare base names (strip :tag suffix) to handle e.g. "qwen2.5:latest" vs "qwen2.5"
def _base_name(model: str) -> str:
    return model.split(":")[0]

available_models = [m for m in available_models if _base_name(m) != _base_name(judge_model_name)]

if not available_models:
    st.sidebar.error("No models found. Pull a model with `ollama pull <name>`.")
    st.stop()

model_a = st.sidebar.selectbox("Model A", available_models, index=0)
model_b = st.sidebar.selectbox(
    "Model B", available_models, index=min(1, len(available_models) - 1)
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"⚖️ **Judge Model:** `{judge_model_name}`")
st.sidebar.caption("The judge is a dedicated model that cannot be selected as a competitor to ensure impartial evaluation.")

st.sidebar.markdown("---")

# Persona selection
selected_persona = st.sidebar.selectbox("Battle Persona", get_persona_names())
custom_persona_text = ""
if selected_persona == CUSTOM_PERSONA_KEY:
    custom_persona_text = st.sidebar.text_area(
        "Enter your custom system prompt:", height=100
    )

system_prompt = resolve_persona(selected_persona, custom_persona_text)

st.sidebar.markdown("---")

# Generation parameters
st.sidebar.subheader("🎛️ Generation Parameters")
temperature = st.sidebar.slider(
    "Temperature", 0.0, 2.0, cfg("defaults.temperature", 0.7), 0.05
)
top_p = st.sidebar.slider(
    "Top-P", 0.0, 1.0, cfg("defaults.top_p", 0.9), 0.05
)
num_ctx = st.sidebar.select_slider(
    "Context Length", options=[512, 1024, 2048, 4096, 8192],
    value=cfg("defaults.num_ctx", 2048),
)

st.sidebar.markdown("---")

# Streaming toggle
use_streaming = st.sidebar.checkbox("🔴 Stream responses live", value=False)


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_arena, tab_leaderboard, tab_history = st.tabs(
    ["🏟️ Arena", "🏆 Leaderboard", "📜 History"]
)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 – Arena
# ══════════════════════════════════════════════════════════════════════════════

with tab_arena:
    prompt = st.text_area("Enter your prompt for the duel:", height=150)
    fight_btn = st.button("⚔️ FIGHT!", type="primary", use_container_width=True)

    if model_a == model_b:
        st.info("ℹ️ Both sides use the same model – it's a mirror match!")

    if fight_btn and not prompt:
        st.warning("Please enter a prompt to start the fight.")

    if fight_btn and prompt:
        # Persist the original prompt & persona so the judge uses them later
        st.session_state.original_prompt = prompt
        st.session_state.original_persona = system_prompt

        col1, col2 = st.columns(2)

        gen_kwargs = dict(
            temperature=temperature,
            top_p=top_p,
            num_ctx=num_ctx,
        )

        if use_streaming:
            # ── Streaming mode ────────────────────────────────────────────
            with col1:
                st.subheader(f"🅰️ {model_a}")
                placeholder_a = st.empty()
                full_a = ""
                elapsed_a = 0.0
                for chunk, elapsed_a in stream_response(
                    model_a, prompt, system_prompt, **gen_kwargs
                ):
                    full_a += chunk
                    placeholder_a.markdown(full_a + "▌")
                placeholder_a.markdown(full_a)

            with col2:
                st.subheader(f"🅱️ {model_b}")
                placeholder_b = st.empty()
                full_b = ""
                elapsed_b = 0.0
                for chunk, elapsed_b in stream_response(
                    model_b, prompt, system_prompt, **gen_kwargs
                ):
                    full_b += chunk
                    placeholder_b.markdown(full_b + "▌")
                placeholder_b.markdown(full_b)

            resp_a_text, time_a = full_a, elapsed_a
            resp_b_text, time_b = full_b, elapsed_b
            err_a = err_b = None
        else:
            # ── Parallel (blocking) mode ──────────────────────────────────
            with st.spinner("Both models are generating in parallel…"):
                resp_a, resp_b = run_battle(
                    model_a, model_b, prompt, system_prompt, **gen_kwargs
                )

            resp_a_text, time_a, err_a = resp_a.content, resp_a.elapsed, resp_a.error
            resp_b_text, time_b, err_b = resp_b.content, resp_b.elapsed, resp_b.error

            with col1:
                st.subheader(f"🅰️ {model_a}")
                if err_a:
                    st.error(f"Error: {err_a}")
                else:
                    st.markdown(resp_a_text)

            with col2:
                st.subheader(f"🅱️ {model_b}")
                if err_b:
                    st.error(f"Error: {err_b}")
                else:
                    st.markdown(resp_b_text)

        # ── Metrics ───────────────────────────────────────────────────────
        if not err_a and not err_b:
            m_a = compute_metrics(resp_a_text)
            m_b = compute_metrics(resp_b_text)

            with col1:
                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("⏱ Time", f"{time_a:.2f}s")
                mc2.metric("📖 Reading Ease", f"{m_a.reading_ease}")
                mc3.metric("🔢 Words", f"{m_a.word_count}")
                mc4, mc5, mc6 = st.columns(3)
                mc4.metric("🎓 Grade Level", f"{m_a.grade_level}")
                mc5.metric("😊 Sentiment", f"{m_a.sentiment_polarity:+.2f}")
                mc6.metric("📐 Subjectivity", f"{m_a.sentiment_subjectivity:.2f}")

            with col2:
                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("⏱ Time", f"{time_b:.2f}s")
                mc2.metric("📖 Reading Ease", f"{m_b.reading_ease}")
                mc3.metric("🔢 Words", f"{m_b.word_count}")
                mc4, mc5, mc6 = st.columns(3)
                mc4.metric("🎓 Grade Level", f"{m_b.grade_level}")
                mc5.metric("😊 Sentiment", f"{m_b.sentiment_polarity:+.2f}")
                mc6.metric("📐 Subjectivity", f"{m_b.sentiment_subjectivity:.2f}")

            # Speed winner tag
            if time_a < time_b:
                with col1:
                    st.success(f"⚡ Faster: {model_a} by {time_b - time_a:.2f}s")
            elif time_b < time_a:
                with col2:
                    st.success(f"⚡ Faster: {model_b} by {time_a - time_b:.2f}s")

            # Save to session state
            st.session_state.response_a = resp_a_text
            st.session_state.response_b = resp_b_text
            st.session_state.time_a = time_a
            st.session_state.time_b = time_b

    # ── AI Judge ──────────────────────────────────────────────────────────
    st.markdown("---")
    if st.session_state.response_a and st.session_state.response_b:
        if st.button("⚖️ Ask the AI Judge"):
            with st.spinner("The Judge is deliberating…"):
                verdict_resp = get_judge_verdict(
                    question=st.session_state.original_prompt,
                    persona=st.session_state.original_persona,
                    model_a=model_a,
                    response_a=st.session_state.response_a,
                    model_b=model_b,
                    response_b=st.session_state.response_b,
                    judge_model=cfg("judge.model", "llama3"),
                    judge_system_prompt=cfg("judge.system_prompt", "You are a fair judge."),
                )
            if verdict_resp.error:
                st.error(f"Judge error: {verdict_resp.error}")
            else:
                st.session_state.judge_verdict = verdict_resp.content
                st.info(verdict_resp.content)

                # Determine winner from verdict
                verdict_text = verdict_resp.content.upper()
                if "TIE" in verdict_text:
                    winner = "TIE"
                elif model_a.upper() in verdict_text.split("WINNER")[1] if "WINNER" in verdict_text else "":
                    winner = model_a
                else:
                    winner = model_b
                st.session_state.battle_winner = winner

        # ── Save & Export ─────────────────────────────────────────────────
        if st.session_state.judge_verdict:
            exp_col1, exp_col2, exp_col3 = st.columns(3)

            with exp_col1:
                if st.button("💾 Save to History"):
                    save_battle(
                        db_path=cfg("history.db_path", "battle_history.json"),
                        prompt=st.session_state.original_prompt,
                        persona=st.session_state.original_persona,
                        model_a=model_a,
                        response_a=st.session_state.response_a,
                        time_a=st.session_state.time_a,
                        model_b=model_b,
                        response_b=st.session_state.response_b,
                        time_b=st.session_state.time_b,
                        winner=st.session_state.battle_winner,
                        judge_verdict=st.session_state.judge_verdict,
                    )
                    st.success("Battle saved!")

            with exp_col2:
                md_report = export_battle_markdown(
                    prompt=st.session_state.original_prompt,
                    persona=st.session_state.original_persona,
                    model_a=model_a,
                    response_a=st.session_state.response_a,
                    time_a=st.session_state.time_a,
                    model_b=model_b,
                    response_b=st.session_state.response_b,
                    time_b=st.session_state.time_b,
                    winner=st.session_state.battle_winner,
                    judge_verdict=st.session_state.judge_verdict,
                )
                st.download_button(
                    "📄 Download Markdown",
                    data=md_report,
                    file_name="battle_report.md",
                    mime="text/markdown",
                )

            with exp_col3:
                pdf_bytes = export_battle_pdf_bytes(
                    prompt=st.session_state.original_prompt,
                    persona=st.session_state.original_persona,
                    model_a=model_a,
                    response_a=st.session_state.response_a,
                    time_a=st.session_state.time_a,
                    model_b=model_b,
                    response_b=st.session_state.response_b,
                    time_b=st.session_state.time_b,
                    winner=st.session_state.battle_winner,
                    judge_verdict=st.session_state.judge_verdict,
                )
                if pdf_bytes:
                    st.download_button(
                        "📕 Download PDF",
                        data=pdf_bytes,
                        file_name="battle_report.pdf",
                        mime="application/pdf",
                    )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 – Leaderboard
# ══════════════════════════════════════════════════════════════════════════════

with tab_leaderboard:
    st.header("🏆 Model Leaderboard")
    db_path = cfg("history.db_path", "battle_history.json")
    board = get_leaderboard(db_path)

    if board:
        rows = []
        for model, stats in board.items():
            win_rate = (
                stats["wins"] / stats["battles"] * 100 if stats["battles"] else 0
            )
            rows.append(
                {
                    "Model": model,
                    "Battles": stats["battles"],
                    "Wins": stats["wins"],
                    "Losses": stats["losses"],
                    "Ties": stats["ties"],
                    "Win Rate (%)": round(win_rate, 1),
                }
            )
        df = pd.DataFrame(rows).sort_values("Win Rate (%)", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Bar chart
        st.bar_chart(df.set_index("Model")[["Wins", "Losses", "Ties"]])
    else:
        st.info("No battles recorded yet. Go fight in the Arena!")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 – History
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    st.header("📜 Battle History")
    db_path = cfg("history.db_path", "battle_history.json")
    records = get_all_battles(db_path)

    if records:
        for i, rec in enumerate(records):
            with st.expander(
                f"#{i+1}  |  {rec['model_a']} vs {rec['model_b']}  |  "
                f"Winner: {rec.get('winner', '?')}  |  {rec.get('timestamp', '')[:19]}"
            ):
                st.markdown(f"**Prompt:** {rec['prompt']}")
                st.markdown(f"**Persona:** {rec.get('persona', 'N/A')}")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"### {rec['model_a']}  ({rec['time_a']:.2f}s)")
                    st.markdown(rec["response_a"])
                with c2:
                    st.markdown(f"### {rec['model_b']}  ({rec['time_b']:.2f}s)")
                    st.markdown(rec["response_b"])
                if rec.get("judge_verdict"):
                    st.info(rec["judge_verdict"])

        if st.button("🗑️ Clear All History"):
            clear_history(db_path)
            st.rerun()
    else:
        st.info("No battles recorded yet.")
