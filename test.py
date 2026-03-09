from groq import Groq

client = Groq(api_key="your-groq-key-here")


system_prompt = """You are a friendly and knowledgeable academic advisor 
for university students. You help with:
- Course selection and planning
- GPA improvement strategies  
- Graduation requirement tracking
- Internship and career advice
- Study tips and resources

Always be encouraging, concise, and specific. Ask clarifying questions 
when needed, like what year or major the student is."""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "I'm a sophomore CS student with a 2.8 GPA, what should I focus on?"}
    ]
)

print(response.choices[0].message.content)
