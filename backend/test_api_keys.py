"""Quick test to verify Claude and Gemini API keys work with CrewAI."""
import os
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

print(f"ANTHROPIC_API_KEY set: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
print(f"GEMINI_API_KEY set: {bool(os.getenv('GEMINI_API_KEY'))}")

# Test 1: Direct Anthropic API call
print("\n--- Test 1: Direct Claude API ---")
try:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    print(f"Claude OK: {msg.content[0].text}")
except Exception as e:
    print(f"Claude Error: {type(e).__name__}: {str(e)[:300]}")

# Test 2: Direct Gemini via litellm
print("\n--- Test 2: Gemini via litellm ---")
try:
    import litellm
    response = litellm.completion(
        model="gemini/gemini-2.0-flash",
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=50,
    )
    print(f"Gemini OK: {response.choices[0].message.content}")
except Exception as e:
    print(f"Gemini Error: {type(e).__name__}: {str(e)[:300]}")

# Test 3: CrewAI with Claude
print("\n--- Test 3: CrewAI + Claude ---")
try:
    from crewai import Agent, Task, Crew, Process
    agent = Agent(
        role="Test",
        goal="Say hello",
        backstory="Test agent.",
        llm="anthropic/claude-3-5-sonnet-20241022",
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description="Respond with exactly: CREWAI_CLAUDE_OK",
        expected_output="CREWAI_CLAUDE_OK",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    print(f"CrewAI+Claude OK: {result}")
except Exception as e:
    print(f"CrewAI+Claude Error: {type(e).__name__}: {str(e)[:300]}")

    # Test 4: CrewAI with Gemini fallback
    print("\n--- Test 4: CrewAI + Gemini (fallback) ---")
    try:
        agent2 = Agent(
            role="Test",
            goal="Say hello",
            backstory="Test agent.",
            llm="gemini/gemini-2.0-flash",
            verbose=False,
            allow_delegation=False,
        )
        task2 = Task(
            description="Respond with exactly: CREWAI_GEMINI_OK",
            expected_output="CREWAI_GEMINI_OK",
            agent=agent2,
        )
        crew2 = Crew(agents=[agent2], tasks=[task2], process=Process.sequential, verbose=False)
        result2 = crew2.kickoff()
        print(f"CrewAI+Gemini OK: {result2}")
    except Exception as e2:
        print(f"CrewAI+Gemini Error: {type(e2).__name__}: {str(e2)[:300]}")

print("\n--- Done ---")
