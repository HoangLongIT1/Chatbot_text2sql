import google.generativeai as genai

GEMINI_API_KEY = "yout_gemini_api_key_here" 

def call_llm(prompt):
    try:
        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel('gemini-2.5-flash')

        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        return f"Error calling Gemini: {str(e)}"

if __name__ == "__main__":
    print(call_llm("Tell me a short joke about computers."))