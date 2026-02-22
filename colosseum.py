import streamlit as st
import ollama
import time
import textstat

# --- Page Config ---
st.set_page_config(page_title="⚔️ Synapse-AI-Arena", layout="wide")
st.title("⚔️ Synapse AI Arena")

# --- Session State (Memory) ---
# This keeps the answers on screen when you click "Ask Judge"
if "response_a" not in st.session_state:
    st.session_state.response_a = ""
if "response_b" not in st.session_state:
    st.session_state.response_b = ""
if "time_a" not in st.session_state:
    st.session_state.time_a = 0
if "time_b" not in st.session_state:
    st.session_state.time_b = 0

# --- Feature 1: Personas ---
PERSONAS = {
    "Standard Assistant": "You are a helpful and precise AI assistant.",
    "Angry Pirate": "You are a rude pirate captain from the 1700s. Use slang like 'Yarr', 'Matey', and 'Landlubber'. Be aggressive but helpful.",
    "5-Year-Old": "Explain everything like I am 5 years old. Use simple words and analogies.",
    "Philosopher": "You are a deep thinker. Answer every question with a philosophical twist and a quote from a famous philosopher.",
    "Roast Master": "You are a comedian who loves to roast people. Answer the question but make fun of the user for asking it."
}

# --- Sidebar Controls ---
st.sidebar.title("Combatants")
models_list = ['llama3', 'mistral', 'gemma:2b']
model_a = st.sidebar.selectbox("Select Model A", models_list, index=0)
model_b = st.sidebar.selectbox("Select Model B", models_list, index=1)

st.sidebar.markdown("---")
# New Dropdown for Persona
selected_persona = st.sidebar.selectbox("Select Battle Persona", list(PERSONAS.keys()))
system_prompt = PERSONAS[selected_persona]

# --- The Battle Arena ---
prompt = st.text_area("Enter your prompt for the duel:", height=150)
fight_btn = st.button("FIGHT!", type="primary", use_container_width=True)

def get_model_response(model_name, user_prompt, sys_prompt):
    """
    Sends a prompt AND a system prompt to Ollama.
    """
    start_time = time.time()
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': user_prompt}
        ])
        end_time = time.time()
        elapsed_time = end_time - start_time
        return response['message']['content'], elapsed_time, None
    except Exception as e:
        return None, 0, str(e)

if fight_btn and prompt:
    if model_a == model_b:
        st.warning("⚠️ You have selected the same model for both sides. It's a mirror match!")

    col1, col2 = st.columns(2)

    # --- Battle Logic ---
    
    # Model A Turn
    with col1:
        st.subheader(f"Model A: {model_a}")
        with st.spinner(f"{model_a} is generating ({selected_persona})..."):
            resp_a, time_a, err_a = get_model_response(model_a, prompt, system_prompt)
            
            if err_a:
                st.error(f"Error: {err_a}")
            else:
                st.write(resp_a)
                st.markdown("---")
                st.metric("Time Taken", f"{time_a:.2f}s")
                st.metric("Reading Ease", f"{textstat.flesch_reading_ease(resp_a):.1f}")
                
                # SAVE TO MEMORY
                st.session_state.response_a = resp_a
                st.session_state.time_a = time_a

    # Model B Turn
    with col2:
        st.subheader(f"Model B: {model_b}")
        with st.spinner(f"{model_b} is generating ({selected_persona})..."):
            resp_b, time_b, err_b = get_model_response(model_b, prompt, system_prompt)
            
            if err_b:
                st.error(f"Error: {err_b}")
            else:
                st.write(resp_b)
                st.markdown("---")
                st.metric("Time Taken", f"{time_b:.2f}s")
                st.metric("Reading Ease", f"{textstat.flesch_reading_ease(resp_b):.1f}")
                
                # SAVE TO MEMORY
                st.session_state.response_b = resp_b
                st.session_state.time_b = time_b

    # Winner Logic
    if not err_a and not err_b:
        if time_a < time_b:
            with col1:
                st.success(f"🏆 WINNER: {model_a}")
        elif time_b < time_a:
            with col2:
                st.success(f"🏆 WINNER: {model_b}")

# --- Feature 2: The AI Judge ---
st.markdown("---")

# Only show the button if we have answers in memory
if st.session_state.response_a and st.session_state.response_b:
    if st.button("⚖️ Ask the AI Judge"):
        with st.spinner("The Judge is deliberating..."):
            # We construct a meta-prompt for the judge
            judge_prompt = f"""
            You are an impartial expert judge.
            User Question: "{prompt}"
            
            Model A ({model_a}) Answer: "{st.session_state.response_a}"
            
            Model B ({model_b}) Answer: "{st.session_state.response_b}"
            
            Task: Compare these two answers. Pick the winner based on accuracy, style, and how well they followed the persona instructions. 
            Explain your decision in 2 sentences. Format your answer as: **WINNER:** [Model Name] \n **REASON:** [Reason]
            """
            
            # Use Llama3 as the default judge
            judge_verdict, _, _ = get_model_response('llama3', judge_prompt, "You are a fair judge.")
            
            st.info(judge_verdict)
elif not prompt and fight_btn:
    st.warning("Please enter a prompt to start the fight.")